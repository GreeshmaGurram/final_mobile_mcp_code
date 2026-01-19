
import requests
import os

from cryptography.hazmat.asn1.asn1 import sequence

from tools.base import login_check, get_jwt, get_auth_headers, get_user_id, get_current_project, set_job_id, get_user_name, get_job_id

BASE_URL = os.getenv("BASE_URL")
ITERATIONS = 20_000
KEY_LENGTH = 32  # bytes
import base64
import hmac
from typing import Tuple

# Try stdlib first; fall back to cryptography if unavailable
try:
    import hashlib
    _HAS_PBKDF2 = hasattr(hashlib, "pbkdf2_hmac")
except Exception:
    _HAS_PBKDF2 = False

if not _HAS_PBKDF2:
    try:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        _USE_CRYPTOGRAPHY = True
    except Exception as e:
        raise RuntimeError(
            "PBKDF2 is not available via hashlib, and cryptography is not installed."
        ) from e
else:
    _USE_CRYPTOGRAPHY = False

def _pbkdf2_sha1(password: bytes, salt: bytes) -> bytes:
    """Derive key using PBKDF2-HMAC-SHA1 with a compatible backend."""
    if not _USE_CRYPTOGRAPHY:
        # stdlib path
        return hashlib.pbkdf2_hmac(
            'sha1',
            password,
            salt,
            ITERATIONS,
            dklen=KEY_LENGTH
        )
    # cryptography fallback
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend(),
    )
    return kdf.derive(password)

def encode_password(plain_password: str) -> str:
    """
    Equivalent to Java getMethod1
    Returns 'saltBase64$hashBase64'
    """
    if not isinstance(plain_password, str) or not plain_password:
        raise ValueError("Password must be a non-empty string")

    # Java uses SecureRandom SHA1PRNG with 32-byte salt
    salt = os.urandom(KEY_LENGTH)

    derived_key = _pbkdf2_sha1(plain_password.encode('utf-8'), salt)

    salt_b64 = base64.b64encode(salt).decode('ascii')
    hash_b64 = base64.b64encode(derived_key).decode('ascii')

    return f"{salt_b64}${hash_b64}"

def starter_tools_registration(mcp):
    @mcp.tool
    def add_user(username: str, password: str, role: str, projects: list) -> dict:
        """
        Add a new user.

        Parameters:
        - username: The new user's username.
        - password: The new user's password.
        - role: The role to assign to the user.("user", "admin", "project_admin")
        - projects: A list of project identifiers to grant access to.

        Returns:
        - A dict containing success, status_code, and data or error.
        """
        url = f"{(BASE_URL or '').rstrip('/')}/add_user"
        headers = get_auth_headers()
        encoded_password = encode_password(password)
        payload = {
            "user_name": username,
            "password": encoded_password,
            "role": role,
            "access_baseline": "",
            "access_intents": "",
            "projects": projects or [],
            "creator_user_name": get_user_name(),
        }

        try:
            resp = requests.post(url, headers=headers, json=payload)
            if 200 <= resp.status_code < 300:
                try:
                    data = resp.json()
                except Exception:
                    data = {"text": resp.text}
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "data": data,
                }
            else:
                try:
                    error = resp.json()
                except Exception:
                    error = {"text": resp.text}
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": error,
                }
        except requests.RequestException as e:
            return {
                "success": False,
                "status_code": None,
                "error": str(e),
            }

    @mcp.tool
    def add_project(project_name: str) -> dict:
        """
        Create a new project for the current user.

        Parameters:
        - project_name: The name of the project to create.

        Returns:
        - A dict containing success, status_code, and data or error.
        """
        # Build URL and headers (Step 2)
        url = f"{(BASE_URL or '').rstrip('/')}/add_project"
        headers = get_auth_headers()

        # Use query params as per backend's add_project reading request.query_params (Step 2)
        params = {
            "user": get_user_name(),
            "project_name": project_name,
        }

        try:
            # Using POST with query params to align with backend example that reads query_params
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if 200 <= resp.status_code < 300:
                try:
                    data = resp.json()
                except Exception:
                    data = {"text": resp.text}
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "data": data,
                }
            else:
                try:
                    error = resp.json()
                except Exception:
                    error = {"text": resp.text}
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": error,
                }
        except requests.RequestException as e:
            return {
                "success": False,
                "status_code": None,
                "error": str(e),
            }
    #print(add_project("newTestProject"))
    #print(add_user("maniiideep", "admin123","user", ["TestProject"] ))
#starter_tools_registration("hi")

