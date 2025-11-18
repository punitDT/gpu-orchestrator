"""
GPU Manager for Vast.ai orchestration.
Handles GPU lifecycle, health checks, and inference forwarding.
"""
import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


class GPUManager:
    """Manages Vast.ai GPU instance lifecycle and operations."""
    
    def __init__(self):
        self.last_request_time: Optional[datetime] = None
        self.gpu_status_cache: Optional[Dict[str, Any]] = None
        self.gpu_status_cache_time: Optional[datetime] = None
        self._start_lock = asyncio.Lock()
        self._stop_lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_GPU_REQUESTS)
        
    async def _get_vast_headers(self) -> Dict[str, str]:
        """Get headers for Vast.ai API requests."""
        return {
            "Authorization": f"Bearer {settings.VAST_API_KEY}",
            "Content-Type": "application/json",
        }
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=settings.RETRY_BACKOFF_FACTOR, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def _make_vast_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Make a request to Vast.ai API with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx request
        
        Returns:
            Response JSON data
        """
        url = f"https://console.vast.ai/api/v0/{endpoint}"
        headers = await self._get_vast_headers()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
    
    async def is_gpu_running(self, use_cache: bool = True) -> bool:
        """
        Check if GPU instance is running.
        
        Args:
            use_cache: Whether to use cached status
        
        Returns:
            True if GPU is running, False otherwise
        """
        try:
            # Check cache first
            if use_cache and self.gpu_status_cache_time:
                cache_age = (datetime.now(timezone.utc) - self.gpu_status_cache_time).total_seconds()
                if cache_age < settings.GPU_STATUS_CACHE_SECONDS:
                    status = self.gpu_status_cache.get("actual_status", "stopped")
                    logger.info(
                        "Using cached GPU status",
                        extra={"gpu_status": status, "cache_age_seconds": cache_age},
                    )
                    return status == "running"

            # Fetch fresh status
            response = await self._make_vast_request(
                "GET", f"instances/{settings.VAST_MACHINE_ID}"
            )

            self.gpu_status_cache = response
            self.gpu_status_cache_time = datetime.now(timezone.utc)
            
            status = response.get("actual_status", "stopped")
            logger.info("GPU status fetched", extra={"gpu_status": status})
            
            return status == "running"
            
        except Exception as e:
            logger.error(f"Failed to check GPU status: {e}", exc_info=True)
            return False
    
    async def start_gpu(self) -> Dict[str, Any]:
        """
        Start the GPU instance.
        
        Returns:
            Status information
        """
        async with self._start_lock:
            # Check if already running
            if await self.is_gpu_running(use_cache=False):
                logger.info("GPU already running")
                return {"status": "already_running", "message": "GPU is already running"}
            
            try:
                logger.info("Starting GPU instance", extra={"machine_id": settings.VAST_MACHINE_ID})
                
                await self._make_vast_request(
                    "PUT",
                    f"instances/{settings.VAST_MACHINE_ID}/start/",
                )
                
                # Invalidate cache
                self.gpu_status_cache = None
                self.gpu_status_cache_time = None
                
                logger.info("GPU start command sent successfully")
                return {"status": "starting", "message": "GPU instance is starting"}

            except Exception as e:
                logger.error(f"Failed to start GPU: {e}", exc_info=True)
                raise

    async def stop_gpu(self) -> Dict[str, Any]:
        """
        Stop the GPU instance.

        Returns:
            Status information
        """
        async with self._stop_lock:
            try:
                logger.info("Stopping GPU instance", extra={"machine_id": settings.VAST_MACHINE_ID})

                await self._make_vast_request(
                    "PUT",
                    f"instances/{settings.VAST_MACHINE_ID}/stop/",
                )

                # Invalidate cache
                self.gpu_status_cache = None
                self.gpu_status_cache_time = None

                logger.info("GPU stop command sent successfully")
                return {"status": "stopped", "message": "GPU instance is stopping"}

            except Exception as e:
                logger.error(f"Failed to stop GPU: {e}", exc_info=True)
                raise

    async def wait_until_ready(self, timeout_seconds: Optional[int] = None) -> bool:
        """
        Wait until GPU is ready to accept requests.

        Args:
            timeout_seconds: Maximum time to wait (uses config default if None)

        Returns:
            True if GPU is ready, False if timeout
        """
        timeout = timeout_seconds or settings.GPU_WARMUP_TIMEOUT_SECONDS
        start_time = time.time()

        logger.info(
            "Waiting for GPU to be ready",
            extra={"timeout_seconds": timeout},
        )

        while time.time() - start_time < timeout:
            try:
                # Check if GPU is running
                if not await self.is_gpu_running(use_cache=False):
                    logger.debug("GPU not yet running, waiting...")
                    await asyncio.sleep(settings.GPU_HEALTH_CHECK_INTERVAL_SECONDS)
                    continue

                # Check GPU worker health endpoint
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{settings.GPU_WORKER_URL}/health")

                    if response.status_code == 200:
                        elapsed = time.time() - start_time
                        logger.info(
                            "GPU is ready",
                            extra={"warmup_time_seconds": round(elapsed, 2)},
                        )
                        return True

            except Exception as e:
                logger.debug(f"GPU not ready yet: {e}")

            await asyncio.sleep(settings.GPU_HEALTH_CHECK_INTERVAL_SECONDS)

        logger.warning("GPU warmup timeout exceeded", extra={"timeout_seconds": timeout})
        return False

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=settings.RETRY_BACKOFF_FACTOR, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def forward_inference(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Forward inference request to GPU worker.

        Args:
            prompt: Text prompt for image generation
            **kwargs: Additional parameters for the inference

        Returns:
            Inference result with image data
        """
        async with self.semaphore:
            self.last_request_time = datetime.now(timezone.utc)

            try:
                logger.info(
                    "Forwarding inference request to GPU",
                    extra={"prompt_length": len(prompt)},
                )

                payload = {"prompt": prompt, **kwargs}

                async with httpx.AsyncClient(
                    timeout=settings.REQUEST_TIMEOUT_SECONDS
                ) as client:
                    response = await client.post(
                        f"{settings.GPU_WORKER_URL}/generate",
                        json=payload,
                    )
                    response.raise_for_status()
                    result = response.json()

                logger.info("Inference completed successfully")
                return result

            except Exception as e:
                logger.error(f"Inference request failed: {e}", exc_info=True)
                raise

    def get_idle_time_seconds(self) -> Optional[float]:
        """
        Get time since last request in seconds.

        Returns:
            Idle time in seconds, or None if no requests yet
        """
        if self.last_request_time is None:
            return None

        return (datetime.now(timezone.utc) - self.last_request_time).total_seconds()

    def should_shutdown(self) -> bool:
        """
        Check if GPU should be shut down due to inactivity.

        Returns:
            True if GPU should be shut down
        """
        idle_time = self.get_idle_time_seconds()

        if idle_time is None:
            return False

        should_stop = idle_time >= settings.IDLE_SHUTDOWN_SECONDS

        if should_stop:
            logger.info(
                "GPU idle timeout reached",
                extra={"idle_seconds": round(idle_time, 2)},
            )

        return should_stop

