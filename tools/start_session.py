import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from appium.webdriver import Remote as AppiumRemote
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions


def start_session_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the start_session MCP tool.
    Connects to an Appium server and starts a session on a device.
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
        device_name: Optional[str] = None
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

        ios_devices = []
        android_devices = []

        # -------------------------------
        # iOS DEVICE DETECTION
        # -------------------------------
        if platform in ("auto", "ios"):
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
        if platform in ("auto", "android"):
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
        # CAPABILITIES (🔥 FIXED HERE)
        # -------------------------------
        caps = {
            "platformName": "iOS" if selected_platform == "ios" else "Android",
            "appium:udid": selected_device["id"],
            "appium:deviceName": selected_device["name"],

            # Common
            "appium:newCommandTimeout": 600,
        }

        if selected_device.get("version"):
            caps["appium:platformVersion"] = selected_device["version"]

        if selected_platform == "ios":
            caps["appium:automationName"] = "XCUITest"

            options = XCUITestOptions().load_capabilities(caps)

        else:
            # 🔥 ANDROID FIXES
            caps.update({
                "appium:automationName": "UiAutomator2",

                # 🚀 CRITICAL FIX (your error)
                "appium:uiautomator2ServerLaunchTimeout": 120000,
                "appium:uiautomator2ServerInstallTimeout": 120000,
                "appium:adbExecTimeout": 120000,

                # 🧠 Stability
                "appium:skipServerInstallation": False,
                "appium:skipDeviceInitialization": False,
                "appium:noReset": True,
                "appium:ignoreHiddenApiPolicyError": True
            })

            options = UiAutomator2Options().load_capabilities(caps)

        log(f"[start_session] Capabilities: {caps}")

        # -------------------------------
        # CONNECT TO APPIUM
        # -------------------------------
        try:
            log("[start_session] Connecting to Appium...")

            driver = AppiumRemote(
                command_executor="http://127.0.0.1:4723",
                options=options
            )

            shared_state.appium_driver = driver
            # Avoid immediate NoSuchElement when the UI is still settling after launch/transition
            driver.implicitly_wait(10)

            log("[start_session] Session started successfully")

            # 🔥 DEBUG CHECK
            try:
                current_activity = driver.current_activity
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

                # Clear logcat buffer and truncate file so reads stay fast
                try:
                    await exec_async(f'adb -s {selected_device["id"]} logcat -c')
                except Exception as clear_err:
                    log(f"[start_session] Warning: could not clear logcat buffer: {str(clear_err)}")

                proc = subprocess.Popen(
                    [
                        "adb", "-s", selected_device["id"],
                        "logcat", "-v", "time", "*:I"
                    ],
                    stdout=open(ANDROID_LOG_FILE, "w"),
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