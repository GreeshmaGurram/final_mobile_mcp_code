from typing import Dict, Any
import os
import tempfile
import random
import time
from pathlib import Path


def get_page_source_file_tool_registration(mcp, shared_state, dependencies):
    """
    Registers the get_page_source_file MCP tool.
    Retrieves the XML page source, saves it to a temp file, and returns the file path.
    """

    log = dependencies["log_to_file"]

    @mcp.tool()
    async def get_page_source_file() -> Dict[str, Any]:
        """
        Gets page source and saves it to a temp file.
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
            log("[get_page_source_file] Attempting to get page source...")

            # -------------------------------
            # GET PAGE SOURCE
            # -------------------------------
            response = driver.execute("getPageSource")

            page_source = response if isinstance(response, str) else response.get("value", "")

            log("[get_page_source_file] Page source retrieved successfully.")

            # -------------------------------
            # CREATE TEMP FILE PATH
            # -------------------------------
            temp_dir = tempfile.gettempdir()

            file_name = f"appium-mcp-pagesource-{int(time.time()*1000)}-{random.randint(0, 10**6)}.xml"

            file_path = Path(temp_dir) / file_name
            file_path = file_path.resolve()

            # -------------------------------
            # WRITE FILE
            # -------------------------------
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(page_source)

            log(f"[get_page_source_file] Page source saved to: {file_path}")

            return {
                "content": [{
                    "type": "text",
                    "text": str(file_path)
                }]
            }

        except Exception as e:
            log(f"[get_page_source_file] Error getting page source: {str(e)}")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Error getting page source: {str(e)}"
                }]
            }