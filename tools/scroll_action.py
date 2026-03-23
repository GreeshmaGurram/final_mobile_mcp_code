import asyncio
from typing import Dict, Any


def scroll_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the scroll MCP tool.
    Performs scroll using normalized coordinates (0 → 1).
    """

    log = dependencies["log_to_file"]

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

            # Clamp values between 0 and 1
            end_x = max(0, min(1, end_x))
            end_y = max(0, min(1, end_y))

            log(f"[scroll] Normalized coords: ({start_x},{start_y}) → ({end_x},{end_y})")

            # -------------------------------
            # BUILD ACTIONS
            # -------------------------------
            actions = _build_scroll_actions(start_x, start_y, end_x, end_y, width, height)

            log(f"[scroll] Performing W3C actions: {actions}")

            # -------------------------------
            # EXECUTE SCROLL
            # -------------------------------
            driver.perform_actions(actions)

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