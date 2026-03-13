"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "Personal Information Library"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # AI
    openai_api_base: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Crawler
    crawler_max_workers: int = 5
    crawler_request_timeout: int = 30
    crawler_rate_limit: float = 1.0  # seconds between requests
    crawler_max_depth: int = 3

    # Task Queue
    task_queue_size: int = 1000
    task_max_retries: int = 3


settings = Settings()
