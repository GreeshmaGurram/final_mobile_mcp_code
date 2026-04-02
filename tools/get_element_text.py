from typing import Dict, Any

from appium.webdriver.webelement import WebElement


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
        elementId = (elementId or "").strip()
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

            text = WebElement(driver, elementId).text

            log(f"[get_element_text] Successfully got text from element with ID '{elementId}'. Text: \"{text}\"")

            locator = shared_state.action_recorder.get_element_locator(elementId)
            params = {"elementId": elementId}
            if locator:
                params["locator"] = locator
            shared_state.action_recorder.record("get_element_text", params, {"text": text})

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