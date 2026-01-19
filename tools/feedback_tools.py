import mcp
import requests
import os

from cryptography.hazmat.asn1.asn1 import sequence

from tools.base import login_check, get_jwt, get_auth_headers, get_user_id, get_current_project, set_job_id, get_job_id

BASE_URL = os.getenv("BASE_URL")
SELECTED_APPLICATION = "General"
BASE_FRONTEND_URL = os.getenv("BASE_FRONTEND_URL", "http://localhost:8082/Quality_Engineering_Agents/ai/")


def feedback_tools_registration(mcp):

    @mcp.tool()
    def get_feedback_details() -> str:
        """
        Calls the /feedback_details API to fetch feedback using the stored job_id.
        Provide the sequence_number; test_case_id defaults to 1.

        Returns:
            The feedback string, or an error message.
        """
        # Ensure the user is authenticated and headers are available
        # #user_data = login_check()
        # if not user_data:
        #     return "Failed to authenticate. Cannot get feedback details."

        headers = get_auth_headers()
        if not headers:
            return "Authentication headers missing. Cannot get feedback details."
        sequence_number = 2
        test_case_id = 1
        # Retrieve the stored job_id
        job_id = get_job_id()
        if not job_id:
            return "No job_id found in session. Start generation first to obtain a job_id."

        url = BASE_URL + "feedback_details"
        payload = {
            "job_id": job_id,
            "sequence_number": sequence_number,
            "test_case_id": test_case_id,
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            feedback = data.get("feedback")

            if feedback is not None:
                # If the feedback is structured data, pretty-print it
                if isinstance(feedback, (dict, list)):
                    import json

                    return json.dumps(feedback, ensure_ascii=False, indent=2)
                return str(feedback)

            return f"No 'feedback' in response. Response: {response.text}"

        except requests.RequestException as e:
            return f"Failed to get feedback details. Error: {str(e)}"

    import os
    import requests

    # Constants

    @mcp.tool()
    def save_feedback_test_steps(
            test_case_name: str,
            test_case_description: str,
            test_steps: str,
            refinement_text: str = ""
    ) -> str:
        """
        Saves feedback test steps by first calling getAETestcase to generate test JSON,
        then saving it via save_feedback_steps API, and finally sending to validation.

        Args:
            test_case_name: Name of the test case
            test_case_description: Description of the test case
            test_steps: Test steps as a string (newline-separated steps)
            refinement_text: Any refinement comments (optional)

        Returns:
            Success message with response or detailed error message
        """

        # STEP 1: Call getAETestcase to generate test JSON
        test_case_id = 1
        sequence_no = 2
        if refinement_text is "":
            refinement_text = "N/A"
        try:
            url_ae = BASE_FRONTEND_URL + "getAETestcase_mcp"
            if refinement_text is "":
                refinement_text="N/A"

            # Build the genAITestCases string
            prefix_tc = f"Test Case: {test_case_description}\nFile Name: {test_case_name}\n"
            suffix_tc = "\n<<END>>"
            test_steps_list = test_steps.splitlines()
            test_steps_n = ""
            for i in range(len(test_steps_list)):
                test_steps_n += str(i + 1) + ". " + test_steps_list[i] + "\n"

            gen_ai_test_cases = prefix_tc + test_steps_n + suffix_tc
            form_data = {
                "user_id": "admin",
                "project_id": get_current_project(),
                "application": SELECTED_APPLICATION,
                "genAITestCases": gen_ai_test_cases
            }

            # Send as form data
            response = requests.post(url_ae, data=form_data)
            response.raise_for_status()

            test_json = response.text

            # Check if result starts with "Error:"
            if test_json.startswith("Error:"):
                return f"Failed to generate test JSON: {test_json}"

        except requests.HTTPError as e:
            return f"Failed to call getAETestcase: HTTP error {e.response.status_code}. Response: {e.response.text}"
        except requests.RequestException as e:
            return f"Failed to call getAETestcase: Network error. Error: {str(e)}"
        except Exception as e:
            return f"Failed to call getAETestcase: Unexpected error. Error: {str(e)}"

        # STEP 2: Save feedback steps with the generated test JSON
        try:
            headers = get_auth_headers()
            if not headers:
                return "Failed to save feedback: Authentication headers missing."

            job_id = get_job_id()
            if not job_id:
                return "Failed to save feedback: No job_id found in session. Start generation first."

            url_save = BASE_URL + "save_feedback_steps"

            payload = {
                "job_id": job_id,
                "sequence_no": sequence_no,
                "test_case_id": test_case_id,
                "test_steps": test_steps_list,
                "test_json": test_json,
                "baseline_json": test_json,
                "refinement_text": refinement_text,
            }

            response = requests.post(url_save, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        except requests.HTTPError as e:
            return f"Failed to save feedback: HTTP error {e.response.status_code}. Response: {e.response.text}"
        except requests.RequestException as e:
            return f"Failed to save feedback: Network error. Error: {str(e)}"
        except Exception as e:
            return f"Failed to save feedback: Unexpected error. Error: {str(e)}"

        # STEP 3: Send to validation
        try:
            url_validation = BASE_URL + f"sendToValidation/{job_id}"

            validation_payload = {
                "send_to_validation_or_refine": "Validation",  # or "refine" - please confirm which one you need
                "test_case_id": "test_case_"+str(test_case_id),
                "test_case_name": test_case_name
            }

            response = requests.post(url_validation, json=validation_payload, headers=headers)
            response.raise_for_status()
            validation_data = response.json()

            # Return combined success message
            import json
            result_message = f"Successfully saved feedback for test case '{test_case_name}' (ID: {test_case_id})\n\n"
            result_message += "Save Feedback Response:\n" + json.dumps(data, ensure_ascii=False, indent=2)
            result_message += "\n\nValidation Response:\n" + json.dumps(validation_data, ensure_ascii=False, indent=2)




            # def _get_user_input(self, job_id, data: dict = Body(...), token: str = Depends(jwt_required)):
            #     j_id = int(job_id)
            #     if j_id not in self.jobs:
            #         return JSONResponse(content={"error": "Job not found"}, status_code=404)
            #     input_from_user = data.get('user_input')

            #return result_message

        except requests.HTTPError as e:
            return f"Feedback saved but failed to send to validation: HTTP error {e.response.status_code}. Response: {e.response.text}"
        except requests.RequestException as e:
            return f"Feedback saved but failed to send to validation: Network error. Error: {str(e)}"
        except Exception as e:
            return f"Feedback saved but failed to send to validation: Unexpected error. Error: {str(e)}"

        try:
            url_user_input = BASE_URL + f"/userInput/{job_id}"

            user_input_payload = {
                "user_input": "Continue",  # or "refine" - please confirm which one you need
            }

            response = requests.post(url_user_input, json=user_input_payload, headers=headers)
            response.raise_for_status()
            user_input_data = response.json()
            return result_message


        except requests.HTTPError as e:
            return f"Feedback saved but failed to send to validation (Continue): HTTP error {e.response.status_code}. Response: {e.response.text}"
        except requests.RequestException as e:
            return f"Feedback saved but failed to send to validation (Continue): Network error. Error: {str(e)}"
        except Exception as e:
            return f"Feedback saved but failed to send to validation (Continue): Unexpected error. Error: {str(e)}"


