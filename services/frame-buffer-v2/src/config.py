"""Configuration management for Frame Buffer v2."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "frame-buffer-v2"
    environment: str = "development"
    debug: bool = True

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 50

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_workers: int = 1

    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60

    class Config:
        """Pydantic config."""

        env_prefix = "FRAME_BUFFER_"
        env_file = ".env"
