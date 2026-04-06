import requests
from tools.base import BASE_URL, get_auth_headers, set_job_id


def start_test_step_generation(user_input: str) -> str:
    """
    Calls the backend to start test step generation for the given user story.
    On success, stores the returned job_id and returns a success message.
    """
    if not BASE_URL:
        return "Error: BASE_URL environment variable is not set."

    url = BASE_URL + "start_generation"
    headers = get_auth_headers()
    payload = {"user_story": user_input}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        job_id = data.get("job_id") or data.get("jobId") or ""
        if job_id:
            set_job_id(str(job_id))
            return f"Successfully started generation job. Job ID: {job_id}"
        else:
            return f"Error: Backend did not return a job_id. Response: {data}"

    except requests.RequestException as e:
        return f"Error: Failed to start generation — {str(e)}"


def generation_tools_registration(mcp):

    @mcp.tool()
    def generate_test_steps(user_story: str) -> str:
        """
        Start test step generation for the provided user story.
        Returns the job ID on success.
        """
        return start_test_step_generation(user_story)
