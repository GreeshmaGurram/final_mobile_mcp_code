import asyncio
from typing import Dict, Any

from tools.page_source_helper import read_ui_hierarchy


def find_element_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the find_element MCP tool.
    Supports both Android and iOS strategies.
    """

    log = dependencies["log_to_file"]
    # NOTE:
    # We intentionally DO NOT hard-block strategies here.
    # Appium can accept additional strategies depending on driver/platform/version.
    # We keep lightweight platform sanity checks and rely on the underlying driver
    # to validate the strategy, then return clear error messages.
    COMMON_STRATEGY_HINTS = [
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
        selector: str = "//android.widget.TextView",
        refresh_ui: bool = True,
        retry_once: bool = True,
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

        async def refresh_page_source() -> None:
            """
            Force-refresh the UI hierarchy so the agent isn't acting on stale DOM assumptions.
            Note: Appium find_element always queries the live UI, but capturing page source
            here makes debugging deterministic and improves agent reasoning.
            """
            if not refresh_ui:
                return
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: read_ui_hierarchy(driver, log=log),
                )
            except Exception as e:
                # Non-fatal; finding may still work even if page source retrieval fails.
                log(f"[find_element] page source refresh failed (non-fatal): {str(e)}")

        # FIND ELEMENT (with optional UI refresh + one retry)
        try:
            await refresh_page_source()
            log(f"[find_element] Strategy: {strategy}, Selector: {selector}")

            element = driver.find_element(strategy, selector)
            element_id = element.id
            log(f"[find_element] Element found with ID: {element_id}")

            # Cache the locator and record the action
            shared_state.action_recorder.register_element(element_id, strategy, selector)
            shared_state.action_recorder.record(
                "find_element",
                {"strategy": strategy, "selector": selector},
                {"elementId": element_id},
            )

            return {
                "content": [{
                    "type": "text",
                    "text": f"Element found. ID: {element_id}"
                }]
            }

        except Exception as e:
            # Optional one retry after a short wait (helps with transitions/animations/overlays).
            if retry_once:
                try:
                    await asyncio.sleep(0.6)
                    await refresh_page_source()
                    element = driver.find_element(strategy, selector)
                    element_id = element.id
                    log(f"[find_element] Element found on retry. ID: {element_id}")

                    shared_state.action_recorder.register_element(element_id, strategy, selector)
                    shared_state.action_recorder.record(
                        "find_element",
                        {"strategy": strategy, "selector": selector, "retried": True},
                        {"elementId": element_id},
                    )

                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Element found (after retry). ID: {element_id}"
                        }]
                    }
                except Exception:
                    pass

            log(f"[find_element] Error: {str(e)}")
            err = str(e)
            hint = ""
            lowered = err.lower()
            if "invalid selector" in lowered or "invalid" in lowered or "strategy" in lowered:
                hint = (
                    " Hint: strategy may be unsupported by the current driver/session. "
                    f"Common strategies: {COMMON_STRATEGY_HINTS}."
                )
            elif "no such element" in lowered:
                hint = (
                    " Hint: element not found on the current screen. "
                    "If the UI just changed, retry with refresh_ui=true (default), "
                    "or call get_page_source/get_page_source_file and choose a selector that matches the live hierarchy."
                )

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error finding element: {str(e)}{hint}"
                }]
            }