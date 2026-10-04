"""Central configuration for AlphaQuant AI backend."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AlphaQuant AI"
    version: str = "1.0.0"
    database_url: str = "sqlite:///./alphaquant.db"
    yfinance_timeout: int = 15
    default_ticker: str = "AAPL"
    cors_origins: list[str] = ["http://localhost:3000", "http://frontend:3000"]
    gbm_mu: float = 0.0008
    gbm_sigma: float = 0.018

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
