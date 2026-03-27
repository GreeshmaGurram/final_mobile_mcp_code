from typing import Dict, Any


def get_page_source_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the get_page_source MCP tool.
    Retrieves the XML source hierarchy of the current screen.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def get_page_source() -> Dict[str, Any]:
        """
        Gets the page source (XML hierarchy) from the current Appium session.
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
            log("[get_page_source] Attempting to get page source...")

            # -------------------------------
            # GET PAGE SOURCE
            # -------------------------------
            # Equivalent to WebdriverIO getPageSource()
            response = driver.execute("getPageSource")

            # Appium may return string or dict
            page_source = response if isinstance(response, str) else response.get("value", "")

            log("[get_page_source] Page source retrieved successfully.")

            return {
                "content": [{
                    "type": "text",
                    "text": page_source
                }]
            }

        except Exception as e:
            log(f"[get_page_source] Error getting page source: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error getting page source: {str(e)}"
                }]
            }