from typing import Dict, Any


def tap_element_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the tap_element MCP tool.
    Taps/clicks an element using its element ID.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def tap_element(elementId: str) -> Dict[str, Any]:
        """
        Tap an element using its element ID.
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

        # -------------------------------
        # INPUT VALIDATION
        # -------------------------------
        if not elementId or elementId.strip() == "":
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Element ID was not provided."
                }]
            }

        driver = shared_state.appium_driver

        try:
            log(f"[tap_element] Attempting to tap element with ID '{elementId}'")

            # -------------------------------
            # TAP ELEMENT
            # -------------------------------
            # Equivalent to WebdriverIO: elementClick
            driver.execute("elementClick", {"id": elementId})

            log(f"[tap_element] Element with ID '{elementId}' tapped successfully.")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Element with ID '{elementId}' tapped successfully."
                }]
            }

        except Exception as e:
            log(f"[tap_element] Error tapping element with ID '{elementId}': {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error tapping element with ID '{elementId}': {str(e)}"
                }]
            }