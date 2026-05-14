# AgentCore Deployment

Deploy the SSH MCP server as an Amazon Bedrock AgentCore Runtime. AgentCore hosts the container in a managed microVM, handles scaling and session isolation, and exposes it as an MCP endpoint over HTTPS.

> **VPC mode only.** AgentCore Runtime cannot be assigned a public IP in a public subnet. Deploy in a **private subnet** with a **NAT Gateway** for outbound internet access.

## Prerequisites

- AWS CLI configured with sufficient permissions
- Docker with `buildx` support (for cross-platform builds)
- An ECR repository for the image
- A VPC with private subnets and a NAT Gateway
- SSH credentials stored in AWS Secrets Manager (recommended)

---

## 1. Clone

```bash
git clone https://github.com/tharun52/ssh-mcp.git
cd ssh-mcp
```

## 2. ECR Login

```bash
aws ecr get-login-password --region <region> | \
  docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
```

## 3. Build for ARM64 and Push

AgentCore Runtime runs on ARM64 (Graviton). Build the image for `linux/arm64` regardless of your local machine architecture.

```bash
# Create a buildx builder if you don't have one
docker buildx create --use

# Build for ARM64, tag, and push in one step
docker buildx build \
  --platform linux/arm64 \
  -t <account-id>.dkr.ecr.<region>.amazonaws.com/ssh-mcp:latest \
  --push \
  .
```

---

## 4. Store SSH Credentials in Secrets Manager

AgentCore has no access to your local filesystem, so the SSH key must be stored in AWS Secrets Manager. The secret value must be a JSON object with an `SSH_KEY` field.

```bash
# Write the secret JSON
echo "{\"SSH_KEY\": \"$(cat /path/to/key.pem | awk '{printf "%s\\n", $0}')\"}" > /tmp/ssh_secret.json

# Create the secret
aws secretsmanager create-secret \
  --name ssh-mcp-key \
  --region <region> \
  --secret-string file:///tmp/ssh_secret.json

# Clean up
rm /tmp/ssh_secret.json
```

The execution role attached to the runtime must have permission to read this secret:

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:<region>:<account-id>:secret:ssh-mcp-key*"
}
```

---

## 5. Deploy the AgentCore Runtime

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --region <region> \
  --agent-runtime-name "ssh_mcp_server" \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "<account-id>.dkr.ecr.<region>.amazonaws.com/ssh-mcp:latest"
    }
  }' \
  --role-arn "arn:aws:iam::<account-id>:role/<execution-role>" \
  --protocol-configuration '{"serverProtocol": "MCP"}' \
  --network-configuration '{
    "networkMode": "VPC",
    "networkModeConfig": {
      "subnets": ["<private-subnet-id>"],
      "securityGroups": ["<security-group-id>"]
    }
  }' \
  --environment-variables '{
    "HOST_IP": "<vm-ip>",
    "USERNAME": "ubuntu",
    "SECRET_NAME": "ssh-mcp-key",
    "SECRET_REGION": "<region>",
    "PORT": "8000",
    "FILE_PATH": "/mnt/transfers"
  }'
```

> Note: `FILE_PATH` must match the mount path configured in the filesystem section below.

---

## 6. Persistent File Storage (S3 Files)

By default, files written inside a session are lost when the session ends. To persist files across sessions and share them across invocations, attach an **S3 Files** access point.

### Why S3 Files instead of Managed Session Storage

| | Managed Session Storage | S3 Files |
|---|---|---|
| Scope | Per-session only | Shared across all sessions and agents |
| Persistence | Lost after session expires | Permanent (backed by S3) |
| VPC required | No | Yes |
| Access via S3 API | No | Yes |

Managed session storage is suitable for scratch space within a single session. S3 Files is required when files must survive across invocations or be accessible from outside AgentCore.

### Prerequisites for S3 Files

1. **S3 Files file system** — created and backed by an S3 bucket
2. **Mount targets** — deployed in the **same VPC and Availability Zone** as the AgentCore runtime subnets (TCP port 2049 must be open between the runtime security group and the mount target security group)
3. **S3 Files access point** — created on the file system with a POSIX UID/GID matching the container user (typically `0:0` for root)

The execution role also needs these IAM permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3files:ClientMount",
    "s3files:ClientWrite",
    "s3files:GetAccessPoint"
  ],
  "Resource": "<access-point-arn>",
  "Condition": {
    "StringEquals": {
      "s3files:AccessPointArn": "<access-point-arn>"
    }
  }
}
```

### Attach the Access Point to the Runtime

The mount path **must match** the `FILE_PATH` environment variable so the SCP and workspace tools write to the right place.

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --region <region> \
  --agent-runtime-id <runtime-id> \
  --filesystem-configurations '[{
    "s3FilesAccessPoint": {
      "accessPointArn": "<s3-files-access-point-arn>",
      "mountPath": "/mnt/transfers"
    }
  }]'
```

In the console this appears under **Filesystem configuration** when editing the runtime:

- **Filesystem type:** S3 files
- **Mount path:** `/mnt/transfers` ← must equal `FILE_PATH`
- **Access point ARN:** your S3 Files access point ARN

Once attached, `scp_download` writes files to `/mnt/transfers` inside the container, which syncs bidirectionally with the backing S3 bucket. Files written in one session are available in the next.

> **Note:** Files appear in the S3 bucket with eventual consistency — there may be a short delay before they're visible via the S3 console or API. Files are stored under the access point's root directory path, not at the S3 bucket root.

