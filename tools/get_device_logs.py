from typing import Dict, Any
import os


def get_device_logs_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the get_device_logs MCP tool.
    Retrieves console logs from the connected device/simulator since the last call.
    """

    log = dependencies["log_to_file"]
    device_log_file_path = dependencies["device_log_file_path"]
    android_log_file_path = dependencies["android_log_file_path"]

    @mcp.tool()
    async def get_device_logs() -> Dict[str, Any]:
        # -------------------------------
        # SESSION CHECK
        # -------------------------------
        if not shared_state.appium_driver:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Appium session not active. Please start a session first."
                }]
            }

        # -------------------------------
        # DETERMINE LOG FILE
        # -------------------------------
        log_file_path = (
            android_log_file_path
            if shared_state.current_platform == "android"
            else device_log_file_path
        )

        platform_name = shared_state.current_platform or "device"

        # -------------------------------
        # CHECK FILE EXISTS
        # -------------------------------
        log_file_exists = os.path.exists(log_file_path)

        if not shared_state.device_log_process and not log_file_exists:
            log(f"[get_device_logs] {platform_name} log capture is not active and no log file found.")

            return {
                "content": [{
                    "type": "text",
                    "text": f"{platform_name} log capture is not active or no logs have been captured yet."
                }]
            }

        # -------------------------------
        # READ LOG FILE
        # -------------------------------
        try:
            log(f"[get_device_logs] Attempting to read {platform_name} logs from: {log_file_path}")

            # Read only the tail to avoid huge responses/timeouts
            max_bytes = 1024 * 256  # 256 KB
            file_size = os.path.getsize(log_file_path) if os.path.exists(log_file_path) else 0

            with open(log_file_path, "rb") as f:
                if file_size > max_bytes:
                    f.seek(file_size - max_bytes)
                data = f.read()

            logs = data.decode("utf-8", errors="replace")

            if logs.strip() == "":
                log(f"[get_device_logs] {platform_name} log file is empty.")

                return {
                    "content": [{
                        "type": "text",
                        "text": f"No new {platform_name} logs since last retrieval."
                    }]
                }

            log(f"[get_device_logs] Successfully read {platform_name} logs. Clearing log file for next retrieval.")

            # -------------------------------
            # TRUNCATE FILE
            # -------------------------------
            try:
                open(log_file_path, "w").close()
                log(f"[get_device_logs] {platform_name} log file truncated.")
            except Exception as trunc_error:
                log(f"[get_device_logs] Warning: Could not truncate {platform_name} log file: {str(trunc_error)}. Logs might be duplicated on next call.")

            if file_size > max_bytes:
                logs = (
                    f"[truncated] Showing last {max_bytes} bytes of {platform_name} logs "
                    f"(file was {file_size} bytes)\n\n{logs}"
                )

            return {
                "content": [{
                    "type": "text",
                    "text": logs
                }]
            }

        except FileNotFoundError:
            log(f"[get_device_logs] {platform_name} log file not found.")

            return {
                "content": [{
                    "type": "text",
                    "text": f"{platform_name} log file not found. No logs to retrieve."
                }]
            }

        except Exception as e:
            log(f"[get_device_logs] Error reading {platform_name} logs: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error reading {platform_name} logs: {str(e)}"
                }]
            }