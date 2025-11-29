"""Centralized settings configuration for OptiFlow backend"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application settings
    app_name: str = "OptiFlow API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database settings
    database_url_simulation: str = "postgresql://optiflow:optiflow_dev@localhost:5432/optiflow_simulation"
    database_url_real: str = "postgresql://optiflow:optiflow_dev@localhost:5433/optiflow_real"
    
    # MQTT settings
    mqtt_broker: str = "172.20.10.3"
    mqtt_port: int = 1883
    mqtt_timeout: int = 3
    
    # Store settings
    default_store_width: int = 1000
    default_store_height: int = 800
    
    # Simulation settings
    default_simulation_speed: float = 1.0
    default_disappearance_rate: float = 0.015
    
    # Position calculation settings
    position_measurement_timeout_seconds: int = 5
    min_anchors_for_position: int = 2
    
    # CORS settings
    cors_origins: list = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Map environment variable names to field names
        env_prefix = ""


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance for convenience
settings = get_settings()
