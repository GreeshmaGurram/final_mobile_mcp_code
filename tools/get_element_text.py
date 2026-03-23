from typing import Dict, Any


def get_element_text_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the get_element_text MCP tool.
    Gets the text from an element (like input value or label text).
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def get_element_text(elementId: str) -> Dict[str, Any]:
        """
        Gets text from an element using its element ID.
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
        if not elementId:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Element ID was not provided."
                }]
            }

        driver = shared_state.appium_driver

        try:
            log(f"[get_element_text] Attempting to get text from element with ID '{elementId}'")

            # -------------------------------
            # GET ELEMENT TEXT (low-level)
            # -------------------------------
            # Equivalent to WebdriverIO getElementText
            response = driver.execute("getElementText", {"id": elementId})

            # Appium may return either direct string or dict
            text = response if isinstance(response, str) else response.get("value", "")

            log(f"[get_element_text] Successfully got text from element with ID '{elementId}'. Text: \"{text}\"")

            return {
                "content": [{
                    "type": "text",
                    "text": text
                }]
            }

        except Exception as e:
            log(f"[get_element_text] Error getting text from element with ID '{elementId}': {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error getting text from element with ID '{elementId}': {str(e)}"
                }]
            }