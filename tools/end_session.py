from typing import Dict, Any


def end_session_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the end_session MCP tool.
    Ends the current Appium session.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def end_session() -> Dict[str, Any]:
        """
        End the current Appium session.
        """

        # -------------------------------
        # CHECK IF SESSION EXISTS
        # -------------------------------
        if shared_state.appium_driver:
            platform_name = shared_state.current_platform or "device"

            try:
                log(f"[end_session] Attempting to delete {platform_name} Appium session.")

                # 🔥 Equivalent of deleteSession()
                shared_state.appium_driver.quit()

                # Clear shared state
                shared_state.appium_driver = None
                shared_state.current_platform = None
                shared_state.current_device = None

                log(f"[end_session] {platform_name} Appium session deleted successfully.")

                # -------------------------------
                # TERMINATE LOG PROCESS
                # -------------------------------
                if shared_state.device_log_process:
                    log(f"[end_session] Terminating {platform_name} log capture process.")

                    try:
                        shared_state.device_log_process.terminate()
                    except Exception as kill_error:
                        log(f"[end_session] Error terminating log process: {str(kill_error)}")

                    shared_state.device_log_process = None

                    log(f"[end_session] {platform_name} log capture process terminated.")

                return {
                    "content": [{
                        "type": "text",
                        "text": "Appium session ended."
                    }]
                }

            except Exception as e:
                log(f"[end_session] Error ending Appium session: {str(e)}")

                # 🔥 Always clean state (VERY IMPORTANT)
                shared_state.appium_driver = None
                shared_state.current_platform = None
                shared_state.current_device = None

                # Cleanup log process even on failure
                if shared_state.device_log_process:
                    log("[end_session] Terminating log process due to error.")

                    try:
                        shared_state.device_log_process.terminate()
                    except Exception as kill_error:
                        log(f"[end_session] Error terminating log process during error: {str(kill_error)}")

                    shared_state.device_log_process = None

                return {
                    "content": [{
                        "type": "text",
                        "text": f"Error ending Appium session: {str(e)}"
                    }]
                }

        else:
            log("[end_session] No active Appium session to end.")

            return {
                "content": [{
                    "type": "text",
                    "text": "No active Appium session to end."
                }]
            }