from typing import Dict, Any


def press_home_button_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the press_home_button MCP tool.
    Simulates pressing the home button on the device.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def press_home_button() -> Dict[str, Any]:
        """
        Simulates pressing the home button.
        """

        log("[press_home_button] Simulating home button press.")

        # -------------------------------
        # SESSION CHECK
        # -------------------------------
        if not shared_state.appium_driver:
            log("[press_home_button] Error: Appium session not started.")
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Appium session not started. Please start a session first."
                }]
            }

        driver = shared_state.appium_driver

        # -------------------------------
        # DETECT PLATFORM
        # -------------------------------
        try:
            capabilities = getattr(driver, "capabilities", {}) or {}
            platform_name = str(capabilities.get("platformName", "")).lower()
        except Exception:
            platform_name = ""

        log(f"[press_home_button] Detected platform: {platform_name}")

        try:
            # -------------------------------
            # iOS HANDLING
            # -------------------------------
            if platform_name == "ios":
                driver.execute_script("mobile: pressButton", {"name": "home"})

            # -------------------------------
            # ANDROID HANDLING
            # -------------------------------
            elif platform_name == "android":
                # Preferred method
                try:
                    driver.press_keycode(3)  # HOME key
                except Exception:
                    # Fallback (low-level)
                    driver.execute("pressKeyCode", {"keycode": 3})

            else:
                raise RuntimeError(f"Unsupported platform: {platform_name}. Only iOS and Android are supported.")

            success_message = (
                "Successfully simulated home button press. "
                "The application is now in the background."
            )

            log(f"[press_home_button] {success_message}")

            shared_state.action_recorder.record("press_home_button", {})

            return {
                "content": [{
                    "type": "text",
                    "text": success_message
                }]
            }

        except Exception as e:
            log(f"[press_home_button] Error simulating home button press: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Failed to simulate home button press: {str(e)}"
                }]
            }