from typing import Dict, Any


def launch_app_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the launch_app MCP tool.
    Works for both local Appium and cloud providers.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def launch_app(bundleId: str = "com.android.settings") -> Dict[str, Any]:
        #using a sample bundleID just for testing purposes
        """
        Launch an app using bundleId/package name.
        """

        if not bundleId or bundleId.strip() == "":
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: bundleId/package name cannot be empty."
                }]
            }

        # CHECK SESSION
        if not shared_state.appium_driver:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Appium session not active. Please start a session first."
                }]
            }

        driver = shared_state.appium_driver

        try:
            log(f"[launch_app] Launch request for: {bundleId}")

            is_cloud = False

            # -------------------------------
            # DETECT CLOUD (simple heuristic)
            # -------------------------------
            executor_url = getattr(driver, "command_executor", None)

            if executor_url and hasattr(executor_url, "_url"):
                url = executor_url._url
                if any(x in url for x in ["browserstack", "saucelabs", "lambda"]):
                    is_cloud = True

            log(f"[launch_app] Cloud environment: {is_cloud}")

            app_state = None

            if not is_cloud:
                try:
                    app_state = driver.query_app_state(bundleId)
                    log(f"[launch_app] App state: {app_state}")
                except Exception as e:
                    log(f"[launch_app] query_app_state not supported: {str(e)}")

            # TERMINATE IF RUNNING
            if app_state and app_state > 1:
                try:
                    log(f"[launch_app] App running (state={app_state}), terminating...")

                    driver.terminate_app(bundleId)

                    log(f"[launch_app] App terminated successfully")

                except Exception as term_error:
                    log(f"[launch_app] Could not terminate app: {str(term_error)}")

            elif is_cloud:
                # On cloud, try terminate anyway (safe attempt)
                try:
                    log("[launch_app] Cloud mode: attempting terminate (best effort)")
                    driver.terminate_app(bundleId)
                except Exception:
                    log("[launch_app] Cloud terminate skipped (not supported)")

            # ACTIVATE APP (MAIN STEP)
            log(f"[launch_app] Activating app: {bundleId}")

            driver.activate_app(bundleId)

            log(f"[launch_app] App launched successfully")

            return {
                "content": [{
                    "type": "text",
                    "text": f"App '{bundleId}' launched successfully (restarted if needed)."
                }]
            }

        except Exception as e:
            log(f"[launch_app] Error launching app {bundleId}: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error launching app '{bundleId}': {str(e)}"
                }]
            }