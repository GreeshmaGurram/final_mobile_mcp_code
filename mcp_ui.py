
import json

import mcp
import requests
import os
from fastapi import FastAPI, Request, Query, Body
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn
from pydantic import BaseModel
from starlette.responses import JSONResponse

from tools import generation_tools
from tools.base import get_job_id, get_status, get_auth_headers
from tools.generation_tools import generation_tools_registration

app = FastAPI()

BASE_URL = os.getenv("BASE_URL")
@app.get("/home", response_class=HTMLResponse)
async def home():
    """Serve the index.html page"""
    html_file = Path("index.html")

    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    else:
        return """
        <html>
            <body>
                <h1>Error: index.html not found</h1>
                <p>Please make sure index.html is in the same directory as this Python file.</p>
            </body>
        </html>
        """


@app.get("/")
async def root():
    """Root endpoint - redirect info"""
    return {
        "message": "Welcome to Test Automation API",
        "info": "Navigate to /home to view the chat interface"
    }

class UserInput(BaseModel):
    user_input: str

@app.post("/start-generation")
async def start_generation(payload: UserInput):
    """
    Receives user story → calls start_test_step_generation → returns job_id
    """
    result_str = generation_tools.start_test_step_generation(payload.user_input)

    if "Successfully started" in result_str:
        job_id = get_job_id()  # should be already set by the function
        return {
            "success": True,
            "job_id": job_id,
            "message": "Generation job started"
        }
    else:
        return {
            "success": False,
            "error": result_str
        }

@app.post("/getReviews")
async def get_reviews(payload: dict = Body(...)):
    """
    Accepts JSON body: {"job_id": "...", "sequence_number": 2}
    Forwards to real /reviews endpoint.
    """
    job_id = payload.get("job_id")
    sequence_number = payload.get("sequence_number", 2)  # default to 2

    if not job_id:
        return JSONResponse(
            content={"error": "job_id is required in request body"},
            status_code=422
        )

    try:
        headers = get_auth_headers()
        real_response = requests.post(
            BASE_URL + "reviews",
            json={
                "job_id": job_id,
                "sequence_number": sequence_number
            },
            headers=headers,
            timeout=15
        )
        real_response.raise_for_status()
        return real_response.json()

    except requests.RequestException as e:
        return {"error": f"Failed to reach reviews backend: {str(e)}"}
    except Exception as e:
        return {"error": f"Internal error: {str(e)}"}

@app.get("/status")
async def get_job_status(request: Request):
    """
    Proxy endpoint that returns raw status JSON/text from backend
    Frontend polls this every ~1.4 seconds
    """
    job_id = get_job_id()
    if not job_id:
        return {"error": "No active job_id in session"}

    status_str = get_status()   # your existing function

    # Optional: try to return as JSON if possible
    try:
        return json.loads(status_str)
    except:
        return {"raw_status": status_str}


if __name__ == "__main__":
    print("Starting server on http://localhost:8080")
    print("Navigate to http://localhost:8080/home to view the chat interface")
    uvicorn.run(app, host="localhost", port=8080)