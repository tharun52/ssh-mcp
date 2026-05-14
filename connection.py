"""
SSH connection — single lazy connection with idle timeout.
"""

import io
import logging
import threading
import time

import paramiko

from config import HOST_IP, USERNAME, SSH_KEY, PASSWORD, SSH_PORT, IDLE_TIMEOUT

log = logging.getLogger("ssh-mcp")

# Key loading (once at import time)
_pkey: paramiko.PKey | None = None
if SSH_KEY:
    for _key_class in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
        try:
            _pkey = _key_class.from_private_key(io.StringIO(SSH_KEY))
            break
        except Exception:
            continue
    if _pkey is None:
        raise ValueError("Could not load SSH_KEY — unsupported key type or malformed key")

# Connection
def _new_client() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if _pkey:
        client.connect(HOST_IP, port=SSH_PORT, username=USERNAME, pkey=_pkey)
    else:
        client.connect(HOST_IP, port=SSH_PORT, username=USERNAME, password=PASSWORD)
    return client


class SSHConnection:
    """
    Single lazy SSH connection — created on first use and closed automatically
    after IDLE_TIMEOUT seconds of inactivity.
    """

    def __init__(self, idle_timeout: int) -> None:
        self._idle_timeout = idle_timeout
        self._client: paramiko.SSHClient | None = None
        self._last_released: float = 0.0
        self._lock = threading.Lock()
        self._reaper = threading.Thread(target=self._reap_idle, daemon=True)
        self._reaper.start()
        log.info("SSH connection ready — lazy, idle_timeout=%ds (port %d)", idle_timeout, SSH_PORT)

    def acquire(self) -> paramiko.SSHClient:
        with self._lock:
            if self._client is not None:
                transport = self._client.get_transport()
                if transport and transport.is_active():
                    log.info("Reusing existing SSH connection")
                    return self._client
                else:
                    log.info("Existing SSH connection is dead, reconnecting")
                    try:
                        self._client.close()
                    except Exception:
                        pass
                    self._client = None

            log.info("Opening new SSH connection")
            self._client = _new_client()
            return self._client

    def release(self) -> None:
        with self._lock:
            self._last_released = time.monotonic()

    def get_sftp(self) -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
        client = self.acquire()
        sftp = client.open_sftp()
        return client, sftp

    def _reap_idle(self) -> None:
        while True:
            time.sleep(10)
            with self._lock:
                if (
                    self._client is not None
                    and self._last_released > 0
                    and time.monotonic() - self._last_released > self._idle_timeout
                ):
                    log.info("Closing idle SSH connection (exceeded %ds timeout)", self._idle_timeout)
                    try:
                        self._client.close()
                    except Exception:
                        pass
                    self._client = None
                    self._last_released = 0.0

    @property
    def is_connected(self) -> bool:
        with self._lock:
            if self._client is None:
                return False
            transport = self._client.get_transport()
            return transport is not None and transport.is_active()


# Singleton used by all tools
pool = SSHConnection(IDLE_TIMEOUT)


def run(command: str, timeout: int = 30) -> dict:
    client = pool.acquire()
    try:
        log.info("Executing: %s", command)
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        log.info("exit_code=%d stdout=%.120s stderr=%.120s", exit_code, out, err)
        return {"stdout": out, "stderr": err, "exit_code": exit_code}
    finally:
        pool.release()
