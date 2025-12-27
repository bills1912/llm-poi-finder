"""
Configuration management for the Maps LLM application.
Handles environment variables, API keys, and application settings.
"""

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with validation and defaults."""
    
    # Application Settings
    app_name: str = "HeyPico Maps LLM"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment name")
    
    # Server Settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Google Maps API Settings
    google_maps_api_key: str = Field(
        default="",
        description="Google Maps API key for backend services"
    )
    google_maps_frontend_key: str = Field(
        default="",
        description="Google Maps API key for frontend (restricted)"
    )
    
    # Rate Limiting Settings
    rate_limit_requests: int = Field(
        default=100,
        description="Maximum requests per time window"
    )
    rate_limit_window: int = Field(
        default=3600,
        description="Rate limit time window in seconds"
    )
    daily_quota_limit: int = Field(
        default=1000,
        description="Daily API quota limit per user"
    )
    
    # LLM Settings (Ollama)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    llm_model: str = Field(
        default="llama3.2",
        description="LLM model to use (llama3.2, mistral, phi3)"
    )
    llm_temperature: float = Field(
        default=0.7,
        description="LLM temperature for response generation"
    )
    llm_max_tokens: int = Field(
        default=1024,
        description="Maximum tokens in LLM response"
    )
    
    # Search Settings
    default_search_radius: int = Field(
        default=5000,
        description="Default search radius in meters"
    )
    max_search_results: int = Field(
        default=10,
        description="Maximum number of search results to return"
    )
    default_location: str = Field(
        default="-7.7713,110.3774",  # Yogyakarta, Indonesia as default
        description="Default location (lat,lng) for searches"
    )
    
    # Cache Settings
    cache_ttl: int = Field(
        default=3600,
        description="Cache time-to-live in seconds"
    )
    enable_cache: bool = Field(
        default=True,
        description="Enable response caching"
    )
    
    @field_validator('google_maps_api_key', 'google_maps_frontend_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format (basic check)."""
        if v and len(v) < 20:
            raise ValueError("API key appears to be invalid (too short)")
        return v
    
    @field_validator('allowed_origins')
    @classmethod
    def parse_origins(cls, v: str) -> str:
        """Ensure origins string is properly formatted."""
        return v.strip()
    
    @property
    def cors_origins(self) -> list[str]:
        """Get list of CORS origins."""
        return [origin.strip() for origin in self.allowed_origins.split(',')]
    
    @property
    def default_coords(self) -> tuple[float, float]:
        """Get default coordinates as tuple."""
        lat, lng = self.default_location.split(',')
        return (float(lat), float(lng))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class APIKeyManager:
    """
    Manages API key security and validation.
    Implements best practices for API key handling.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._validate_keys()
    
    def _validate_keys(self) -> None:
        """Validate that required API keys are present."""
        if not self.settings.google_maps_api_key:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY is required. "
                "Please set it in your .env file or environment variables."
            )
    
    def get_backend_key(self) -> str:
        """Get the backend API key (for server-side requests)."""
        return self.settings.google_maps_api_key
    
    def get_frontend_key(self) -> Optional[str]:
        """
        Get the frontend API key (restricted key for client-side).
        Returns None if not configured (uses backend key with caution).
        """
        return self.settings.google_maps_frontend_key or None
    
    def mask_key(self, key: str) -> str:
        """Mask API key for logging (show only first/last 4 chars)."""
        if len(key) <= 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"


class QuotaTracker:
    """
    Tracks API usage to prevent exceeding quotas.
    In production, this should use Redis or a database.
    """
    
    def __init__(self, daily_limit: int):
        self.daily_limit = daily_limit
        self._usage: dict[str, int] = {}  # Simple in-memory tracking
    
    def check_quota(self, user_id: str) -> bool:
        """Check if user has remaining quota."""
        current = self._usage.get(user_id, 0)
        return current < self.daily_limit
    
    def increment_usage(self, user_id: str, amount: int = 1) -> int:
        """Increment usage counter and return new total."""
        current = self._usage.get(user_id, 0)
        new_total = current + amount
        self._usage[user_id] = new_total
        return new_total
    
    def get_remaining(self, user_id: str) -> int:
        """Get remaining quota for user."""
        current = self._usage.get(user_id, 0)
        return max(0, self.daily_limit - current)
    
    def reset_user(self, user_id: str) -> None:
        """Reset quota for a specific user."""
        self._usage[user_id] = 0
    
    def reset_all(self) -> None:
        """Reset all quotas (call daily via cron/scheduler)."""
        self._usage.clear()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Initialize global instances
settings = get_settings()
