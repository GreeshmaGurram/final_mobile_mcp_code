import json
from pathlib import Path
from typing import Dict, Any
import requests
import os

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

if load_dotenv:
    # Loads .env from current working directory or project root if run there
    load_dotenv()

STATIC_USERNAME = "admin"
STATIC_PASSWORD = "admin123"
BASE_URL = os.getenv("BASE_URL")
# Static project name to set after login
STATIC_PROJECT_NAME = "TestProject"

# In-memory cache
JWT: str = ""
USER_ID: str = ""
USER_NAME: str = ""
CURRENT_PROJECT: str = ""
CURRENT_JOB_ID: str = ""  # Added for job_id tracking
TEST_JSON: dict = {}

# Persistent storage location: ~/.genwizard_mcp/jwt_token.json
TOKEN_FILE = Path.home() / ".genwizard_mcp" / "jwt_token.json"


def _ensure_storage_dir() -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_context_from_disk() -> Dict[str, Any]:
    """
    Load the persisted context (access_token, user_id, current_project, job_id).
    Returns empty defaults if not found or on error.
    """
    if not TOKEN_FILE.exists():
        return {}
    try:
        with TOKEN_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except Exception as e:
        print(f"Warning: failed to load context from disk: {e}")
        return {}


def _save_context_to_disk(ctx: Dict[str, Any]) -> None:
    """
    Persist the entire context to disk.
    """
    _ensure_storage_dir()
    try:
        with TOKEN_FILE.open("w", encoding="utf-8") as f:
            json.dump(ctx, f)
    except Exception as e:
        print(f"Warning: failed to persist context to disk: {e}")


def _get_ctx() -> Dict[str, Any]:
    """
    Construct a dict from in-memory values (used as the single source of truth).
    """
    return {
        "access_token": JWT or "",
        "user_id": USER_ID or "",
        "current_project": CURRENT_PROJECT or "",
        "job_id": CURRENT_JOB_ID or "",
        "user_name": USER_NAME or "",
        "test_json": TEST_JSON or {}
    }

def set_test_json(test_json: dict) -> None:
    """
    Set JWT in memory and persist it to disk.
    """
    global TEST_JSON
    TEST_JSON = test_json or ""
    ctx = _get_ctx()
    _save_context_to_disk(ctx)


def set_jwt(token: str) -> None:
    """
    Set JWT in memory and persist it to disk.
    """
    global JWT
    JWT = token or ""
    ctx = _get_ctx()
    _save_context_to_disk(ctx)


def set_user_id(user_id: str) -> None:
    """
    Set user_id in memory and persist it to disk.
    """
    global USER_ID
    USER_ID = str(user_id or "")
    ctx = _get_ctx()
    _save_context_to_disk(ctx)

def set_user_name(user_name: str) -> None:
    """
    Set user_id in memory and persist it to disk.
    """
    global USER_NAME
    USER_NAME = str(user_name or "")
    ctx = _get_ctx()
    _save_context_to_disk(ctx)


def set_current_project(project_name: str) -> None:
    """
    Set current project in memory and persist it to disk.
    """
    global CURRENT_PROJECT
    CURRENT_PROJECT = project_name or ""
    ctx = _get_ctx()
    _save_context_to_disk(ctx)


def set_job_id(job_id: str) -> None:
    """
    Set job_id in memory and persist it to disk.
    This allows the job_id to be referenced across the entire MCP session.
    """
    global CURRENT_JOB_ID
    CURRENT_JOB_ID = job_id or ""
    ctx = _get_ctx()
    _save_context_to_disk(ctx)
    print(f"Job ID '{job_id}' stored and persisted.")


def get_test_json() -> str:
    """
    Retrieve the JWT from memory, falling back to disk if necessary.
    """
    global TEST_JSON
    if TEST_JSON:
        return TEST_JSON
    # Hydrate from disk
    data = _load_context_from_disk()
    TEST_JSON = data.get("test_json", "") or ""
    return TEST_JSON

def get_jwt() -> str:
    """
    Retrieve the JWT from memory, falling back to disk if necessary.
    """
    global JWT
    if JWT:
        return JWT
    # Hydrate from disk
    data = _load_context_from_disk()
    JWT = data.get("access_token", "") or ""
    return JWT


def get_user_id() -> str:
    """
    Retrieve the user_id from memory, falling back to disk if necessary.
    """
    global USER_ID
    if USER_ID:
        return USER_ID
    data = _load_context_from_disk()
    USER_ID = str(data.get("user_id", "") or "")
    return USER_ID


def get_user_name() -> str:
    """
    Retrieve the user_id from memory, falling back to disk if necessary.
    """
    global USER_NAME
    if USER_NAME:
        return USER_NAME
    data = _load_context_from_disk()
    USER_NAME = str(data.get("user_name", "") or "")
    return USER_NAME

def get_current_project() -> str:
    """
    Retrieve the current project from memory, falling back to disk if necessary.
    """
    global CURRENT_PROJECT
    if CURRENT_PROJECT:
        return CURRENT_PROJECT
    data = _load_context_from_disk()
    CURRENT_PROJECT = data.get("current_project", "") or ""
    return CURRENT_PROJECT



def get_project_path() -> str:
    artefacts_path=os.getenv("ARTEFACTS_BASE")

    return f"{artefacts_path}/Main/{CURRENT_PROJECT}"



def get_job_id() -> str:
    """
    Retrieve the job_id from memory, falling back to disk if necessary.
    This allows any part of the MCP to access the current job_id.
    """
    global CURRENT_JOB_ID
    if CURRENT_JOB_ID:
        return CURRENT_JOB_ID
    data = _load_context_from_disk()
    CURRENT_JOB_ID = data.get("job_id", "") or ""
    return CURRENT_JOB_ID


def clear_jwt() -> None:
    """
    Clear JWT from memory and disk (e.g., on logout).
    """
    global JWT
    JWT = ""
    try:
        if TOKEN_FILE.exists():
            # Keep other context keys intact if needed; here we wipe all for simplicity
            TOKEN_FILE.unlink()
    except Exception as e:
        print(f"Warning: failed to delete context file: {e}")


def clear_job_id() -> None:
    """
    Clear the job_id from memory and disk.
    """
    global CURRENT_JOB_ID
    CURRENT_JOB_ID = ""
    ctx = _get_ctx()
    _save_context_to_disk(ctx)
    print("Job ID cleared.")


def get_auth_headers() -> dict:
    """
    Helper to get Authorization headers for authenticated requests.
    """
    token = get_jwt()
    return {"Authorization": f"Bearer {token}"} if token else {}


def set_current_project_api(project_name: str, user_id: str) -> bool:
    """
    Calls GET /setCurrentProject?project=<project_name>&userId=<user_id>.
    On success, stores project_name (and user_id if provided).
    """
    url = BASE_URL+"setCurrentProject"
    params = {"project": project_name, "userId": user_id}
    headers = get_auth_headers()
    try:
        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        # Persist locally on success
        if user_id:
            set_user_id(user_id)
        set_current_project(project_name)
        print(f"Current project set to '{project_name}' for user '{user_id}'.")
        return True
    except Exception as e:
        print(f"Failed to set current project: {e}")
        return False



def login_check():
    """
    Check if current session is alive by calling the isSessionAlive API with JWT in headers.
    Returns a dict: {"status": "Session alive"} or {"status": "Signed out"}.
    """
    url = BASE_URL + "isSessionAlive"
    try:
        headers = get_auth_headers()
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            # Prefer server-provided status if available, fallback to "Session alive"
            try:
                data = response.json()
                status = data.get("status") or "Session alive"
            except Exception:
                status = "Session alive"
            return True

        if response.status_code == 401:
            return False

        # Treat any unexpected response as signed out
        return False

    except Exception as e:
        print(f"Session alive check failed: {e}")
        return False



def base_tools_registration(mcp):
    @mcp.tool
    def login(user_name, password, project):
        """
            Authenticate with the backend, storing the JWT on success.
            Also initializes the current project for the authenticated user via the API.
            Parameters: user_name (str), password (str), project(str).
            Returns: a result/response on success; raises on authentication or API errors.
            Side effects: Persists the token and updates client session/project state.
        """
        url = BASE_URL + "login_check_mcp"
        params = {
            "user_name": user_name,
            "password": password
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if response.status_code == 200:
                token = data.get("access_token")
                user_id = str(data.get("user_id", "") or "")
                if token:
                    set_jwt(token)
                    print("Login check successful, JWT stored")
                else:
                    print("Login check successful but no access_token in response")

                if user_id:
                    set_user_id(user_id)
                    set_user_name(user_name)

                # After login, set the current project using a static name
                if token and user_id:
                    success = set_current_project_api(project, user_id)
                    if not success:
                        print("Warning: setCurrentProject API failed; project not updated.")
                else:
                    print("Warning: Missing token or user_id; skipping setCurrentProject API.")

            return data
        except Exception as e:
            print(f"Login check failed: {e}")
            return None
     #login("admin", "admin123", "TestProject")

# Attempt to preload an existing context at import time
_loaded = _load_context_from_disk()
JWT = _loaded.get("access_token", "") or ""
USER_ID = str(_loaded.get("user_id", "") or "")
CURRENT_PROJECT = _loaded.get("current_project", "") or ""
CURRENT_JOB_ID = _loaded.get("job_id", "") or ""  # Load job_id on startup


def get_status() -> str:
    """This Tool is used to receive status of the system, what agents and workflows have completed"""
    #add the screenshot url
    url = BASE_URL + "status/" + str(get_job_id())
    print(url)
    # payload ={
    #     "job_id": get_job_id()
    # }
    try:
        response = requests.get(url, headers=get_auth_headers())
        response.raise_for_status()
        print(response.text)
        return response.text
    except requests.RequestException as e:
        return f"Failed to get status. Error: {str(e)}"

def get_execution_logs(
        unique_id: str,
        execution_id: str | None = None,
        limit: int = 500,
        batch: str = "false"
) -> str:
    """
    Fetches real-time execution logs for a Playwright/script generation run.

    Retrieves logs (steps, actions, errors, screenshots info etc.) and optional
    shLog (shell/command output HTML if available).

    Main parameters:
    ┌────────────────┬──────────────────────────────────────────────────────────────┐
    │ Parameter      │ Description                                                  │
    ├────────────────┼──────────────────────────────────────────────────────────────┤
    │ unique_id      │ Required - The unique identifier of the execution run        │
    │                │ (usually returned when starting script generation)           │
    ├────────────────┼──────────────────────────────────────────────────────────────┤
    │ execution_id   │ Optional - Specific execution ID (currExecutionId)           │
    │                │ If not provided, falls back to unique_id                     │
    ├────────────────┼──────────────────────────────────────────────────────────────┤
    │ limit          │ Max number of log entries to return (1–1000)                 │
    │                │ Default: 500                                                 │
    ├────────────────┼──────────────────────────────────────────────────────────────┤
    │ batch          │ "true" or "false" - batch mode handling                      │
    │                │ Usually keep as "false" for single script runs               │
    └────────────────┴──────────────────────────────────────────────────────────────┘

    Returns:
        Formatted string containing:
        - Number of log entries found
        - Recent logs (most useful/recent entries)
        - Any shell/command output (shLog) if present
        - Or error message if the request failed

    Example usage:
        get_execution_logs("auto-12345-1-1739456789", limit=200)
        get_execution_logs(unique_id="exec-abc123", execution_id="456", batch="false")
    """
    try:
        headers = get_auth_headers()
        if not headers:
            return "Cannot fetch logs - authentication headers missing"

        params = {
            "uniqueId": unique_id,
            "limit": str(limit),
            "batch": batch
        }

        if execution_id:
            params["currExecutionId"] = execution_id

        response = requests.get(
            BASE_URL + "get_execution_logs",
            params=params,
            headers=headers,
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            return f"API reported failure: {data.get('error', 'Unknown error')}"

        logs = data.get("logs", [])
        shlog = data.get("shLog", "")

        # Prepare nice output
        result_lines = []

        result_lines.append(f"Execution logs for unique_id: {unique_id}")
        if execution_id:
            result_lines.append(f"  (specific execution_id: {execution_id})")

        result_lines.append(f"Total log entries received: {len(logs)}")
        result_lines.append(f"Limit requested: {limit}\n")

        if logs:
            result_lines.append("Recent logs (newest first):")
            # Show last 8-12 lines for readability, or all if few
            display_count = min(12, len(logs))
            for log in logs[-display_count:]:
                timestamp = log.get("timestamp", "—")
                level = log.get("level", "INFO").ljust(7)
                message = log.get("message", "").strip()
                result_lines.append(f"[{timestamp}] {level} {message}")
            if len(logs) > display_count:
                result_lines.append(f"... ({len(logs) - display_count} more entries)")
        else:
            result_lines.append("No log entries found yet.")

        if shlog and shlog.strip():
            result_lines.append("\nShell/Command output (shLog):")
            result_lines.append("-" * 60)
            # Limit shlog preview too (first ~1000 chars)
            preview = shlog[:1200] + ("..." if len(shlog) > 1200 else "")
            result_lines.append(preview)

        return "\n".join(result_lines)

    except requests.exceptions.RequestException as e:
        return f"Failed to fetch execution logs (network/API error): {str(e)}"
    except Exception as e:
        return f"Unexpected error while getting logs: {str(e)}"

if __name__ == "__main__":
    # Example usage for manual testing:
    print(login_check())
    #base_tools_registration("hi")
    print("Current JWT:", get_jwt())
    print("Current user_id:", get_user_id())
    print("Current project:", get_current_project())
    print("Current job_id:", get_job_id())
    #print(set_user_name("admiin"))
    print("Current user_name", get_user_name())