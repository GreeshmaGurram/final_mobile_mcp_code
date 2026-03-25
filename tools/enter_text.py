from typing import Dict, Any

from appium.webdriver.webelement import WebElement


def enter_text_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the enter_text MCP tool.
    Sets the value of an element by clearing it first and then typing.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def enter_text(elementId: str, text: str) -> Dict[str, Any]:
        """
        Sets the value of an element, clearing its contents first.
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
        elementId = (elementId or "").strip()
        if not elementId:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Element ID was not provided."
                }]
            }

        if text is None:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Text to enter was not provided."
                }]
            }

        driver = shared_state.appium_driver

        try:
            log(f"[enter_text] Attempting to set value for element with ID '{elementId}'")

            el = WebElement(driver, elementId)
            el.clear()
            el.send_keys(text)

            log(f"[enter_text] Value set for element with ID '{elementId}' successfully.")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Value set for element with ID '{elementId}' successfully."
                }]
            }

        except Exception as e:
            log(f"[enter_text] Error setting value for element with ID '{elementId}': {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error setting value for element with ID '{elementId}': {str(e)}"
                }]
            }