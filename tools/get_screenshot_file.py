import random
import tempfile
import time
from pathlib import Path
from typing import Dict, Any


def get_screenshot_file_tool_registration(mcp, shared_state, dependencies):
    """
    Registers get_screenshot_file: writes a PNG to disk and returns the path.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def get_screenshot_file() -> Dict[str, Any]:
        """
        Capture the current screen as a PNG file on this machine.
        Returns the full path to the saved .png file (open it in any image viewer).
        """

        if not shared_state.appium_driver:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: Appium session not active. Please start a session first."
                }]
            }

        driver = shared_state.appium_driver

        try:
            log("[get_screenshot_file] Capturing PNG bytes...")

            png_bytes = driver.get_screenshot_as_png()
            if not png_bytes:
                raise RuntimeError("Empty screenshot from driver.")

            temp_dir = Path(tempfile.gettempdir())
            file_name = (
                f"appium-mcp-screenshot-{int(time.time() * 1000)}-"
                f"{random.randint(0, 10**6)}.png"
            )
            file_path = (temp_dir / file_name).resolve()

            file_path.write_bytes(png_bytes)
            log(f"[get_screenshot_file] Saved: {file_path}")

            return {
                "content": [{
                    "type": "text",
                    "text": str(file_path)
                }]
            }

        except Exception as e:
            log(f"[get_screenshot_file] Error: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error saving screenshot file: {str(e)}"
                }]
            }
