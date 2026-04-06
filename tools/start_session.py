import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from appium.webdriver import Remote as AppiumRemote
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions
from selenium.webdriver.common.options import ArgOptions

from tools.capability_store import _load_all as _load_caps


def start_session_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the start_session MCP tool.
    Connects to an Appium server and starts a session on a device.
    Supports local Appium and cloud providers (BrowserStack, Sauce Labs, LambdaTest).
    """

    log = dependencies["log_to_file"]
    exec_async = dependencies["exec_async"]
    parse_ios_version = dependencies["parse_ios_version"]
    detect_android_devices = dependencies["detect_android_devices"]

    LOG_DIR = Path("./logs")
    IOS_LOG_FILE = LOG_DIR / "ios_device.log"
    ANDROID_LOG_FILE = LOG_DIR / "android_device.log"

    @mcp.tool()
    async def start_session(
        platform: str = "auto",
        device_name: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        cloud_device_name: Optional[str] = None,
        cloud_os_version: Optional[str] = None,
        app: Optional[str] = None,
        cloud_auto_launch: Optional[bool] = None,
        cloud_app_package: Optional[str] = None,
        cloud_app_activity: Optional[str] = None,
        cloud_bundle_id: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Start an Appium session on a local or cloud device.

        Quickstart — use a saved capability profile:
            start_session(profile_name="my-profile")

        All other parameters are ignored when profile_name is provided.
        Create profiles with save_capability_profile first.
        """

        # -------------------------------
        # Load capability profile
        # -------------------------------
        if profile_name:
            profiles = _load_caps()
            profile = profiles.get(profile_name.strip())
            if profile is None:
                names = list(profiles.keys())
                return {
                    "content": [{
                        "type": "text",
                        "text": (
                            f"Capability profile '{profile_name}' not found.\n"
                            f"Available: {names if names else '(none)'}\n"
                            "Use save_capability_profile to create one."
                        )
                    }]
                }
            platform = profile.get("platform", "auto")
            device_name = profile.get("device_name")
            app = profile.get("app")
            cloud_provider = profile.get("cloud_provider")
            cloud_device_name = profile.get("cloud_device_name")
            cloud_os_version = profile.get("cloud_os_version")
            log(f"[start_session] Loaded capability profile '{profile_name}'")

        # -------------------------------
        # Prevent duplicate session
        # -------------------------------
        if shared_state.appium_driver:
            return {
                "content": [{
                    "type": "text",
                    "text": "Session already active. Please end it first."
                }]
            }

        # Helper to run blocking Appium driver creation in a thread
        # so the async event loop stays alive and MCP doesn't time out.
        async def create_driver_async(command_executor, options):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: AppiumRemote(
                    command_executor=command_executor,
                    options=options
                )
            )

        normalized_platform = (platform or "auto").strip().lower()
        if normalized_platform not in {"auto", "android", "ios"}:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Invalid platform '{platform}'. Use: auto, android, ios."
                }]
            }

        # -------------------------------
        # CLOUD SESSION
        # -------------------------------
        # Cloud/local routing must be driven by user intent from the agent call.
        # We intentionally do NOT auto-fallback to env CLOUD_PROVIDER.
        provider = (cloud_provider or "").strip().lower()
        cloud_requested_without_provider = (
            not provider and
            any([
                bool((cloud_device_name or "").strip()),
                bool((cloud_os_version or "").strip()),
                bool((app or "").strip()),
                bool((cloud_app_package or "").strip()),
                bool((cloud_app_activity or "").strip()),
                bool((cloud_bundle_id or "").strip()),
            ])
        )

        if cloud_requested_without_provider:
            return {
                "content": [{
                    "type": "text",
                    "text": (
                        "Cloud session parameters were provided without cloud_provider. "
                        "Set cloud_provider to one of: browserstack, saucelabs, lambdatest."
                    )
                }]
            }

        if provider:
            username = os.getenv("CLOUD_USERNAME", "")
            access_key = os.getenv("CLOUD_ACCESS_KEY", "")
            device = cloud_device_name or ""
            os_version = cloud_os_version or ""
            cloud_platform = normalized_platform if normalized_platform != "auto" else "android"

            log(f"[start_session] Starting cloud session on {provider}...")

            cloud_new_command_timeout = int(os.getenv("CLOUD_NEW_COMMAND_TIMEOUT", "3600"))
            cloud_idle_timeout_lt = int(os.getenv("CLOUD_IDLE_TIMEOUT", "1800"))

            app_url = (app or "").strip() if app is not None else (os.getenv("CLOUD_APP_URL", "") or "").strip()

            desired_auto_launch = None
            cloud_launch_target_label = ""
            lt_post_activate = False

            try:
                if provider == "browserstack":
                    hub_url = "https://hub-cloud.browserstack.com/wd/hub"
                    caps = {
                        "platformName": "iOS" if cloud_platform == "ios" else "Android",
                        "appium:newCommandTimeout": cloud_new_command_timeout,
                        "bstack:options": {
                            "userName": username,
                            "accessKey": access_key,
                            "deviceName": device,
                            "osVersion": os_version,
                        }
                    }

                elif provider == "saucelabs":
                    hub_url = f"https://{username}:{access_key}@ondemand.us-west-1.saucelabs.com/wd/hub"
                    caps = {
                        "platformName": "iOS" if cloud_platform == "ios" else "Android",
                        "appium:newCommandTimeout": cloud_new_command_timeout,
                        "appium:deviceName": device,
                        "appium:platformVersion": os_version,
                        "appium:app": app_url,
                        "appium:automationName": "XCUITest" if cloud_platform == "ios" else "UiAutomator2",
                    }

                elif provider == "lambdatest":
                    hub_url = f"https://{username}:{access_key}@mobile-hub.lambdatest.com/wd/hub"

                    # Real-device hubs often reject session caps such as appPackage, appActivity, bundleId,
                    # and autoLaunch ("capability not supported for real devices"). Use minimal caps only,
                    # then activate cloud_app_package / cloud_bundle_id via Appium after the session exists.
                    android_target_package = (cloud_app_package or "").strip() if cloud_platform == "android" else ""
                    ios_target_bundle_id = (cloud_bundle_id or "").strip() if cloud_platform == "ios" else ""
                    has_launch_target = bool(android_target_package or ios_target_bundle_id)

                    # Decide whether to include an app artifact (lt://...) in the session.
                    # - If user explicitly passes `app`, we use it (empty string clears app for this call).
                    # - If no `app` and they set a launch target, do not inject CLOUD_APP_URL (avoids OS mismatch).
                    # - Otherwise fall back to CLOUD_APP_URL for legacy single-app runs.
                    if app is not None:
                        app_url = (app or "").strip()
                    else:
                        app_url = "" if has_launch_target else (os.getenv("CLOUD_APP_URL", "") or "").strip()

                    if cloud_auto_launch is not None:
                        desired_auto_launch = bool(cloud_auto_launch)
                    else:
                        desired_auto_launch = False if has_launch_target else True

                    cloud_launch_target_label = (
                        android_target_package if android_target_package else ios_target_bundle_id
                    )

                    if cloud_auto_launch is False and not has_launch_target:
                        return {
                            "content": [{
                                "type": "text",
                                "text": (
                                    "LambdaTest: cloud_auto_launch=false requires a post-connect target. "
                                    "Provide cloud_app_package (Android) or cloud_bundle_id (iOS), or omit cloud_auto_launch."
                                )
                            }]
                        }

                    # Bare device session (no lt:// and no launch target) is allowed — start on launcher/home.
                    # Optional app_url from CLOUD_APP_URL still works for classic flows.

                    caps = {
                        "platformName": "iOS" if cloud_platform == "ios" else "Android",
                        "appium:newCommandTimeout": cloud_new_command_timeout,
                        "deviceName": device,
                        "platformVersion": os_version,
                        "automationName": "XCUITest" if cloud_platform == "ios" else "UiAutomator2",
                        "isRealMobile": True,
                        "LT:Options": {
                            "username": username,
                            "accessKey": access_key,
                            "w3c": True,
                            "build": "MCP Automation",
                            "name": "MCP Test Session",
                            "idleTimeout": cloud_idle_timeout_lt,
                        },
                    }

                    if app_url:
                        caps["app"] = app_url

                    lt_post_activate = bool(cloud_launch_target_label) and (
                        not app_url or cloud_auto_launch is False
                    )

                else:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Unknown cloud provider '{provider}'. Use: browserstack, saucelabs, lambdatest."
                        }]
                    }

                # Build options
                if provider == "lambdatest":
                    options = ArgOptions()
                    for key, value in caps.items():
                        options.set_capability(key, value)
                elif cloud_platform == "ios":
                    options = XCUITestOptions().load_capabilities(caps)
                else:
                    options = UiAutomator2Options().load_capabilities(caps)

                log(f"[start_session] Connecting to {provider} at {hub_url}...")

                # ✅ FIX: Non-blocking driver creation for cloud
                driver = await create_driver_async(hub_url, options)

                shared_state.appium_driver = driver
                shared_state.current_platform = cloud_platform
                shared_state.current_device = {
                    "platform": cloud_platform,
                    "type": "cloud",
                    "provider": provider,
                    "name": device or f"{provider} device",
                    "id": None,
                    "version": os_version,
                }

                session_app_ref = cloud_launch_target_label or app_url or ""
                shared_state.action_recorder.set_session(
                    cloud_platform,
                    shared_state.current_device,
                    session_app_ref,
                )

                # LambdaTest: open system/preinstalled app after session (never via appPackage in session caps).
                if provider == "lambdatest" and lt_post_activate:
                    try:
                        loop = asyncio.get_event_loop()
                        if cloud_platform == "android":
                            pkg = (cloud_app_package or "").strip()
                            act = (cloud_app_activity or "").strip()
                            if act:
                                await loop.run_in_executor(
                                    None,
                                    lambda: driver.start_activity(pkg, act),
                                )
                            else:
                                try:
                                    await loop.run_in_executor(
                                        None,
                                        lambda p=pkg: driver.activate_app(p),
                                    )
                                except Exception:
                                    await loop.run_in_executor(
                                        None,
                                        lambda p=pkg: driver.start_activity(p, ".Settings"),
                                    )
                        else:
                            await loop.run_in_executor(
                                None,
                                lambda: driver.activate_app(
                                    (cloud_bundle_id or "").strip()
                                ),
                            )
                        log(f"[start_session] Opened target app on cloud: {cloud_launch_target_label}")
                    except Exception as e:
                        log(f"[start_session] Failed to open target app: {str(e)}")
                        return {
                            "content": [{
                                "type": "text",
                                "text": (
                                    "Cloud session started, but opening the target app failed. "
                                    f"Target: {cloud_launch_target_label}. "
                                    f"Error: {str(e)}. "
                                    "This usually means the app/package/bundleId is not available on that "
                                    "cloud device image. If you need installation, also provide `app` (lt://...) "
                                    "and ensure your cloud_app_package/cloud_bundle_id matches that uploaded build."
                                )
                            }]
                        }

                log(f"[start_session] Cloud session started on {provider}")

                return {
                    "content": [{
                        "type": "text",
                        "text": (
                            f"Cloud session started on {provider} ({device or 'default device'}). "
                            f"autoLaunch={desired_auto_launch}. "
                            f"Target={cloud_launch_target_label or '(none)'}"
                        )
                    }]
                }

            except Exception as e:
                shared_state.appium_driver = None
                shared_state.current_device = None
                shared_state.current_platform = None
                log(f"[start_session] Cloud session failed: {str(e)}")

                err = str(e)
                hints = []
                if "401" in err.lower() or "unauthorized" in err.lower():
                    hints.append("Check CLOUD_USERNAME/CLOUD_ACCESS_KEY.")
                if "device" in err.lower() and "not" in err.lower():
                    hints.append("Verify cloud_device_name and cloud_os_version match LambdaTest's pool.")
                if "capability" in err.lower() or "invalid" in err.lower():
                    if provider == "lambdatest":
                        hints.append(
                            "LambdaTest real devices often reject appPackage/autoLaunch in session caps; "
                            "use cloud_app_* / cloud_bundle_id (opened after connect)."
                        )
                    else:
                        hints.append("Verify cloud capabilities match the provider documentation.")
                if not hints:
                    hints.append("Check the LambdaTest logs/video for capability errors.")
                hint_text = " " + " ".join(hints)

                return {
                    "content": [{
                        "type": "text",
                        "text": f"Error starting cloud session on {provider}: {str(e)}.{hint_text}"
                    }]
                }

        # -------------------------------
        # LOCAL SESSION
        # -------------------------------
        ios_devices = []
        android_devices = []

        # -------------------------------
        # iOS DEVICE DETECTION
        # -------------------------------
        if normalized_platform in ("auto", "ios"):
            try:
                log("[start_session] Detecting iOS simulators...")

                result = await exec_async("xcrun simctl list devices booted -j")
                sim_data = json.loads(result["stdout"])

                for runtime, devices in sim_data.get("devices", {}).items():
                    for device in devices:
                        if device.get("state") == "Booted":
                            ios_devices.append({
                                "platform": "ios",
                                "id": device.get("udid"),
                                "name": device.get("name"),
                                "version": parse_ios_version(runtime),
                                "runtime": runtime,
                                "type": "simulator"
                            })

                log(f"[start_session] Found {len(ios_devices)} iOS devices")

            except Exception as e:
                log(f"[start_session] iOS detection failed: {str(e)}")

        # -------------------------------
        # ANDROID DEVICE DETECTION
        # -------------------------------
        if normalized_platform in ("auto", "android"):
            try:
                log("[start_session] Detecting Android devices...")
                android_devices = detect_android_devices()
                log(f"[start_session] Found {len(android_devices)} Android devices")
            except Exception as e:
                log(f"[start_session] Android detection failed: {str(e)}")

        all_devices = ios_devices + android_devices

        if not all_devices:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: No devices found. Start emulator or simulator."
                }]
            }

        # -------------------------------
        # DEVICE SELECTION
        # -------------------------------
        selected_device = None

        if device_name:
            for d in all_devices:
                if device_name.lower() in (d.get("name") or "").lower():
                    selected_device = d
                    break

            if not selected_device:
                names = ", ".join(d.get("name", "") for d in all_devices)
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Device '{device_name}' not found. Available: {names}"
                    }]
                }
        else:
            selected_device = ios_devices[0] if ios_devices else android_devices[0]

        if not selected_device:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error selecting device"
                }]
            }

        selected_platform = selected_device["platform"]

        shared_state.current_device = selected_device
        shared_state.current_platform = selected_platform

        log(f"[start_session] Selected {selected_platform}: {selected_device['name']}")

        # -------------------------------
        # CAPABILITIES
        # -------------------------------
        caps = {
            "platformName": "iOS" if selected_platform == "ios" else "Android",
            "appium:udid": selected_device["id"],
            "appium:deviceName": selected_device["name"],
            "appium:newCommandTimeout": 3600,
        }

        if selected_device.get("version"):
            caps["appium:platformVersion"] = selected_device["version"]

        if selected_platform == "ios":
            caps["appium:automationName"] = "XCUITest"
            options = XCUITestOptions().load_capabilities(caps)

        else:
            caps.update({
                "appium:automationName": "UiAutomator2",
                "appium:uiautomator2ServerLaunchTimeout": 120000,
                "appium:uiautomator2ServerInstallTimeout": 120000,
                "appium:adbExecTimeout": 120000,
                "appium:skipServerInstallation": False,
                "appium:skipDeviceInitialization": False,
                "appium:noReset": True,
                "appium:ignoreHiddenApiPolicyError": True
            })
            options = UiAutomator2Options().load_capabilities(caps)

        log(f"[start_session] Capabilities: {caps}")

        # -------------------------------
        # CONNECT TO APPIUM
        # ✅ FIX: Use run_in_executor so the blocking AppiumRemote()
        #         call does NOT freeze the async event loop.
        #         Without this, Claude's MCP client times out waiting
        #         for a response during the 30-90s session creation.
        # -------------------------------
        try:
            log("[start_session] Connecting to Appium (non-blocking)...")

            driver = await create_driver_async("http://127.0.0.1:4723", options)

            shared_state.appium_driver = driver
            shared_state.action_recorder.set_session(
                selected_platform,
                selected_device,
                app or "",
            )

            log("[start_session] Session started successfully")

            # Debug: fetch current activity
            try:
                loop = asyncio.get_event_loop()
                current_activity = await loop.run_in_executor(
                    None, lambda: driver.current_activity
                )
                log(f"[start_session] Current activity: {current_activity}")
            except Exception as e:
                log(f"[start_session] Could not fetch activity: {str(e)}")

        except Exception as e:
            shared_state.appium_driver = None
            shared_state.current_device = None
            shared_state.current_platform = None

            log(f"[start_session] Session failed: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error starting session: {str(e)}"
                }]
            }

        # -------------------------------
        # LOG CAPTURE
        # -------------------------------
        if shared_state.device_log_process:
            try:
                shared_state.device_log_process.terminate()
            except Exception:
                pass
            shared_state.device_log_process = None

        LOG_DIR.mkdir(exist_ok=True)

        try:
            if selected_platform == "ios":
                log("[start_session] Starting iOS log capture...")
                ios_log_fh = open(IOS_LOG_FILE, "a")
                proc = subprocess.Popen(
                    [
                        "xcrun", "simctl", "spawn",
                        selected_device["id"],
                        "log", "stream"
                    ],
                    stdout=ios_log_fh,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                proc._log_fh = ios_log_fh  # keep reference so it can be closed on end_session

            else:
                log("[start_session] Starting Android logcat...")
                android_log_fh = open(ANDROID_LOG_FILE, "a")
                proc = subprocess.Popen(
                    [
                        "adb", "-s", selected_device["id"],
                        "logcat", "-v", "time", "*:V"
                    ],
                    stdout=android_log_fh,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                proc._log_fh = android_log_fh  # keep reference so it can be closed on end_session

            shared_state.device_log_process = proc

        except Exception as e:
            log(f"[start_session] Log capture failed: {str(e)}")

        # -------------------------------
        # SUCCESS RESPONSE
        # -------------------------------
        return {
            "content": [{
                "type": "text",
                "text": f"Appium session started on {selected_device['name']} ({selected_platform})"
            }]
        }