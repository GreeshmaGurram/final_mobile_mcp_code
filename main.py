from fastmcp import FastMCP
import logging
import uvicorn
import httpx
import threading
import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# ---- NEW IMPORTS (IMPORTANT) ----
from core.shared_state import SharedState
from core.dependencies import (
    log_to_file,
    exec_async,
    parse_ios_version,
    parse_android_version,
    detect_android_devices,
)

# ---- TOOL IMPORTS ----
from tools.locator_tools import locator_tools_registration
from tools.base import base_tools_registration
from core.prompts import generation_agent_prompts
from tools.tsu_tools import tsu_tools_registration
from tools.testcase_tools import testcase_tools_registration
from tools.start_session import start_session_tool_registration
from tools.end_session import end_session_tool_registration
from tools.launch_app import launch_app_tool_registration
from tools.find_element import find_element_tool_registration
from tools.enter_text import enter_text_tool_registration
from tools.get_device_logs import get_device_logs_tool_registration
from tools.get_element_text import get_element_text_tool_registration
from tools.get_page_source import get_page_source_tool_registration
from tools.get_page_source_file import get_page_source_file_tool_registration
from tools.get_screenshot import get_screenshot_tool_registration
from tools.get_screenshot_file import get_screenshot_file_tool_registration
from tools.press_home_button import press_home_button_tool_registration
from tools.simulate_gesture import simulate_gesture_tool_registration
from tools.tap_element import tap_element_tool_registration
from tools.scroll_action import scroll_tool_registration

# ---- LOGGING ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- MCP INSTANCE by name PhaseBasedMCP----
mcp = FastMCP("PhaseBasedMCP")

# =========================================================
# 🔥 NEW: CREATE SHARED STATE + DEPENDENCIES (LIKE TS)
# =========================================================
shared_state = SharedState()

dependencies = {
    "log_to_file": log_to_file,
    "exec_async": exec_async,
    "parse_ios_version": parse_ios_version,
    "parse_android_version": parse_android_version,
    "detect_android_devices": detect_android_devices,
    # Expected by `tools/get_device_logs.py` to locate logs created in `start_session.py`
    "device_log_file_path": str(Path("./logs") / "ios_device.log"),
    "android_log_file_path": str(Path("./logs") / "android_device.log"),
}

# =========================================================
# 🔥 REGISTER TOOLS (PASS PROPS LIKE TS)
# =========================================================
base_tools_registration(mcp)
generation_agent_prompts(mcp)

tsu_tools_registration(mcp)
testcase_tools_registration(mcp)
locator_tools_registration(mcp)

# 🔥 UPDATED: pass shared_state + dependencies
start_session_tool_registration(mcp, shared_state, dependencies)
end_session_tool_registration(mcp, shared_state, dependencies)
launch_app_tool_registration(mcp, shared_state, dependencies)
find_element_tool_registration(mcp, shared_state, dependencies)
enter_text_tool_registration(mcp, shared_state, dependencies)
get_device_logs_tool_registration(mcp, shared_state, dependencies)
get_element_text_tool_registration(mcp, shared_state, dependencies)
get_page_source_tool_registration(mcp, shared_state, dependencies)
get_page_source_file_tool_registration(mcp, shared_state, dependencies)
get_screenshot_tool_registration(mcp, shared_state, dependencies)
get_screenshot_file_tool_registration(mcp, shared_state, dependencies)
press_home_button_tool_registration(mcp, shared_state, dependencies)
simulate_gesture_tool_registration(mcp, shared_state, dependencies)
tap_element_tool_registration(mcp, shared_state, dependencies)
scroll_tool_registration(mcp, shared_state, dependencies)

# =========================================================
#run this code when file matching the name main is run directly and not when imported
if __name__ == "__main__":
    logger.info("Starting MCP server with CORS proxy...")

    # ---- FASTAPI WRAPPER ----
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

    # ---- RUN MCP SERVER IN THREAD ----
    def run_mcp_server():
        mcp.run(
            transport="http",
            host="127.0.0.1",
            port=3334
        )

    #Run MCP server in the bg and FastAPI instance as main thread
    #daemon=True means the thread will run in the background and will not block the main thread
    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()

    # Give the MCP server time to start
    time.sleep(2)

    # ---- PROXY ROUTE ----
    @app.api_route("/mcp", methods=["GET", "POST", "OPTIONS"])
    @app.api_route("/mcp/{path:path}", methods=["GET", "POST", "OPTIONS"])
    async def proxy_mcp(request: Request, path: str = ""):
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )

        url = f"http://127.0.0.1:3334/mcp"
        if path:
            url += f"/{path}"

        # CRITICAL FIX: Set a much longer timeout
        timeout = httpx.Timeout(300.0, connect=60.0)  # 5 minutes total, 60s connect

        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = dict(request.headers)
            headers.pop("host", None)

            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=await request.body(),
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

    # ---- RUN SERVER ----
    logger.info("CORS proxy running on http://127.0.0.1:3333")
    logger.info("Connect MCP Inspector to: http://127.0.0.1:3333/mcp")
    #Run FastAPI server on port 3333 and handles async HTTP requests smoothly
    uvicorn.run(app, host="127.0.0.1", port=3333)


    #MCP server started on port 3334
    #FastAPI server started on port 3333
    #MCP not browser friendly, so requests from Browser/Inspector sent to
    #FastAPI server which then forwards to MCP server