import json

import mcp
import requests
import os
from tools.base import login_check, get_jwt,get_auth_headers, get_user_id, get_current_project, set_job_id,get_job_id
from tools.script_generation_tools import script_generation_tools_registration

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


def script_execution_tools_registration(mcp):
    @mcp.tool()
    def execute_testcase(
            script_name: str,
            test_case_id: int = 1,
            browser: str = "chrome",
            headless: bool = False,
            sequence_no: int = 2
    ) -> dict:
        """
        Executes a refined test case in agentic mode.

        This tool performs an execution-only flow. It does NOT run validation logic.
        Instead, it explicitly transitions the test case from Validation to Execution,
        fetches the refined test case from storage, and starts Playwright execution
        with agentic behavior enabled.

        ──────────────────────────────────────────────────────────────────────────────
        Execution Flow
        ──────────────────────────────────────────────────────────────────────────────
        1. Marks the test case Validation stage as COMPLETED.
        2. Moves the test case Execution stage to IN_PROGRESS.
        3. Fetches the refined test case using /get_refined_TestCases.
        4. Starts Playwright execution in AGENTIC mode.

        In agentic mode:
        • Execution stops immediately on the first failure.
        • No self-healing or retries are performed.
        • An execution report is generated automatically.

        ──────────────────────────────────────────────────────────────────────────────
        Parameters
        ──────────────────────────────────────────────────────────────────────────────
        script_name : str
            Name of the script as shown in execution reports and UI.

        test_case_id : int
            Identifier of the test case to execute.

        browser : str, optional
            Browser to use for execution.
            Examples: "chrome", "firefox".
            Default is "chrome".

        headless : bool, optional
            Whether to run the browser in headless mode.
            Default is False.

        sequence_no : int, optional
            Workflow sequence number.
            Present for compatibility; not used directly in execution.
            Default is 2.

        ──────────────────────────────────────────────────────────────────────────────
        Returns
        ──────────────────────────────────────────────────────────────────────────────
        dict
            On success:
            {
                "success": true,
                "job_id": <int>,
                "test_case_id": <int>,
                "script_name": <str>,
                "unique_id": <str>,
                "execution_id": <str>,
                "browser": <str>,
                "headless": <bool>,
                "agentic": true
            }

            On failure:
            {
                "success": false,
                "stage": <"stage_update" | "fetch_refined" | "execution">,
                "error": <str>
            }

        ──────────────────────────────────────────────────────────────────────────────
        Important Notes
        ──────────────────────────────────────────────────────────────────────────────
        • This tool assumes the test case has already been refined.
        • Validation is NOT re-run.
        • Refined test cases are fetched via /get_refined_TestCases.
        • Execution is strictly agentic (fail-fast).
        • Suitable for direct execution, re-runs, or agent-driven workflows.

        ──────────────────────────────────────────────────────────────────────────────
        Correct Usage
        ──────────────────────────────────────────────────────────────────────────────
        execute_testcase(
            script_name="Login Flow",
            test_case_id=1,
            browser="chrome",
            headless=false
        )

        ──────────────────────────────────────────────────────────────────────────────
        Incorrect Usage
        ──────────────────────────────────────────────────────────────────────────────
        • Calling this tool before refinement is completed.
        • Expecting self-healing or retries (agentic mode disables them).
        """


        job_id = get_job_id()
        headers = get_auth_headers()
        if not headers:
            return {
                "success": False,
                "error": "Authentication headers missing"
            }

        # ── Step 1: Update test case stages ────────────────────────────────────
        try:
            stage_response = requests.post(
                f"{BASE_URL}update_test_case_stages",
                json={  # ✅ JSON body
                    "job_id": job_id,
                    "tc_id": test_case_id
                },
                headers=headers,
                timeout=15
            )

            stage_response.raise_for_status()
            stage_data = stage_response.json()

            if stage_data.get("status") != "success":
                return {
                    "success": False,
                    "stage": "stage_update",
                    "response": stage_data
                }

        except Exception as e:
            return {
                "success": False,
                "stage": "stage_update",
                "error": str(e)
            }

        # ── Step 2: Fetch refined test case via API ────────────────────────────
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

            # ⚠️ IMPORTANT:
            # _get_refined_test_cases deletes `test_json` before returning,
            # so we must reconstruct execution JSON from stored refined data
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

        # ── Step 3: Start execution (agentic mode) ─────────────────────────────
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
                "agentic": "true"
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

            return {
                "success": True,
                "job_id": job_id,
                "test_case_id": test_case_id,
                "script_name": result.get("scriptName"),
                "unique_id": result.get("uniqueId"),
                "execution_id": result.get("exec_id"),
                "browser": browser,
                "headless": headless,
                "agentic": True
            }

        except Exception as e:
            return {
                "success": False,
                "stage": "execution",
                "error": str(e)
            }

    @mcp.tool()
    def get_execution_logs(
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
