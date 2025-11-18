# Quick Start Guide

Get the GPU Orchestrator running in 5 minutes!

## 🚀 Fast Setup

### 1. Install Dependencies (30 seconds)

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure (1 minute)

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
VAST_API_KEY=your_api_key_here
VAST_MACHINE_ID=your_machine_id
GPU_WORKER_URL=http://your-gpu-url:8000
```

### 3. Run (5 seconds)

```bash
./run.sh
```

Or:
```bash
python main.py
```

### 4. Test (30 seconds)

Open another terminal:
```bash
python test_api.py
```

## 📋 API Quick Reference

### Health Check
```bash
curl http://localhost:8080/health
```

### GPU Status
```bash
curl http://localhost:8080/gpu-status
```

### Generate Logo
```bash
curl -X POST http://localhost:8080/generate-logo \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A modern tech logo with blue gradient",
    "width": 512,
    "height": 512,
    "num_inference_steps": 20
  }'
```

## 🌐 Deploy to Fly.io (2 minutes)

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Deploy
fly launch
fly secrets set VAST_API_KEY="your_key"
fly secrets set VAST_MACHINE_ID="your_id"
fly secrets set GPU_WORKER_URL="http://your-url:8000"
fly deploy
```

## 📊 How It Works

1. **Request arrives** → Check if GPU is running
2. **GPU off** → Start it, return "warming_up" status
3. **GPU on** → Forward request, return generated image
4. **Idle timeout** → Auto-shutdown after 120 seconds

## 🔧 Common Issues

**"Connection refused"**
- Make sure server is running: `python main.py`

**"GPU not starting"**
- Check Vast.ai API key in `.env`
- Verify machine ID is correct

**"Timeout waiting for GPU"**
- GPU might need more warmup time
- Check GPU worker is running on Vast.ai

## 📚 Next Steps

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
- Check [README.md](README.md) for full documentation
- Review code in `main.py` and `gpu_manager.py`

## 💡 Tips

- Use `fly logs -f` to monitor production logs
- Adjust `IDLE_SHUTDOWN_SECONDS` to optimize costs
- Enable CORS for your frontend domain in production
- Add authentication before going live

## 🆘 Need Help?

1. Check logs: `fly logs` (production) or console output (local)
2. Verify environment variables: `fly secrets list`
3. Test GPU worker directly: `curl http://your-gpu-url:8000/health`
4. Review Vast.ai console for GPU status

---

**Ready to go!** 🎉

Your GPU orchestrator is now managing on-demand GPU instances automatically.

