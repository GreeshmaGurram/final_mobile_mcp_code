import json

import mcp
import requests
import os
from tools.base import login_check, get_jwt,get_auth_headers, get_user_id, get_current_project, set_job_id,get_job_id
BASE_URL = os.getenv("BASE_URL")

import random

def generate_unique_id():
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    fraction = random.random()
    result = ""

    while fraction > 0 and len(result) < 20:
        fraction *= 36
        digit = int(fraction)
        result += chars[digit]
        fraction -= digit

    return result


def script_generation_tools_registration(mcp):

    @mcp.tool()
    def generate_script_for_testcase(
            script_name: str,
            test_case_id: int = 1,
            browser: str = "chrome",
            headless: bool = False,
            sequence_no: int = 2
    ) -> dict:
        """
        Triggers validation then automatically starts Playwright script generation
        for the specified test case.
        """

        job_id = get_job_id()
        headers = get_auth_headers()
        if not headers:
            return {
                "success": False,
                "error": "Authentication headers missing"
            }

        # ── Step 1: Validation ───────────────────────────────────────────────
        try:
            val_payload = {
                "job_id": job_id,
                "sequence_no": sequence_no,
                "test_case_id": test_case_id
            }

            val_response = requests.post(
                BASE_URL + "start_validation",
                json=val_payload,
                headers=headers,
                timeout=30
            )
            val_response.raise_for_status()
            val_data = val_response.json()

            if not val_data.get("success") or not val_data.get("test_cases"):
                return {
                    "success": False,
                    "stage": "validation",
                    "response": val_data
                }

            test_case_data = next(
                (
                    tc for tc in val_data["test_cases"]
                    if isinstance(tc, dict)
                    and (tc.get("test_case_id") == test_case_id or tc.get("id") == test_case_id)
                ),
                None
            )

            if not test_case_data or not test_case_data.get("test_json"):
                return {
                    "success": False,
                    "stage": "validation",
                    "error": "Valid test_json not found in validation response"
                }

            test_json = test_case_data["test_json"]

        except Exception as e:
            return {
                "success": False,
                "stage": "validation",
                "error": str(e)
            }

        # ── Step 2: Start script generation / execution ───────────────────────
        try:
            unique_id = generate_unique_id()

            exec_payload = {
                "data": test_json,
                "scriptName": script_name,
                "uniqueId": unique_id,
                "browser": browser,
                "headlessMode": str(headless).lower(),
                "project": get_current_project(),
                "user": "admin",
                "job_id": job_id,
                "baseLineFlag": "false",
                "captureScreenshot": "true",
                "multiData": "false",
                "agentic": "false"
            }

            exec_response = requests.post(
                BASE_URL + "start_script_generation",
                json=exec_payload,
                headers=headers,
                timeout=45
            )
            exec_response.raise_for_status()
            result = exec_response.json()

            if not result.get("success"):
                return {
                    "success": False,
                    "stage": "execution",
                    "response": result
                }

            # ✅ IMPORTANT: structured return
            return {
                "success": True,
                "job_id": job_id,
                "test_case_id": test_case_id,
                "script_name": result.get("scriptName"),
                "unique_id": result.get("uniqueId"),
                "execution_id": result.get("exec_id"),
                "browser": browser,
                "headless": headless
            }

        except Exception as e:
            return {
                "success": False,
                "stage": "execution",
                "error": str(e)
            }

    @mcp.tool()
    def get_script_generation_logs(
            unique_id: str,
            execution_id: str,
            limit: int = 500,
            batch: str = "false"
    ) -> dict:
        """
        Fetches real-time execution logs for a Playwright/script generation run.

        IMPORTANT:
        ⚠️ This tool REQUIRES the execution_id returned by `generate_script_for_testcase`.
        The execution_id MUST be provided explicitly. Do NOT rely on unique_id alone.

        The backend log store is keyed by execution_id. If execution_id is missing,
        log retrieval will fail even if unique_id is valid.

        ──────────────────────────────────────────────────────────────────────────────
        Parameters
        ──────────────────────────────────────────────────────────────────────────────
        unique_id : str
            The unique identifier originally sent when starting script generation.
            This value is used for request correlation ONLY.

        execution_id : str
            REQUIRED. The execution identifier returned by the script generation step.
            This MUST be passed as currExecutionId to retrieve logs.
            Example: result["execution_id"]

        limit : int, optional
            Maximum number of log entries to return (1–1000).
            Default is 500.

        batch : str, optional
            "true" or "false".
            Use "false" for single script runs (default).

        ──────────────────────────────────────────────────────────────────────────────
        Returns
        ──────────────────────────────────────────────────────────────────────────────
        str
            Formatted output containing:
            • Total number of log entries retrieved
            • Recent execution logs (steps, actions, errors, screenshots)
            • Optional shell/command output (shLog) if available

        ──────────────────────────────────────────────────────────────────────────────
        Correct Usage
        ──────────────────────────────────────────────────────────────────────────────
        Step 1: Start script generation
            result = generate_script_for_testcase(...)

        Step 2: Fetch logs using returned identifiers
            get_execution_logs(
                unique_id=result["unique_id"],
                execution_id=result["execution_id"]
            )

        ──────────────────────────────────────────────────────────────────────────────
        Incorrect Usage (will fail)
        ──────────────────────────────────────────────────────────────────────────────
            get_execution_logs(unique_id="abc123")  ❌ execution_id missing
        """

        try:
            headers = get_auth_headers()
            if not headers:
                return {
                    "success": False,
                    "error": "Authentication headers missing"
                }

            params = {
                "uniqueId": unique_id,
                "currExecutionId": execution_id,
                "limit": str(limit),
                "batch": batch
            }

            response = requests.get(
                BASE_URL + "get_execution_logs",
                params=params,
                headers=headers,
                timeout=20
            )

            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                return {
                    "success": False,
                    "error": data.get("error", "Unknown error from execution service")
                }

            logs = data.get("logs", []) or []
            shlog = data.get("shLog", "") or ""

            structured_logs = []

            for log in logs[-40:]:
                if not isinstance(log, (list, tuple)):
                    continue

                structured_logs.append({
                    "step_id": log[0] if len(log) > 0 else None,
                    "action": log[1] if len(log) > 1 else None,
                    "execution_type": log[2] if len(log) > 2 else None,
                    "url": log[3] if len(log) > 3 else None,
                    "message": log[4] if len(log) > 4 else None,
                    "screenshot": log[6] if len(log) > 6 else None,
                    "failed": log[9] == "true" if len(log) > 9 else False
                })

            return {
                "success": True,
                "unique_id": unique_id,
                "execution_id": execution_id,
                "total_logs": len(logs),
                "returned_logs": structured_logs,
                "has_more": len(logs) > 40,
                "shLog_preview": shlog[:1200] if shlog else ""
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": "Network/API error while fetching execution logs",
                "details": str(e)
            }

        except Exception as e:
            return {
                "success": False,
                "error": "Unexpected error while processing execution logs",
                "details": str(e)
            }

    @mcp.tool
    def user_input(user_input: str):
        job_id = get_job_id()
        headers = get_auth_headers()
        try:
            url_user_input = BASE_URL + f"/userInput/{job_id}"

            user_input_payload = {
                "user_input": user_input,  # or "refine" - please confirm which one you need
            }

            response = requests.post(url_user_input, json=user_input_payload, headers=headers)
            response.raise_for_status()
            user_input_data = response.json()
            return user_input_data
        except Exception as e:
            return {
                "success": False,
                "error": "User Input Couldnt be sent",
                "details": str(e)
            }
