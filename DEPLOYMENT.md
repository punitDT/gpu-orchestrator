# Deployment Guide

## Prerequisites

1. **Vast.ai Account**
   - Sign up at https://vast.ai
   - Get your API key from account settings
   - Rent a GPU instance with your Flux model deployed
   - Note the instance ID and public URL

2. **Fly.io Account**
   - Sign up at https://fly.io
   - Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
   - Login: `fly auth login`

## Local Development

### 1. Setup Environment

```bash
# Clone repository
git clone <your-repo>
cd gpu-orchestrator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### 2. Configure .env

```env
VAST_API_KEY=your_vast_api_key
VAST_MACHINE_ID=123456
GPU_WORKER_URL=http://your-gpu-instance.vast.ai:8000
```

### 3. Run Locally

```bash
# Option 1: Using the startup script
./run.sh

# Option 2: Direct Python
python main.py

# Option 3: With uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

### 4. Test the API

```bash
# Run test script
python test_api.py

# Or manual curl tests
curl http://localhost:8080/health
curl http://localhost:8080/gpu-status
```

## Production Deployment (Fly.io)

### 1. Initialize Fly App

```bash
fly launch
```

When prompted:
- Choose app name (e.g., `gpu-orchestrator`)
- Select region closest to your users
- Don't deploy yet (we need to set secrets first)

### 2. Configure Secrets

```bash
# Set required secrets
fly secrets set VAST_API_KEY="your_vast_api_key_here"
fly secrets set VAST_MACHINE_ID="your_machine_id"
fly secrets set GPU_WORKER_URL="http://your-gpu-worker:8000"

# Optional: Override defaults
fly secrets set IDLE_SHUTDOWN_SECONDS=180
fly secrets set MAX_CONCURRENT_GPU_REQUESTS=5
```

### 3. Review fly.toml

The `fly.toml` is pre-configured with:
- Auto-stop/start machines
- Minimum 0 machines (cost optimization)
- Health checks
- Proper resource allocation

Adjust if needed:
```toml
[vm]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256  # Increase if needed
```

### 4. Deploy

```bash
fly deploy
```

### 5. Verify Deployment

```bash
# Check status
fly status

# View logs
fly logs

# Test the deployed app
curl https://your-app.fly.dev/health
```

### 6. Monitor

```bash
# Real-time logs
fly logs -f

# Check metrics
fly dashboard
```

## Scaling Configuration

### Auto-scaling (Already Configured)

The app automatically scales to 0 when idle and starts on demand:

```toml
auto_stop_machines = "stop"
auto_start_machines = true
min_machines_running = 0
```

### Manual Scaling

```bash
# Scale to specific count
fly scale count 2

# Scale VM resources
fly scale vm shared-cpu-1x --memory 512
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAST_API_KEY` | Yes | - | Vast.ai API key |
| `VAST_MACHINE_ID` | Yes | - | Vast.ai instance ID |
| `GPU_WORKER_URL` | Yes | - | GPU worker endpoint |
| `IDLE_SHUTDOWN_SECONDS` | No | 120 | Auto-shutdown delay |
| `GPU_WARMUP_TIMEOUT_SECONDS` | No | 300 | Max warmup wait time |
| `MAX_CONCURRENT_GPU_REQUESTS` | No | 3 | Parallel request limit |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | No | 60 | Rate limit per IP |
| `LOG_LEVEL` | No | INFO | Logging level |
| `CORS_ORIGINS` | No | * | Allowed CORS origins |

## Troubleshooting

### GPU Not Starting

1. Check Vast.ai API key: `fly secrets list`
2. Verify machine ID is correct
3. Check Vast.ai console for instance status
4. Review logs: `fly logs`

### Timeout Errors

1. Increase `GPU_WARMUP_TIMEOUT_SECONDS`
2. Check GPU worker health endpoint
3. Verify network connectivity to GPU instance

### High Costs

1. Reduce `IDLE_SHUTDOWN_SECONDS` for faster shutdown
2. Verify auto-stop is working: check Fly.io dashboard
3. Monitor GPU usage in Vast.ai console

### Rate Limiting Issues

1. Adjust `RATE_LIMIT_REQUESTS_PER_MINUTE`
2. Implement authentication for production
3. Use Redis for distributed rate limiting (future enhancement)

## Security Best Practices

1. **Never commit .env file**
   - Already in .gitignore
   - Use Fly secrets for production

2. **Restrict CORS in production**
   ```bash
   fly secrets set CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
   ```

3. **Add authentication** (recommended for production)
   - Implement API key authentication
   - Use JWT tokens
   - Add rate limiting per user

4. **Monitor logs**
   - Set up log aggregation
   - Configure alerts for errors
   - Track GPU usage patterns

## Cost Optimization

1. **Fly.io**: Auto-scales to 0, only pay when running
2. **Vast.ai**: Auto-shutdown after idle period
3. **Monitoring**: Track usage patterns to optimize timeouts

Estimated costs:
- Fly.io: ~$0-5/month (minimal usage)
- Vast.ai: ~$0.20-0.50/hour when GPU is running
- Total: Depends on usage patterns

## Next Steps

1. Set up monitoring and alerting
2. Implement authentication
3. Add request queuing with Redis
4. Set up CI/CD pipeline
5. Add integration tests
6. Configure custom domain

