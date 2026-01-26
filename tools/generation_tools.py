import time

import mcp
import requests
import os
from tools.base import login_check, get_jwt,get_auth_headers, get_user_id, get_current_project, set_job_id,get_job_id
BASE_URL = os.getenv("BASE_URL")
def generation_tools_registration(mcp):

    @mcp.tool()
    def add_numbers(a: int, b: int) -> int:
        """
        Add two numbers.
        """
        return a + b

    @mcp.tool()
    def start_test_step_generation_with_user_input(user_input: str) -> str:
        """
        Triggers the start of test step generation by calling the /start API endpoint.
        Stores the returned job_id for later reference across the MCP session.

        Args:
            user_input: The user Story.

        Returns:
            Success message with job_id or error message.
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

            # Parse the response to extract job_id
            response_data = response.json()
            job_id = response_data.get("job_id")

            if job_id:
                # Store the job_id in the persistent context
                set_job_id(job_id)
                return (f"Successfully started generation.\n"
                        f"Job ID: {job_id}\n"
                        f"Project ID: {response_data.get('project_id')}\n"
                        f"User ID: {response_data.get('user_id')}\n"
                        f"Job ID has been stored and can be referenced anywhere in the session.")
            else:
                return f"Generation started but no job_id in response. Response: {response.text}"

        except requests.RequestException as e:
            return f"Failed to start generation. Error: {str(e)}"

    @mcp.tool()
    def start_test_step_generation_with_jira() -> str:
        """
        Triggers the start of test step generation by calling the /start API endpoint.
        Stores the returned job_id for later reference across the MCP session.

        Returns:
            Success message with job_id or error message.
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
            "user_input": "start JIRA agent",
            "project_id": project_id,
            "user_id": user_id,
            "sequence_number": 4
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            # Parse the response to extract job_id
            response_data = response.json()
            job_id = response_data.get("job_id")

            if job_id:
                # Store the job_id in the persistent context
                set_job_id(job_id)
                return (f"Successfully started generation.\n"
                        f"Job ID: {job_id}\n"
                        f"Project ID: {response_data.get('project_id')}\n"
                        f"User ID: {response_data.get('user_id')}\n"
                        f"Job ID has been stored and can be referenced anywhere in the session.")
            else:
                return f"Generation started but no job_id in response. Response: {response.text}"

        except requests.RequestException as e:
            return f"Failed to start generation. Error: {str(e)}"

    @mcp.tool()
    def get_status() -> str:
        """This Tool is used to receive status of the system, what agents and workflows have completed"""

        url = BASE_URL + "status/"+str(get_job_id())
        print(url)
        # payload ={
        #     "job_id": get_job_id()
        # }
        try:
            time.sleep(2)
            response = requests.get(url, headers=get_auth_headers())
            response.raise_for_status()
            print(response.text)
            return response.text
        except requests.RequestException as e:
            return f"Failed to get status. Error: {str(e)}"

    @mcp.tool()
    def get_generation_logs() -> str:
        """This Tool is used to receive status of the system, what agents and workflows have completed"""

        url = BASE_URL + "logs/" + str(get_job_id())
        print(url)
        # payload ={
        #     "job_id": get_job_id()
        # }
        try:
            time.sleep(2)
            response = requests.get(url, headers=get_auth_headers())
            response.raise_for_status()
            print(response.text)
            return response.text
        except requests.RequestException as e:
            return f"Failed to get status. Error: {str(e)}"


def start_test_step_generation(user_input: str) -> str:
    """
    Triggers the start of test step generation by calling the /start API endpoint.
    Stores the returned job_id for later reference across the MCP session.

    Args:
        user_input: The user Story.

    Returns:
        Success message with job_id or error message.
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

        # Parse the response to extract job_id
        response_data = response.json()
        job_id = response_data.get("job_id")

        if job_id:
            # Store the job_id in the persistent context
            set_job_id(job_id)
            return (f"Successfully started generation.\n"
                    f"Job ID: {job_id}\n"
                    f"Project ID: {response_data.get('project_id')}\n"
                    f"User ID: {response_data.get('user_id')}\n"
                    f"Job ID has been stored and can be referenced anywhere in the session.")
        else:
            return f"Generation started but no job_id in response. Response: {response.text}"

    except requests.RequestException as e:
        return f"Failed to start generation. Error: {str(e)}"


