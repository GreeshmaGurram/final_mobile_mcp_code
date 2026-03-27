import asyncio
from typing import Dict, Any


def scroll_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the scroll MCP tool.
    Performs scroll using normalized coordinates (0 → 1).
    """

    log = dependencies["log_to_file"]

    def _session_platform(driver) -> str:
        p = (getattr(shared_state, "current_platform", None) or "").strip().lower()
        if p:
            return p
        caps = getattr(driver, "capabilities", None) or {}
        return str(caps.get("platformName", "") or "").strip().lower()

    def _ios_drag_normalized(
        driver,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        width: int,
        height: int,
    ) -> None:
        """
        XCUITest on many cloud grids does not implement W3C perform_actions.
        mobile: dragFromToForDuration is the reliable swipe primitive on iOS.
        """
        driver.execute_script(
            "mobile: dragFromToForDuration",
            {
                "fromX": int(round(start_x * width)),
                "fromY": int(round(start_y * height)),
                "toX": int(round(end_x * width)),
                "toY": int(round(end_y * height)),
                "duration": 0.6,
            },
        )

    def _android_swipe_gesture(driver, direction: str, percent: float) -> None:
        # Appium Android mobile gestures (UiAutomator2)
        size = driver.get_window_size()
        width = size["width"]
        height = size["height"]

        driver.execute_script(
            "mobile: swipeGesture",
            {
                "left": 0,
                "top": 0,
                "width": width,
                "height": height,
                "direction": direction,
                "percent": max(0.01, min(1.0, float(percent))),
            },
        )

    def _build_scroll_actions(start_x, start_y, end_x, end_y, width, height):
        """
        Convert normalized coords → absolute pixels and build W3C actions
        """

        return [{
            "type": "pointer",
            "id": "finger1",
            "parameters": {"pointerType": "touch"},
            "actions": [
                {
                    "type": "pointerMove",
                    "duration": 0,
                    "x": int(start_x * width),
                    "y": int(start_y * height),
                },
                {"type": "pointerDown", "button": 0},
                {"type": "pause", "duration": 200},
                {
                    "type": "pointerMove",
                    "duration": 600,
                    "x": int(end_x * width),
                    "y": int(end_y * height),
                },
                {"type": "pointerUp", "button": 0},
            ],
        }]

    @mcp.tool()
    async def scroll(
        direction: str = "down",
        distance: float = 0.6
    ) -> Dict[str, Any]:
        """
        Scroll screen in a given direction.
        direction: up / down / left / right
        distance: normalized (0–1)
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
            log(f"[scroll] Requested direction={direction}, distance={distance}")

            # -------------------------------
            # GET SCREEN SIZE
            # -------------------------------
            size = driver.get_window_size()
            width = size["width"]
            height = size["height"]

            log(f"[scroll] Screen size: {width}x{height}")

            # -------------------------------
            # DEFAULT CENTER START
            # -------------------------------
            # Keep swipes away from y≈0 / y≈1. Ending a vertical swipe at the very top
            # triggers the system notification / quick-settings shade on Android.
            margin = 0.14
            start_x, start_y = 0.5, 0.5
            end_x, end_y = 0.5, 0.5

            # -------------------------------
            # DIRECTION LOGIC
            # -------------------------------
            if direction == "down":
                end_y = start_y - distance
            elif direction == "up":
                end_y = start_y + distance
            elif direction == "left":
                end_x = start_x + distance
            elif direction == "right":
                end_x = start_x - distance
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": "Error: Invalid direction. Use up/down/left/right."
                    }]
                }

            # Clamp values between 0 and 1, then stay inside safe insets (avoid status/nav bars)
            end_x = max(0, min(1, end_x))
            end_y = max(0, min(1, end_y))
            start_x = max(margin, min(1 - margin, start_x))
            start_y = max(margin, min(1 - margin, start_y))
            end_x = max(margin, min(1 - margin, end_x))
            end_y = max(margin, min(1 - margin, end_y))

            log(f"[scroll] Normalized coords: ({start_x},{start_y}) → ({end_x},{end_y})")

            # -------------------------------
            # BUILD ACTIONS
            # -------------------------------
            actions = _build_scroll_actions(start_x, start_y, end_x, end_y, width, height)

            log(f"[scroll] Performing W3C actions: {actions}")

            # -------------------------------
            # EXECUTE SCROLL
            # -------------------------------
            platform = _session_platform(driver)

            if platform == "ios":
                # Cloud XCUITest often returns NotImplementedError for perform_actions
                log("[scroll] Using iOS mobile: dragFromToForDuration")
                _ios_drag_normalized(
                    driver, start_x, start_y, end_x, end_y, width, height
                )
            elif hasattr(driver, "perform_actions"):
                try:
                    driver.perform_actions(actions)
                    if hasattr(driver, "release_actions"):
                        driver.release_actions()
                except Exception as w3c_err:
                    log(f"[scroll] perform_actions failed ({w3c_err}); trying Android swipeGesture")
                    _android_swipe_gesture(driver, direction=direction, percent=distance)
            else:
                _android_swipe_gesture(driver, direction=direction, percent=distance)

            # Small wait for UI stability
            await asyncio.sleep(1)

            log("[scroll] Scroll executed successfully")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Scrolled {direction} successfully."
                }]
            }

        except Exception as e:
            log(f"[scroll] Error during scroll: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error performing scroll: {str(e)}"
                }]
            }