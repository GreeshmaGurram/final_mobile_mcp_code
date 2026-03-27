from typing import Dict, Any


def find_element_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the find_element MCP tool.
    Supports both Android and iOS strategies.
    """

    log = dependencies["log_to_file"]

    # ✅ All supported strategies (Android + iOS + Common)
    ALLOWED_STRATEGIES = [
        "id",
        "accessibility id",
        "xpath",
        "class name",
        "name",
        "-android uiautomator",
        "-ios predicate string",
        "-ios class chain",
    ]

    @mcp.tool()
    async def find_element(
        strategy: str = "xpath",
        selector: str = "//android.widget.TextView"
    ) -> Dict[str, Any]:
    # gave default values for strategy and selector just for testing purposes
        """
        Finds a UI element using a given strategy and selector.
        """

        # CHECK SESSION
        if not shared_state.appium_driver:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Appium session not active. Start session first."
                }]
            }

        # VALIDATE SELECTOR
        if not selector or selector.strip() == "":
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: selector cannot be empty."
                }]
            }

        driver = shared_state.appium_driver
        platform = shared_state.current_platform

        strategy = (strategy or "").strip()
        selector = (selector or "").strip()

        if not strategy:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: strategy cannot be empty."
                }]
            }

        if not selector:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: selector cannot be empty."
                }]
            }

        # VALIDATE PLATFORM
        if not platform:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Platform not detected. Please start a session first."
                }]
            }

        # VALIDATE STRATEGY
        if strategy not in ALLOWED_STRATEGIES:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Invalid strategy '{strategy}'. Allowed: {ALLOWED_STRATEGIES}"
                }]
            }

        # PLATFORM-SPECIFIC VALIDATION
        if platform == "android" and strategy.startswith("-ios"):
            return {
                "content": [{
                    "type": "text",
                    "text": f"Strategy '{strategy}' is iOS-only."
                }]
            }

        if platform == "ios" and strategy.startswith("-android"):
            return {
                "content": [{
                    "type": "text",
                    "text": f"Strategy '{strategy}' is Android-only."
                }]
            }

        # FIND ELEMENT
        try:
            log(f"[find_element] Strategy: {strategy}, Selector: {selector}")

            element = driver.find_element(strategy, selector)
            element_id = element.id
            log(f"[find_element] Element found with ID: {element_id}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Element found. ID: {element_id}"
                }]
            }

        except Exception as e:
            log(f"[find_element] Error: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error finding element: {str(e)}"
                }]
            }