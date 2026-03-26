import subprocess
import json
from pathlib import Path
from typing import Any, Dict, List
import asyncio


# ---------- Logging ----------
def log_to_file(*args):
    print(*args)


# ---------- Async Exec ----------
async def exec_async(cmd: str) -> Dict[str, str]:
    #open a terminal and execute the command passed as argument
    # and return the output and error if occured
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
    }


# ---------- iOS Version Parser ----------
#return the version of the ios device
def parse_ios_version(runtime: str | None) -> str | None:
    """
    Extracts iOS version from runtime string.
    e.g. "com.apple.CoreSimulator.SimRuntime.iOS-17-0" -> "17.0"
    """
    if not runtime:
        return None
    try:
        part = runtime.split(".")[-1]  # "iOS-17-0"
        for prefix in ("iOS-", "watchOS-", "tvOS-"):
            if part.startswith(prefix):
                part = part[len(prefix):]
                break
        return part.replace("-", ".")
    except Exception:
        return None


# ---------- Android Version Parser ----------
def parse_android_version(api_level: str | None) -> str | None:
    mapping = {34: '14.0', 33: '13.0', 32: '12.1', 31: '12.0', 30: '11.0',
    29: '10.0', 28: '9.0', 27: '8.1', 26: '8.0', 25: '7.1',
    24: '7.0', 23: '6.0', 22: '5.1', 21: '5.0'}
    try:
        #dict_name.get(key, default_value)
        #if the key is not found, return the default value
        #if the key is found, return the value
        return mapping.get(int(api_level), api_level)
    except Exception:
        return api_level


# ---------- Android Detection Helper ----------
def detect_android_devices() -> List[Dict[str, Any]]:
    adb = "adb"
    result = subprocess.run([adb, "devices", "-l"], capture_output=True, text=True)

    devices = []
    for line in result.stdout.splitlines():
        if "device" in line and "List" not in line:
            parts = line.split()
            device_id = parts[0]

            model = "Unknown Android Device"
            api_level = "unknown"

            try:
                #subprocess.run(command, capture_output=True, text=True) -> run system cmd
                model = subprocess.run(
                    [adb, "-s", device_id, "shell", "getprop", "ro.product.model"],
                    capture_output=True, text=True
                ).stdout.strip()

                api_level = subprocess.run(
                    [adb, "-s", device_id, "shell", "getprop", "ro.build.version.sdk"],
                    capture_output=True, text=True
                ).stdout.strip()
            except Exception:
                pass

            devices.append({
                "id": device_id,
                "name": model,
                "apiLevel": api_level,
                "version": parse_android_version(api_level) or "unknown",
                "type": "emulator" if "emulator" in device_id else "device",
                "platform": "android"
            })

    return devices