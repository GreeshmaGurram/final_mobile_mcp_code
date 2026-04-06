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
            # Keep existing low-level command for local compatibility,
            # then fallback for cloud grids that reject `elementClick`.
            try:
                driver.execute("elementClick", {"id": elementId})
            except Exception as click_cmd_error:
                log(f"[tap_element] elementClick not supported: {str(click_cmd_error)}")

                # Appium Python driver can recreate a WebElement from id.
                # This works on both local and cloud providers.
                element = driver.create_web_element(elementId)
                element.click()

            log(f"[tap_element] Element with ID '{elementId}' tapped successfully.")

            # Record the tap with locator context if available
            locator = shared_state.action_recorder.get_element_locator(elementId)
            params = {"elementId": elementId}
            if locator:
                params["locator"] = locator
            shared_state.action_recorder.record("tap_element", params)

            return {
                "content": [{
                    "type": "text",
                    "text": f"Element with ID '{elementId}' tapped successfully."
                }]
            }

        except Exception as e:
            log(f"[tap_element] Error tapping element with ID '{elementId}': {str(e)}")
            err = str(e)
            hint = ""
            lowered = err.lower()
            if "stale" in lowered or "invalid" in lowered or "no such element" in lowered:
                hint = (
                    " Hint: elementId may be stale after a UI change. "
                    "Call get_page_source, then find_element again to get a fresh elementId."
                )

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error tapping element with ID '{elementId}': {str(e)}{hint}"
                }]
            }