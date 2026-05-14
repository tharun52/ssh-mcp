"""
Shell tools — run commands and scripts on the remote VM.
"""

import logging
import uuid

from connection import run

log = logging.getLogger("ssh-mcp")


def register(mcp):

    @mcp.tool(name="ssh_run_command")
    def run_command(command: str) -> dict:
        """Execute a shell command on the remote VM via SSH. Returns a dict with keys: stdout (str), stderr (str), exit_code (int)."""
        try:
            return run(command)
        except Exception as exc:
            log.exception("SSH command failed")
            return {"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1}

    @mcp.tool(name="ssh_run_command_with_timeout")
    def run_command_with_timeout(command: str, timeout: int) -> dict:
        """Execute a shell command on the remote VM with a custom timeout (seconds). Returns a dict with keys: stdout (str), stderr (str), exit_code (int)."""
        try:
            return run(command, timeout=timeout)
        except Exception as exc:
            log.exception("SSH command failed")
            return {"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1}

    @mcp.tool(name="ssh_run_script")
    def run_script(content: str, interpreter: str = "bash", timeout: int = 30, sudo: bool = False, working_dir: str = "/tmp") -> dict:
        """Upload a script to the remote VM and execute it in one call. interpreter can be bash, python3, sh, etc. (default: bash). timeout is max seconds to wait (default: 30). sudo runs as root (default: false). working_dir is where the script is written (default: /tmp). Returns a dict with keys: stdout (str), stderr (str), exit_code (int)."""
        remote_path = f"{working_dir}/_mcp_{uuid.uuid4().hex}.script"
        escaped = content.replace("'", "'\\''")
        prefix = "sudo " if sudo else ""
        try:
            result = run(f"cat > {remote_path} << 'EOF'\n{escaped}\nEOF")
            if result["exit_code"] != 0:
                return {"error": f"Failed to write script: {result['stderr']}", "stdout": "", "stderr": "", "exit_code": result["exit_code"]}
            return run(f"{prefix}{interpreter} {remote_path}; rm -f {remote_path}", timeout=timeout)
        except Exception as exc:
            log.exception("run_script failed")
            return {"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1}

