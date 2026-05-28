"""
Background job tools — run commands in the background and check their status.
"""

import logging
import uuid

from connection import run

log = logging.getLogger("ssh-mcp")


def register(mcp):

    @mcp.tool(name="ssh_run_background")
    def run_background(command: str, sudo: bool = False) -> dict:
        """Run a command in the background on the remote VM using nohup. Returns job_id and pid to track the job. Use ssh_check_job to poll status and output."""
        job_id = uuid.uuid4().hex
        out = f"/tmp/_mcp_job_{job_id}.out"
        pid = f"/tmp/_mcp_job_{job_id}.pid"
        exit_f = f"/tmp/_mcp_job_{job_id}.exit"
        prefix = "sudo " if sudo else ""
        cmd = (
            f"nohup bash -c '{prefix}{command}; echo $? > {exit_f}' "
            f"> {out} 2>&1 & echo $! | tee {pid}"
        )
        try:
            result = run(cmd)
            if result["exit_code"] != 0:
                return {"error": f"Failed to start background job: {result['stderr']}"}
            return {"job_id": job_id, "pid": result["stdout"].strip()}
        except Exception as exc:
            log.exception("ssh_run_background failed")
            return {"error": str(exc)}

    @mcp.tool(name="ssh_check_job")
    def check_job(job_id: str) -> dict:
        """Check the status of a background job started with ssh_run_background. Returns status (running/done/failed), current output, and exit_code when done."""
        out = f"/tmp/_mcp_job_{job_id}.out"
        pid_f = f"/tmp/_mcp_job_{job_id}.pid"
        exit_f = f"/tmp/_mcp_job_{job_id}.exit"
        try:
            pid_result = run(f"cat {pid_f} 2>/dev/null")
            if pid_result["exit_code"] != 0:
                return {"error": f"Job {job_id} not found"}

            pid = pid_result["stdout"].strip()
            output_result = run(f"cat {out} 2>/dev/null")
            output = output_result["stdout"]

            exit_result = run(f"cat {exit_f} 2>/dev/null")
            if exit_result["exit_code"] == 0 and exit_result["stdout"].strip() != "":
                exit_code = int(exit_result["stdout"].strip())
                return {
                    "status": "done" if exit_code == 0 else "failed",
                    "pid": pid,
                    "output": output,
                    "exit_code": exit_code,
                }

            alive = run(f"kill -0 {pid} 2>/dev/null && echo running || echo done")
            if alive["stdout"].strip() == "running":
                ps = run(f"ps -p {pid} -o pid,ppid,%cpu,%mem,etime,cmd --no-headers 2>/dev/null")
                process_info = ps["stdout"].strip() if ps["exit_code"] == 0 else None
                return {"status": "running", "pid": pid, "output": output, "process_info": process_info}

            return {"status": "done", "pid": pid, "output": output, "exit_code": None}
        except Exception as exc:
            log.exception("ssh_check_job failed")
            return {"error": str(exc)}
