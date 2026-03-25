from typing import Any, Dict, List, Union
import json
import copy


def simulate_gesture_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the simulate_gesture MCP tool.
    Simulates gestures using normalized [0,1] coordinates.
    """

    log = dependencies["log_to_file"]

    def _android_swipe_from_normalized(driver, start_x: float, start_y: float, end_x: float, end_y: float) -> None:
        size = driver.get_window_size()
        width = size["width"]
        height = size["height"]

        dx = end_x - start_x
        dy = end_y - start_y
        if abs(dx) >= abs(dy):
            direction = "left" if dx < 0 else "right"
            percent = min(1.0, max(0.01, abs(dx)))
        else:
            direction = "up" if dy < 0 else "down"
            percent = min(1.0, max(0.01, abs(dy)))

        driver.execute_script(
            "mobile: swipeGesture",
            {
                "left": 0,
                "top": 0,
                "width": width,
                "height": height,
                "direction": direction,
                "percent": percent,
            },
        )

    @mcp.tool()
    async def simulate_gesture(gestureDescription: Union[str, List[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Simulates a gesture using W3C actions with normalized coordinates.
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
        if not gestureDescription:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: gestureDescription was not provided."
                }]
            }

        log(f"[simulate_gesture] Received gestureDescription type={type(gestureDescription)}")

        def _to_action_list(val: Any) -> List[Dict[str, Any]]:
            # If Inspector sends a native array, accept it
            if isinstance(val, list):
                return val

            # If Inspector sends a single object, wrap it
            if isinstance(val, dict):
                # Common Inspector/MCP wrapper: {"gestureDescription": [...]}
                if "gestureDescription" in val and len(val.keys()) == 1:
                    return _to_action_list(val["gestureDescription"])
                return [val]

            # If it's a string, attempt to JSON-parse (and also handle double-encoded strings)
            if isinstance(val, str):
                s = val.strip()
                parsed: Any = json.loads(s)
                # Sometimes tools get double-encoded, so the first parse returns a string
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    return [parsed]
                raise ValueError("gestureDescription JSON did not decode to an array/object.")

            raise ValueError("gestureDescription must be an array, object, or JSON string.")

        try:
            parsed_action_sequences = _to_action_list(gestureDescription)
        except Exception as parse_error:
            log(f"[simulate_gesture] Error parsing gestureDescription: {str(parse_error)}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error parsing gestureDescription: {str(parse_error)}. Expected an array of W3C action sequences."
                }]
            }

        driver = shared_state.appium_driver

        try:
            # -------------------------------
            # GET SCREEN SIZE
            # -------------------------------
            size = driver.get_window_size()
            width = size.get("width")
            height = size.get("height")

            log(f"[simulate_gesture] Normalizing coordinates based on screen size: {width}x{height}")

            # -------------------------------
            # DEEP COPY (avoid modifying input)
            # -------------------------------
            recalculated_sequences = copy.deepcopy(parsed_action_sequences)

            # -------------------------------
            # NORMALIZE COORDINATES
            # -------------------------------
            start_norm = None
            end_norm = None

            for sequence in recalculated_sequences:
                seq_actions = sequence.get("actions")
                if not isinstance(seq_actions, list):
                    raise ValueError(f"Invalid W3C sequence: missing/invalid 'actions' list in {sequence}")

                if sequence.get("type") == "pointer":
                    for action in seq_actions:
                        if action.get("type") == "pointerMove":
                            # Capture first + last normalized positions (before we convert)
                            if start_norm is None and isinstance(action.get("x"), (int, float)) and isinstance(action.get("y"), (int, float)):
                                start_norm = (float(action["x"]), float(action["y"]))
                            if isinstance(action.get("x"), (int, float)) and isinstance(action.get("y"), (int, float)):
                                end_norm = (float(action["x"]), float(action["y"]))

                            if isinstance(action.get("x"), (int, float)):
                                new_x = round(action["x"] * width)
                                log(f"[simulate_gesture] Normalizing x: {action['x']} -> {new_x}")
                                action["x"] = new_x

                            if isinstance(action.get("y"), (int, float)):
                                new_y = round(action["y"] * height)
                                log(f"[simulate_gesture] Normalizing y: {action['y']} -> {new_y}")
                                action["y"] = new_y

            log(f"[simulate_gesture] Performing W3C actions: {json.dumps(recalculated_sequences)}")

            # -------------------------------
            # PERFORM ACTIONS
            # -------------------------------
            if hasattr(driver, "perform_actions"):
                driver.perform_actions(recalculated_sequences)
                if hasattr(driver, "release_actions"):
                    driver.release_actions()
            else:
                # Android-native fallback: interpret the gesture as a swipe
                if not start_norm or not end_norm:
                    raise ValueError("Could not infer swipe start/end from gestureDescription pointerMove actions.")
                _android_swipe_from_normalized(
                    driver,
                    start_x=start_norm[0],
                    start_y=start_norm[1],
                    end_x=end_norm[0],
                    end_y=end_norm[1],
                )

            log("[simulate_gesture] W3C actions performed successfully.")

            return {
                "content": [{
                    "type": "text",
                    "text": "Gesture (W3C actions) performed successfully."
                }]
            }

        except Exception as e:
            log(f"[simulate_gesture] Error performing W3C actions: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error performing W3C actions: {str(e)}"
                }]
            }