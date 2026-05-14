"""
Configuration — loaded from environment variables at import time.
"""

import os
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

log = logging.getLogger("ssh-mcp")

HOST_IP: str = os.environ["HOST_IP"]
USERNAME: str = os.environ["USERNAME"]

# ---------------------------------------------------------------------------
# Credential resolution priority: SECRET_NAME > S3_BUCKET/S3_KEY > SSH_KEY > PASSWORD
# ---------------------------------------------------------------------------
_raw_key: str | None = os.environ.get("SSH_KEY")
PASSWORD: str | None = os.environ.get("PASSWORD")

_secret_name = os.environ.get("SECRET_NAME")
_s3_bucket = os.environ.get("S3_BUCKET")
_s3_key = os.environ.get("S3_KEY")

if _secret_name:
    from aws.credentials import load_from_secrets_manager
    _creds = load_from_secrets_manager(_secret_name)
    _raw_key = _creds.get("SSH_KEY") or _raw_key
    PASSWORD = _creds.get("PASSWORD") or PASSWORD
elif _s3_bucket and _s3_key:
    from aws.credentials import load_from_s3
    _creds = load_from_s3(_s3_bucket, _s3_key)
    _raw_key = _creds.get("SSH_KEY") or _raw_key

if _raw_key:
    _raw_key = _raw_key.replace("\\n", "\n")
    _raw_key = "\n".join(line.strip() for line in _raw_key.splitlines())
SSH_KEY: str | None = _raw_key

PORT: int = int(os.environ.get("PORT", "8000"))
SSH_PORT: int = int(os.environ.get("SSH_PORT", "22"))
FILE_PATH: Path = Path(os.environ.get("FILE_PATH", "/transfers"))
FILE_PATH.mkdir(parents=True, exist_ok=True)
IDLE_TIMEOUT: int = int(os.environ.get("IDLE_TIMEOUT", "60"))

if not SSH_KEY and not PASSWORD:
    raise RuntimeError("Credentials required: set SECRET_NAME, S3_BUCKET+S3_KEY, SSH_KEY, or PASSWORD.")
