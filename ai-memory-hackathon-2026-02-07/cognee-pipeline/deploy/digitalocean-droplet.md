# Deploy to DigitalOcean Droplet

Full local setup on a Droplet with GPU for fast inference.

## Create Droplet

```bash
# GPU Droplet (recommended for LLM)
doctl compute droplet create cognee-server \
  --image docker-20-04 \
  --size gpu-h100x1-80gb \
  --region nyc1 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# Or CPU-only (cheaper, slower)
doctl compute droplet create cognee-server \
  --image docker-20-04 \
  --size s-4vcpu-8gb \
  --region nyc1 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)
```

## Setup Script

SSH into your Droplet and run:

```bash
#!/bin/bash

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull nomic-embed-text
ollama pull qwen3:4b

# Clone project
git clone https://github.com/your-org/cognee-pipeline.git
cd cognee-pipeline/examples/local

# Start Qdrant
docker compose up -d

# Setup Python
apt install -y python3.12 python3.12-venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Restore vectors
cp .env.example .env
python restore_snapshots.py

# Test
python demo.py
```

## Run as Service

Create `/etc/systemd/system/cognee.service`:

```ini
[Unit]
Description=Cognee Search API
After=docker.service ollama.service

[Service]
WorkingDirectory=/root/cognee-pipeline/examples/local
ExecStart=/root/cognee-pipeline/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl enable cognee
systemctl start cognee
```

## Firewall

```bash
ufw allow 22
ufw allow 8080
ufw enable
```

## Access

Your API is now at: `http://<droplet-ip>:8080`
