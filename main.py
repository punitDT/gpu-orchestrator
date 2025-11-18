"""
FastAPI GPU Orchestrator Application.
Manages Vast.ai GPU instances for on-demand image generation.
"""
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import settings
from gpu_manager import GPUManager
from logging_config import setup_logging, get_logger

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

# Global GPU manager instance
gpu_manager: Optional[GPUManager] = None

# Simple in-memory rate limiting
rate_limit_store: Dict[str, list] = {}


class GenerateLogoRequest(BaseModel):
    """Request model for logo generation."""
    prompt: str = Field(..., min_length=1, max_length=1000, description="Text prompt for logo generation")
    width: Optional[int] = Field(512, ge=256, le=2048, description="Image width")
    height: Optional[int] = Field(512, ge=256, le=2048, description="Image height")
    num_inference_steps: Optional[int] = Field(20, ge=1, le=100, description="Number of inference steps")


class StandardResponse(BaseModel):
    """Standard API response format."""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


async def idle_shutdown_task():
    """Background task to shutdown GPU after idle timeout."""
    global gpu_manager
    
    logger.info("Idle shutdown task started")
    
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            if gpu_manager and gpu_manager.should_shutdown():
                is_running = await gpu_manager.is_gpu_running(use_cache=False)
                
                if is_running:
                    logger.info("Initiating idle GPU shutdown")
                    await gpu_manager.stop_gpu()
                    
        except Exception as e:
            logger.error(f"Error in idle shutdown task: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global gpu_manager
    
    # Startup
    logger.info("Starting GPU Orchestrator application", extra={
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
    })
    
    gpu_manager = GPUManager()
    
    # Start background task
    shutdown_task = asyncio.create_task(idle_shutdown_task())
    
    yield
    
    # Shutdown
    logger.info("Shutting down GPU Orchestrator application")
    shutdown_task.cancel()
    try:
        await shutdown_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Configure CORS
origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_rate_limit(client_id: str) -> bool:
    """
    Simple in-memory rate limiting.

    Args:
        client_id: Client identifier (IP address)

    Returns:
        True if within rate limit, False otherwise
    """
    now = datetime.now(timezone.utc)
    minute_ago = now.timestamp() - 60
    
    # Clean old entries
    if client_id in rate_limit_store:
        rate_limit_store[client_id] = [
            ts for ts in rate_limit_store[client_id] if ts > minute_ago
        ]
    else:
        rate_limit_store[client_id] = []
    
    # Check limit
    if len(rate_limit_store[client_id]) >= settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
        return False
    
    # Add current request
    rate_limit_store[client_id].append(now.timestamp())
    return True


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    client_ip = request.client.host
    
    if not check_rate_limit(client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "status": "error",
                "message": "Rate limit exceeded. Please try again later.",
                "data": None,
            },
        )
    
    response = await call_next(request)
    return response


@app.get("/health", response_model=StandardResponse)
async def health_check():
    """Health check endpoint."""
    return StandardResponse(
        status="healthy",
        message="Service is running",
        data={
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "version": settings.APP_VERSION,
        },
    )


@app.get("/gpu-status", response_model=StandardResponse)
async def get_gpu_status():
    """
    Get current GPU status.

    Returns:
        GPU status information
    """
    request_id = str(uuid.uuid4())

    try:
        logger.info("GPU status check requested", extra={"request_id": request_id})

        is_running = await gpu_manager.is_gpu_running(use_cache=True)
        idle_time = gpu_manager.get_idle_time_seconds()

        return StandardResponse(
            status="success",
            message="GPU status retrieved",
            data={
                "gpu_running": is_running,
                "idle_time_seconds": round(idle_time, 2) if idle_time else None,
                "last_request_time": gpu_manager.last_request_time.isoformat() + "Z"
                    if gpu_manager.last_request_time else None,
            },
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Failed to get GPU status: {e}", exc_info=True, extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve GPU status",
        )


@app.post("/generate-logo", response_model=StandardResponse)
async def generate_logo(request: GenerateLogoRequest):
    """
    Generate a logo using the GPU worker.

    Args:
        request: Logo generation request

    Returns:
        Generated logo or warmup status
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    try:
        logger.info(
            "Logo generation requested",
            extra={
                "request_id": request_id,
                "prompt": request.prompt[:100],  # Log first 100 chars
            },
        )

        # Check if GPU is running
        is_running = await gpu_manager.is_gpu_running(use_cache=True)

        if not is_running:
            logger.info("GPU is not running, starting it", extra={"request_id": request_id})

            # Start GPU
            await gpu_manager.start_gpu()

            # Return warming up status
            return StandardResponse(
                status="warming_up",
                message="GPU is starting up. Please retry in a moment.",
                data={
                    "eta_seconds": 15,
                    "retry_after": 15,
                },
                request_id=request_id,
            )

        # Check if GPU worker is ready
        logger.info("Checking GPU worker health", extra={"request_id": request_id})

        try:
            async with asyncio.timeout(5):
                is_ready = await gpu_manager.wait_until_ready(timeout_seconds=5)
        except asyncio.TimeoutError:
            is_ready = False

        if not is_ready:
            logger.warning("GPU worker not ready yet", extra={"request_id": request_id})
            return StandardResponse(
                status="warming_up",
                message="GPU is still warming up. Please retry in a moment.",
                data={
                    "eta_seconds": 10,
                    "retry_after": 10,
                },
                request_id=request_id,
            )

        # Forward inference request
        logger.info("Forwarding to GPU worker", extra={"request_id": request_id})

        result = await gpu_manager.forward_inference(
            prompt=request.prompt,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
        )

        # Calculate duration
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        logger.info(
            "Logo generation completed",
            extra={"request_id": request_id, "duration_ms": round(duration_ms, 2)},
        )

        return StandardResponse(
            status="success",
            message="Logo generated successfully",
            data=result,
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Logo generation failed: {e}",
            exc_info=True,
            extra={"request_id": request_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logo generation failed: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )

