from typing import Dict, Any


def get_screenshot_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the get_screenshot MCP tool.
    Captures a screenshot and returns it as base64 string.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def get_screenshot() -> Dict[str, Any]:
        """
        Takes a screenshot of the current screen.
        """

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

        driver = shared_state.appium_driver

        try:
            log("[get_screenshot] Attempting to take screenshot...")

            # -------------------------------
            # TAKE SCREENSHOT
            # -------------------------------
            # Prefer standard API if available
            screenshot_base64 = None

            try:
                # Standard Appium Python client method
                screenshot_base64 = driver.get_screenshot_as_base64()
            except Exception:
                # Fallback to low-level command (MCP style)
                response = driver.execute("takeScreenshot")
                screenshot_base64 = (
                    response if isinstance(response, str)
                    else response.get("value", "")
                )

            # -------------------------------
            # VALIDATION
            # -------------------------------
            if not screenshot_base64:
                raise RuntimeError("Empty screenshot received from driver.")

            log("[get_screenshot] Screenshot taken successfully.")

            return {
                "content": [{
                    "type": "text",
                    "text": screenshot_base64
                }]
            }

        except Exception as e:
            log(f"[get_screenshot] Error taking screenshot: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error taking screenshot: {str(e)}"
                }]
            }