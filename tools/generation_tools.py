import mcp
import requests
from tools.base import login_check, get_jwt,get_auth_headers, get_user_id, get_current_project
BASE_URL = "http://localhost:8081/"
def generation_tools_registration(mcp):

    @mcp.tool()
    def add_numbers(a: int, b: int) -> int:
        """
        Add two numbers.
        """
        return a + b

    @mcp.tool()
    def start_test_step_generation(user_input: str) -> str:
        """
        Triggers the start of test step generation by calling the /start API endpoint.

        Args:
            user_input: The user Story.
        """
        user_data = login_check()
        if not user_data:
            return "Failed to authenticate. Cannot start generation."

        user_id = "admin"
        headers = get_auth_headers()
        access_token = get_jwt()
        project_id = get_current_project()

        if not user_id or not headers:
            return "Authentication or user context missing. Cannot start generation."

        url = BASE_URL + "start"
        payload = {
            "user_input": user_input,
            "project_id": project_id,
            "user_id": user_id,
            "sequence_number": 1
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return f"Successfully started generation. Response: {response.text}"
        except requests.RequestException as e:
            return f"Failed to start generation. Error: {str(e)}"
