import json

import mcp
import requests
import os
from tools.base import login_check, get_jwt, get_auth_headers, get_user_id, get_current_project, set_job_id, get_job_id, \
    get_project_path
from tools.script_generation_tools import script_generation_tools_registration

BASE_URL = os.getenv("BASE_URL")

def playwright_generation_tools_registration(mcp):
    @mcp.tool()
    def generate_playwright_script(
            script_name: str,
            test_case_id: int = 1,
    ) -> dict:
        """
        Generates a Playwright Python test script from a refined test case.

        Process:
        1. Fetches refined test case JSON via /get_refined_TestCases
        2. Sends it together with project path to /convert_json_to_python
        3. Returns the path to the generated .py script file

        Args:
            script_name: Name of the test case/script (used for naming)
            test_case_id: ID of the test case to generate script for (default: 1)

        Returns:
            dict with keys:
            - success: bool
            - script_path: str (path to generated .py file) – if successful
            - error: str – if failed
            - stage: str – where it failed (optional)
        """
        job_id = get_job_id()
        headers = get_auth_headers()
        if not headers:
            return {
                "success": False,
                "error": "Authentication headers missing"
            }

        project_path = get_project_path()  # Assuming this returns a string or Path
        if not project_path:
            return {
                "success": False,
                "error": "Could not determine project path"
            }

        # Step 1: Fetch refined test case
        try:
            refined_response = requests.post(
                BASE_URL + "get_refined_TestCases",
                json={
                    "job_id": job_id,
                    "test_case_id": test_case_id
                },
                headers=headers,
                timeout=20
            )
            refined_response.raise_for_status()
            refined_data = refined_response.json()

            if "Refined" not in refined_data:
                return {
                    "success": False,
                    "stage": "fetch_refined",
                    "error": refined_data.get("error", "Refined test case not found")
                }

            refined_tc = refined_data["Refined"]
            test_json = refined_tc.get("test_json")

            if not test_json:
                return {
                    "success": False,
                    "stage": "fetch_refined",
                    "error": "No executable test_json found in refined test case"
                }

        except Exception as e:
            return {
                "success": False,
                "stage": "fetch_refined",
                "error": str(e)
            }

        # Step 2: Send to /convert_json_to_python
        try:
            convert_payload = {
                "test_data": test_json,
                "project_path": str(project_path)  # convert Path to str if needed
            }

            convert_response = requests.post(
                BASE_URL + "convert_json_to_python",
                json=convert_payload,
                headers=headers,
                timeout=60
            )
            convert_response.raise_for_status()
            result = convert_response.json()

            # Assuming the endpoint returns something like:
            # {"success": true, "script_path": "/path/to/test_login.py"}
            # Adjust the keys below based on your actual response format
            if result.get("success"):
                return {
                    "success": True,
                    "script_path": result.get("script_path", "unknown"),
                    "message": f"Script generated successfully for test case {test_case_id}"
                }
            else:
                return {
                    "success": False,
                    "stage": "convert_to_python",
                    "error": result.get("error", "Script generation failed")
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "stage": "convert_to_python",
                "error": f"API call failed: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "stage": "convert_to_python",
                "error": f"Unexpected error: {str(e)}"
            }