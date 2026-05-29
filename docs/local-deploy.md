# Local Deployment — Docker

Run the SSH MCP server locally as a Docker container and connect it to Claude Code or Claude Desktop.

## 1. Clone

```bash
git clone https://github.com/tharun52/ssh-mcp.git
cd ssh-mcp
```

## 2. Build

```bash
docker build -t ssh-mcp .
```

## 3. Run

Pick the auth method that fits your setup.

**PEM key file (most common)**

```bash
docker run -p 8000:8000 \
  -e HOST_IP=<vm-ip> \
  -e USERNAME=ubuntu \
  -e SSH_KEY="$(cat /path/to/key.pem)" \
  ssh-mcp
```

**AWS Secrets Manager**

```bash
docker run -p 8000:8000 \
  -e HOST_IP=<vm-ip> \
  -e USERNAME=ubuntu \
  -e SECRET_NAME=ssh-mcp-key \
  -e SECRET_REGION=us-east-1 \
  -v ~/.aws:/root/.aws:ro \
  ssh-mcp
```

**S3-hosted PEM key**

```bash
docker run -p 8000:8000 \
  -e HOST_IP=<vm-ip> \
  -e USERNAME=ubuntu \
  -e S3_BUCKET=<bucket> \
  -e S3_KEY=<path/to/key.pem> \
  -v ~/.aws:/root/.aws:ro \
  ssh-mcp
```

**With a shared file transfer directory**

Add `-v /local/dir:/transfers` to any of the above to persist workspace files on the host:

```bash
docker run -p 8000:8000 \
  -e HOST_IP=<vm-ip> \
  -e USERNAME=ubuntu \
  -e SSH_KEY="$(cat /path/to/key.pem)" \
  -v /local/dir:/transfers \
  ssh-mcp
```

## 4. Verify

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "host": "<vm-ip>",
  "ssh_port": 22,
  "user": "ubuntu",
  "file_path": "/transfers",
  "idle_timeout": 60,
  "connected": false
}
```

## 5. Connect to Claude Code

Add the server to your Claude Code project config:

```bash
claude mcp add ssh-mcp --transport http http://localhost:8000/mcp
```

Or add it manually to `.claude/mcp.json` in your project:

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## 6. Connect to Claude Desktop

Add the following to your Claude Desktop config file.

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "HOST_IP=<vm-ip>",
        "-e", "USERNAME=ubuntu",
        "-e", "SSH_KEY=<your-pem-key-contents>",
        "-p", "8000:8000",
        "ssh-mcp"
      ]
    }
  }
}
```

Alternatively, if you prefer to keep the container running separately and connect over HTTP, use an `httpServer` entry instead (requires Claude Desktop to support HTTP MCP transport):

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Restart Claude Desktop after editing the config.
