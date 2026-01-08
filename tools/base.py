import json
from pathlib import Path
from typing import Dict, Any
import requests

STATIC_USERNAME = "admin"
STATIC_PASSWORD = "static_password"

# Static project name to set after login
STATIC_PROJECT_NAME = "TestProject"

# In-memory cache
JWT: str = ""
USER_ID: str = ""
CURRENT_PROJECT: str = ""
CURRENT_JOB_ID: str = ""  # Added for job_id tracking

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
        "job_id": CURRENT_JOB_ID or "",  # Added job_id to context
    }


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
    url = "http://localhost:8081/setCurrentProject"
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
    Perform login check and store JWT if received.
    Then set a static current project for the logged-in user via the API.
    """
    url = "http://localhost:8081/login_check"
    params = {
        "user_name": STATIC_USERNAME
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

            # After login, set the current project using a static name
            if token and user_id:
                success = set_current_project_api(STATIC_PROJECT_NAME, user_id)
                if not success:
                    print("Warning: setCurrentProject API failed; project not updated.")
            else:
                print("Warning: Missing token or user_id; skipping setCurrentProject API.")

        return data
    except Exception as e:
        print(f"Login check failed: {e}")
        return None


# Attempt to preload an existing context at import time
_loaded = _load_context_from_disk()
JWT = _loaded.get("access_token", "") or ""
USER_ID = str(_loaded.get("user_id", "") or "")
CURRENT_PROJECT = _loaded.get("current_project", "") or ""
CURRENT_JOB_ID = _loaded.get("job_id", "") or ""  # Load job_id on startup

if __name__ == "__main__":
    # Example usage for manual testing:
    login_check()
    print("Current JWT:", get_jwt())
    print("Current user_id:", get_user_id())
    print("Current project:", get_current_project())
    print("Current job_id:", get_job_id())