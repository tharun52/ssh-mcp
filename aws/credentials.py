"""
AWS credential helpers — fetch SSH key or password from Secrets Manager or S3.
"""

import json
import logging
import os

log = logging.getLogger("ssh-mcp")


def _boto_client(service: str):
    import boto3
    region = os.environ.get("SECRET_REGION", os.environ.get("AWS_REGION", "us-east-1"))
    return boto3.client(service, region_name=region)


def load_from_secrets_manager(secret_name: str) -> dict:
    """
    Fetch a secret from AWS Secrets Manager.
    Returns a dict with either 'SSH_KEY' or 'PASSWORD'.
    """
    log.info("Loading credentials from Secrets Manager: %s", secret_name)
    client = _boto_client("secretsmanager")
    secret = json.loads(client.get_secret_value(SecretId=secret_name)["SecretString"])
    if "SSH_KEY" not in secret and "PASSWORD" not in secret:
        raise RuntimeError("Secret must contain either 'SSH_KEY' or 'PASSWORD' key.")
    return secret


def load_from_s3(bucket: str, key: str) -> dict:
    """
    Fetch an SSH private key file from S3.
    Returns a dict with 'SSH_KEY'.
    """
    log.info("Loading SSH key from S3: s3://%s/%s", bucket, key)
    client = _boto_client("s3")
    obj = client.get_object(Bucket=bucket, Key=key)
    return {"SSH_KEY": obj["Body"].read().decode("utf-8")}
