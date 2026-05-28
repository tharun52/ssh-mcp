"""
Shell tools — run commands and scripts on the remote VM.
"""

import logging
import uuid

from connection import pool, run

log = logging.getLogger("ssh-mcp")


def register(mcp):

    @mcp.tool(name="ssh_run_command")
    def run_command(command: str, sudo: bool = False) -> dict:
        """Execute a shell command on the remote VM via SSH. sudo runs the command as root (default: false). Returns a dict with keys: stdout (str), stderr (str), exit_code (int)."""
        try:
            return run(f"sudo {command}" if sudo else command)
        except Exception as exc:
            log.exception("SSH command failed")
            return {"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1}

    @mcp.tool(name="ssh_run_command_with_timeout")
    def run_command_with_timeout(command: str, timeout: int, sudo: bool = False) -> dict:
        """Execute a shell command on the remote VM with a custom timeout (seconds). sudo runs the command as root (default: false). Returns a dict with keys: stdout (str), stderr (str), exit_code (int)."""
        try:
            return run(f"sudo {command}" if sudo else command, timeout=timeout)
        except Exception as exc:
            log.exception("SSH command failed")
            return {"error": str(exc), "stdout": "", "stderr": "", "exit_code": -1}

    @mcp.tool(name="ssh_run_script")
    def run_script(content: str, interpreter: str = "bash", timeout: int = 30, sudo: bool = False, working_dir: str = "/tmp") -> dict:
        """Upload a script to the remote VM and execute it in one call. interpreter can be bash, python3, sh, etc. (default: bash). timeout is max seconds to wait (default: 30). sudo runs as root (default: false). working_dir is where the script is written (default: /tmp). Returns a dict with keys: stdout (str), stderr (str), exit_code (int)."""
        remote_path = f"{working_dir}/_mcp_{uuid.uuid4().hex}.script"
        prefix = "sudo " if sudo else ""
        try:
            client, sftp = pool.get_sftp()
        except Exception as exc:
            log.exception("run_script failed: could not open SFTP channel")
            return {"error": f"Failed to open SFTP channel — is SFTP enabled on the remote VM? ({exc})", "stdout": "", "stderr": "", "exit_code": -1}
        try:
            with sftp.open(remote_path, "w") as f:
                f.write(content)
        except Exception as exc:
            log.exception("run_script failed: could not write script to remote")
            return {"error": f"Failed to write script to {remote_path} on remote VM: {exc}", "stdout": "", "stderr": "", "exit_code": -1}
        finally:
            sftp.close()
            pool.release()
        try:
            return run(f"{prefix}{interpreter} {remote_path}; rm -f {remote_path}", timeout=timeout)
        except Exception as exc:
            log.exception("run_script failed: could not execute script")
            return {"error": f"Failed to execute script on remote VM: {exc}", "stdout": "", "stderr": "", "exit_code": -1}

