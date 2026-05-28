"""
SCP tools — upload and download files via SFTP, plus local workspace operations.
"""

import logging

from config import FILE_PATH, HOST_IP
from connection import pool

log = logging.getLogger("ssh-mcp")


def register(mcp):

    @mcp.tool(name="ssh_scp_upload")
    def scp_upload(local_filename: str, remote_path: str) -> dict:
        """Upload a file from the container's FILE_PATH directory to an absolute path on the remote VM. local_filename is resolved relative to FILE_PATH (default: /transfers). Returns a dict with keys: success (bool), size (int bytes) on success, or error (str) on failure."""
        local_path = (FILE_PATH / local_filename).resolve()
        if not local_path.is_relative_to(FILE_PATH.resolve()):
            return {"error": "Path escapes workspace directory"}
        if not local_path.exists():
            return {"error": f"File not found in FILE_PATH: {local_path}"}
        client, sftp = None, None
        try:
            client, sftp = pool.get_sftp()
            sftp.put(str(local_path), remote_path)
            size = local_path.stat().st_size
            log.info("Uploaded %s -> %s:%s (%d bytes)", local_path, HOST_IP, remote_path, size)
            return {"success": True, "size": size}
        except Exception as exc:
            log.exception("SCP upload failed")
            return {"error": str(exc)}
        finally:
            if sftp:
                sftp.close()
            if client:
                pool.release()

    @mcp.tool(name="ssh_scp_download")
    def scp_download(remote_path: str, local_filename: str) -> dict:
        """Download a file from an absolute path on the remote VM into the container's FILE_PATH directory. local_filename is the name to save it as inside FILE_PATH (default: /transfers). Returns a dict with keys: success (bool), local_path (str), size (int bytes) on success, or error (str) on failure."""
        local_path = FILE_PATH / local_filename
        client, sftp = None, None
        try:
            client, sftp = pool.get_sftp()
            sftp.get(remote_path, str(local_path))
            size = local_path.stat().st_size
            log.info("Downloaded %s:%s -> %s (%d bytes)", HOST_IP, remote_path, local_path, size)
            return {"success": True, "local_path": str(local_path), "size": size}
        except Exception as exc:
            log.exception("SCP download failed")
            return {"error": str(exc)}
        finally:
            if sftp:
                sftp.close()
            if client:
                pool.release()

    @mcp.tool(name="workspace_list")
    def workspace_list() -> dict:
        """List files in the local workspace (FILE_PATH). Returns a dict with key: files (list of str filenames) on success, or error (str) on failure."""
        try:
            entries = [p.name for p in sorted(FILE_PATH.iterdir())]
            return {"files": entries}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool(name="workspace_read")
    def workspace_read(filename: str) -> dict:
        """Read a file from the local workspace (FILE_PATH). Returns a dict with key: content (str) on success, or error (str) on failure."""
        local_path = (FILE_PATH / filename).resolve()
        if not local_path.is_relative_to(FILE_PATH.resolve()):
            return {"error": "Path escapes workspace directory"}
        try:
            return {"content": local_path.read_text()}
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool(name="workspace_write")
    def workspace_write(filename: str, content: str) -> dict:
        """Write content to a file in the local workspace (FILE_PATH), creating or overwriting it. Returns a dict with key: success (bool), size (int bytes) on success, or error (str) on failure."""
        local_path = (FILE_PATH / filename).resolve()
        if not local_path.is_relative_to(FILE_PATH.resolve()):
            return {"error": "Path escapes workspace directory"}
        try:
            local_path.write_text(content)
            return {"success": True, "size": local_path.stat().st_size}
        except Exception as exc:
            return {"error": str(exc)}
