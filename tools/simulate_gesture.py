from typing import Dict, Any
import json
import copy


def simulate_gesture_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the simulate_gesture MCP tool.
    Simulates gestures using normalized [0,1] coordinates.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def simulate_gesture(gestureDescription: str) -> Dict[str, Any]:
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

        log(f"[simulate_gesture] Received raw gestureDescription: {gestureDescription}")

        # -------------------------------
        # PARSE JSON
        # -------------------------------
        try:
            parsed_action_sequences = json.loads(gestureDescription)

            if not isinstance(parsed_action_sequences, list):
                raise ValueError("gestureDescription must be a JSON array of action sequences.")

        except Exception as parse_error:
            log(f"[simulate_gesture] Error parsing gestureDescription JSON: {str(parse_error)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error parsing gestureDescription JSON: {str(parse_error)}. Expected an array of W3C action sequences."
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
            for sequence in recalculated_sequences:
                if sequence.get("type") == "pointer" and isinstance(sequence.get("actions"), list):
                    for action in sequence["actions"]:
                        if action.get("type") == "pointerMove":

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
            driver.perform_actions(recalculated_sequences)

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