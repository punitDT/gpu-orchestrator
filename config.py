"""
Configuration management using Pydantic BaseSettings.
All environment variables are typed and validated.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Vast.ai Configuration
    VAST_API_KEY: str
    VAST_MACHINE_ID: str
    GPU_WORKER_URL: str
    
    # Timing Configuration
    IDLE_SHUTDOWN_SECONDS: int = 120
    GPU_WARMUP_TIMEOUT_SECONDS: int = 300
    GPU_HEALTH_CHECK_INTERVAL_SECONDS: int = 5
    
    # Rate Limiting
    MAX_CONCURRENT_GPU_REQUESTS: int = 3
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    # Request Configuration
    REQUEST_TIMEOUT_SECONDS: int = 60
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0
    
    # Cache Configuration
    GPU_STATUS_CACHE_SECONDS: int = 10
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    LOG_LEVEL: str = "INFO"
    
    # CORS Configuration
    CORS_ORIGINS: str = "*"  # Comma-separated list or "*"
    
    # Application Metadata
    APP_NAME: str = "GPU Orchestrator"
    APP_VERSION: str = "1.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

