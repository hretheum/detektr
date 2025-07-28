"""Configuration management for Frame Buffer v2."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "frame-buffer-v2"
    environment: str = "development"
    debug: bool = True

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_max_connections: int = 50

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

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

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
