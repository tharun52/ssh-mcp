"""
SSH MCP Server — entry point.

Environment variables
---------------------
HOST_IP         IP address of the target VM (required)
USERNAME        SSH username (required)
SSH_KEY         Private key content (PEM string) — takes priority over PASSWORD
PASSWORD        SSH password — used if SSH_KEY is not set
PORT            Listening port (default: 8000)
SSH_PORT        SSH port on the target VM (default: 22)
FILE_PATH       Local directory for SCP uploads/downloads (default: /transfers)
IDLE_TIMEOUT    Seconds of inactivity before connection is closed (default: 60)
"""

import logging

import uvicorn
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import HOST_IP, SSH_PORT, USERNAME, FILE_PATH, IDLE_TIMEOUT, PORT
from connection import pool
from tools import shell, scp

log = logging.getLogger("ssh-mcp")

# ---------------------------------------------------------------------------
# FastMCP + tool registration
# ---------------------------------------------------------------------------
mcp = FastMCP("ssh-mcp")
shell.register(mcp)
scp.register(mcp)


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------
async def health(request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "healthy",
        "host": HOST_IP,
        "ssh_port": SSH_PORT,
        "user": USERNAME,
        "file_path": str(FILE_PATH),
        "idle_timeout": IDLE_TIMEOUT,
        "connected": pool.is_connected,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log.info("Starting SSH MCP on port %d | host=%s user=%s", PORT, HOST_IP, USERNAME)

    mcp_app = mcp.http_app(path="/mcp", stateless_http=True)
    mcp_app.add_route("/health", health, methods=["GET"])

    uvicorn.run(mcp_app, host="0.0.0.0", port=PORT)
