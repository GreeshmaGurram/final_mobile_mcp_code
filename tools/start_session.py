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
    ) -> Dict[str, Any]:

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
            app_url = app or os.getenv("CLOUD_APP_URL", "")
            device = cloud_device_name or ""
            os_version = cloud_os_version or ""
            cloud_platform = normalized_platform if normalized_platform != "auto" else "android"

            log(f"[start_session] Starting cloud session on {provider}...")

            cloud_new_command_timeout = int(os.getenv("CLOUD_NEW_COMMAND_TIMEOUT", "3600"))
            cloud_idle_timeout_lt = int(os.getenv("CLOUD_IDLE_TIMEOUT", "1800"))

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
                            "app": app_url,
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
                    caps = {
                        "platformName": "iOS" if cloud_platform == "ios" else "Android",
                        "appium:newCommandTimeout": cloud_new_command_timeout,
                        "deviceName": device,
                        "platformVersion": os_version,
                        "app": app_url,
                        "automationName": "XCUITest" if cloud_platform == "ios" else "UiAutomator2",
                        "isRealMobile": True,
                        "LT:Options": {
                            "username": username,
                            "accessKey": access_key,
                            "w3c": True,
                            "build": "MCP Automation",
                            "name": "MCP Test Session",
                            "idleTimeout": cloud_idle_timeout_lt,
                        }
                    }

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

                log(f"[start_session] Cloud session started on {provider}")

                return {
                    "content": [{
                        "type": "text",
                        "text": f"Cloud session started on {provider} ({device or 'default device'})."
                    }]
                }

            except Exception as e:
                shared_state.appium_driver = None
                shared_state.current_device = None
                shared_state.current_platform = None
                log(f"[start_session] Cloud session failed: {str(e)}")
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Error starting cloud session on {provider}: {str(e)}"
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
                proc = subprocess.Popen(
                    [
                        "xcrun", "simctl", "spawn",
                        selected_device["id"],
                        "log", "stream"
                    ],
                    stdout=open(IOS_LOG_FILE, "a"),
                    stderr=subprocess.STDOUT,
                    text=True
                )

            else:
                log("[start_session] Starting Android logcat...")
                proc = subprocess.Popen(
                    [
                        "adb", "-s", selected_device["id"],
                        "logcat", "-v", "time", "*:V"
                    ],
                    stdout=open(ANDROID_LOG_FILE, "a"),
                    stderr=subprocess.STDOUT,
                    text=True
                )

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