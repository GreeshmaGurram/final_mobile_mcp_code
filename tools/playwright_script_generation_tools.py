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

            convert_response = requests.get(
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

    @mcp.tool()
    def convert_playwright_py_to_ts(filename: str) -> dict:
        """
        Converts a Playwright Python test file to Playwright TypeScript via API.

        Calls GET /convert_playwright_py_to_ts with JSON body:
        {
          "filename": "<python_filename_without_ext_or_with_ext>"
        }

        Args:
            filename: Python test filename (with or without .py extension).

        Returns:
            The API response JSON as-is, e.g.:
            {
              "status": "success",
              "source": "C:/.../scripts\\test_x.py",
              "output": "C:/.../scripts_ts\\test_x.ts"
            }
            On error, returns:
            {
              "status": "error",
              "error": "<message>",
              "stage": "convert_py_to_ts"
            }
        """
        headers = get_auth_headers()
        if not headers:
            return {
                "status": "error",
                "error": "Authentication headers missing",
                "stage": "convert_py_to_ts"
            }

        payload = {
            "project_name": get_current_project(),
            "filename": filename
        }

        try:
            resp = requests.get(
                BASE_URL + "convert_playwright_py_to_ts",
                json=payload,
                headers=headers
            )
            resp.raise_for_status()
            # Return the API response as-is
            return resp.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"API call failed: {str(e)}",
                "stage": "convert_py_to_ts"
            }
        except ValueError as e:
            # JSON parse error
            return {
                "status": "error",
                "error": f"Invalid JSON response: {str(e)}",
                "stage": "convert_py_to_ts"
            }

    @mcp.tool()
    def export_artefacts(project: str = None) -> dict:
        """
        Calls /export_artefacts to save artefacts ZIP on the server and returns the file name to the user.

        Args:
            project: Optional project name. If not provided, resolved from current context.

        Returns:
            dict with keys:
            - success: bool
            - file_name: str (always present on success)
            - file_path: str (absolute path on the server, if provided by API)
            - saved: bool (True if newly created, False if it already existed; if provided by API)
            - error: str (when failed)
            - stage: str (where it failed)
        """
        headers = get_auth_headers()
        if not headers:
            return {
                "success": False,
                "stage": "auth",
                "error": "Authentication headers missing"
            }

        if not BASE_URL:
            return {
                "success": False,
                "stage": "config",
                "error": "BASE_URL is not configured"
            }

        proj = project or get_current_project()
        if not proj:
            return {
                "success": False,
                "stage": "input",
                "error": "Project name not provided and could not be determined"
            }

        try:
            resp = requests.post(
                BASE_URL + "export_artefacts",
                json={"project": proj},
                headers=headers,
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()

            file_name = data.get("file_name") or data.get("filename") or data.get("name")
            if not file_name:
                return {
                    "success": False,
                    "stage": "parse_response",
                    "error": f"file_name not found in response: {data}"
                }
            file_path = f"{BASE_URL}download/{file_name}"
            # Minimal contract: return filename to the user; path and saved are optional
            return {
                "success": True,
                "file_name": file_name,
                "file_path": file_path,
                "saved": data.get("saved")
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "stage": "export_artefacts",
                "error": f"API call failed: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "stage": "export_artefacts",
                "error": f"Unexpected error: {str(e)}"
            }
    #print(export_artefacts())

#s = playwright_generation_tools_registration("hi")


