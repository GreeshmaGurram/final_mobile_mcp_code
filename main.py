from fastmcp import FastMCP
#from execution.run_engine import run_phase
from phases.definitions.generation import GenerationPhase
# from tools.generation_tools import add_numbers
import logging
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from tools.generation_tools import generation_tools_registration
from tools.feedback_tools import feedback_tools_registration
from tools.starter_tools import starter_tools_registration
from tools.base import base_tools_registration
import httpx

# Add logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP instance
mcp = FastMCP("PhaseBasedMCP")

# Register tool
generation_tools_registration(mcp)
feedback_tools_registration(mcp)
starter_tools_registration(mcp)
base_tools_registration(mcp)
# Register prompt
# @mcp.prompt()
# def run(prompt: str) -> str:
#     return run_phase(
#         phase=GenerationPhase(),
#         user_prompt=prompt
#     )


if __name__ == "__main__":
    logger.info("Starting MCP server with CORS proxy...")

    # Create a wrapper FastAPI app with CORS
    app = FastAPI()

    # Add CORS middleware to the wrapper
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

    # Start the MCP server in a thread on a different port
    import threading


    def run_mcp_server():
        mcp.run(
            transport="http",
            host="127.0.0.1",
            port=3334  # Different port for internal MCP server
        )


    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()

    # Give the MCP server time to start
    import time

    time.sleep(2)


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

        # Forward the request to the actual MCP server
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


    # Run the CORS-enabled proxy on port 3333
    logger.info("CORS proxy running on http://127.0.0.1:3333")
    logger.info("Connect MCP Inspector to: http://127.0.0.1:3333/mcp")

    uvicorn.run(app, host="127.0.0.1", port=3333)