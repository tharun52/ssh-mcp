# SSH MCP Server

An MCP (Model Context Protocol) server that exposes SSH operations as tools, letting AI agents run commands, execute scripts, and transfer files on a remote VM over SSH.

Connects to any SSH-accessible machine. Supports key-based auth, password auth, AWS Secrets Manager, and S3-hosted keys.

## Tools

### Shell

| Tool | Description |
|---|---|
| `ssh_run_command` | Run a shell command on the remote VM. Returns `stdout`, `stderr`, `exit_code`. |
| `ssh_run_command_with_timeout` | Same as above with a custom timeout (seconds). |
| `ssh_run_script` | Write a script to the remote VM and execute it in one call. Supports any interpreter (`bash`, `python3`, `sh`, etc.), optional `sudo`, and configurable `working_dir`. |

### File Transfer (SCP)

| Tool | Description |
|---|---|
| `ssh_scp_upload` | Push a file from the local workspace (`FILE_PATH`) to an absolute path on the remote VM. |
| `ssh_scp_download` | Pull a file from an absolute path on the remote VM into the local workspace (`FILE_PATH`). |

### Workspace (local `FILE_PATH`)

| Tool | Description |
|---|---|
| `workspace_list` | List all files in the local workspace. |
| `workspace_read` | Read a file from the local workspace by filename. |
| `workspace_write` | Write or overwrite a file in the local workspace. |

The workspace is the staging area for SCP transfers. In Docker, mount a host directory to it. In AgentCore, attach an S3 Files or EFS access point.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `HOST_IP` | yes | — | IP or hostname of the remote VM |
| `USERNAME` | yes | — | SSH user on the remote VM |
| `SECRET_NAME` | one of four | — | AWS Secrets Manager secret name (JSON with `SSH_KEY` or `PASSWORD`) |
| `SECRET_REGION` | no | `us-east-1` | Region for Secrets Manager |
| `S3_BUCKET` + `S3_KEY` | one of four | — | S3 object path to a PEM key file |
| `AWS_REGION` | no | `us-east-1` | Region for S3 |
| `SSH_KEY` | one of four | — | PEM private key string (use `\n` for newlines in `.env` files) |
| `PASSWORD` | one of four | — | SSH password |
| `PORT` | no | `8000` | HTTP port this server listens on |
| `SSH_PORT` | no | `22` | SSH port on the remote VM |
| `FILE_PATH` | no | `/transfers` | Local staging directory for SCP and workspace tools |
| `IDLE_TIMEOUT` | no | `60` | Seconds before an idle SSH connection is closed |

**Auth priority:** `SECRET_NAME` → `S3_BUCKET`+`S3_KEY` → `SSH_KEY` → `PASSWORD`

## MCP Endpoint

```
http://localhost:8000/mcp
```

Health check:

```
http://localhost:8000/health
```

## Deployment

- [local-deploy.md](./local-deploy.md) — Docker and local Python setup
- [agentcore-deploy.md](./agentcore-deploy.md) — AWS AgentCore Runtime deployment with VPC, S3 Files, and Gateway
