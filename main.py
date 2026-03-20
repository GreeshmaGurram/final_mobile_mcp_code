from fastmcp import FastMCP
import logging
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import threading
import time

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

# ---- LOGGING ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- MCP INSTANCE ----
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
# =========================================================

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

    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()

    # Give time for MCP server to start
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

        timeout = httpx.Timeout(300.0, connect=60.0)

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

    uvicorn.run(app, host="127.0.0.1", port=3333)