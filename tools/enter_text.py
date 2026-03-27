from typing import Dict, Any


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

            # -------------------------------
            # CLEAR ELEMENT
            # -------------------------------
            # Preserve existing command path for local behavior.
            # If cloud grid rejects the command, fallback to element API.
            try:
                driver.execute("elementClear", {"id": elementId})
            except Exception as clear_cmd_error:
                log(f"[enter_text] elementClear not supported: {str(clear_cmd_error)}")
                element = driver.create_web_element(elementId)
                element.clear()

            # -------------------------------
            # SEND KEYS
            # -------------------------------
            # Same pattern for send keys.
            try:
                driver.execute("elementSendKeys", {
                    "id": elementId,
                    "text": text
                })
            except Exception as send_keys_cmd_error:
                log(f"[enter_text] elementSendKeys not supported: {str(send_keys_cmd_error)}")
                element = driver.create_web_element(elementId)
                element.send_keys(text)

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