"""
Centralized Configuration Management
=====================================
Manages all application configuration using Pydantic BaseSettings.
Consolidates environment variables, provides validation, and ensures type safety.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
from pathlib import Path
import os


class DatabaseSettings(BaseSettings):
    """Database connection configuration"""
    
    # Simulation database
    simulation_host: str = Field(default="localhost", description="Simulation database host")
    simulation_port: int = Field(default=5432, description="Simulation database port")
    simulation_user: str = Field(default="optiflow", description="Simulation database user")
    simulation_password: str = Field(default="", description="Simulation database password")
    simulation_db: str = Field(default="optiflow_simulation", description="Simulation database name")
    
    # Real database
    real_host: str = Field(default="localhost", description="Real database host")
    real_port: int = Field(default=5433, description="Real database port")
    real_user: str = Field(default="optiflow", description="Real database user")
    real_password: str = Field(default="", description="Real database password")
    real_db: str = Field(default="optiflow_real", description="Real database name")
    
    # Connection pooling
    pool_size: int = Field(default=5, ge=1, le=50, description="Database connection pool size")
    max_overflow: int = Field(default=10, ge=0, le=100, description="Max overflow connections")
    pool_recycle: int = Field(default=3600, ge=300, description="Connection recycle time (seconds)")
    
    @property
    def simulation_url(self) -> str:
        """Generate simulation database URL"""
        return f"postgresql://{self.simulation_user}:{self.simulation_password}@{self.simulation_host}:{self.simulation_port}/{self.simulation_db}"
    
    @property
    def real_url(self) -> str:
        """Generate real database URL"""
        return f"postgresql://{self.real_user}:{self.real_password}@{self.real_host}:{self.real_port}/{self.real_db}"
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False


class MQTTSettings(BaseSettings):
    """MQTT broker configuration"""
    
    broker: str = Field(default="172.20.10.3", description="MQTT broker address")
    port: int = Field(default=1883, ge=1, le=65535, description="MQTT broker port")
    topic_data: str = Field(default="store/aisle1", description="Data topic")
    topic_status: str = Field(default="store/status", description="Status topic")
    topic_control: str = Field(default="store/control", description="Control topic")
    topic_restock: str = Field(default="store/restock", description="Restock topic")
    keepalive: int = Field(default=60, ge=10, le=300, description="MQTT keepalive (seconds)")
    qos: int = Field(default=1, ge=0, le=2, description="MQTT QoS level")
    
    class Config:
        env_prefix = "MQTT_"
        case_sensitive = False


class SecuritySettings(BaseSettings):
    """Security and authentication configuration"""
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")
    
    # API Keys (for future implementation)
    api_key_enabled: bool = Field(default=False, description="Enable API key authentication")
    api_keys: List[str] = Field(default=[], description="Valid API keys")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=False, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=60, ge=1, description="Requests per minute")
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = False


class SimulationSettings(BaseSettings):
    """Simulation configuration"""
    
    # Store dimensions
    store_width: int = Field(default=1000, ge=100, description="Store width (cm)")
    store_height: int = Field(default=800, ge=100, description="Store height (cm)")
    
    # RFID/UWB parameters
    rfid_detection_range: float = Field(default=150.0, ge=50.0, le=500.0, description="RFID detection range (cm)")
    uwb_noise_std: float = Field(default=5.0, ge=0.0, le=20.0, description="UWB measurement noise std dev (cm)")
    
    # Simulation defaults
    default_speed_multiplier: float = Field(default=1.0, ge=0.5, le=5.0, description="Default speed multiplier")
    default_mode: str = Field(default="REALISTIC", description="Default simulation mode")
    default_disappearance_rate: float = Field(default=0.015, ge=0.0, le=0.1, description="Default item disappearance rate")
    
    # Process management
    output_file: str = Field(default="sim_output.txt", description="Simulation output file")
    
    class Config:
        env_prefix = "SIM_"
        case_sensitive = False


class ApplicationSettings(BaseSettings):
    """Main application configuration"""
    
    # Application
    app_name: str = Field(default="OptiFlow API", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    
    # API
    api_prefix: str = Field(default="/api/v1", description="API route prefix")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json/text)")
    
    # State management
    state_file_path: str = Field(default="/tmp/optiflow_state.json", description="State file path")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment"""
        valid_envs = ['development', 'staging', 'production']
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment. Must be one of: {valid_envs}")
        return v.lower()
    
    class Config:
        env_prefix = "APP_"
        case_sensitive = False


class Settings(BaseSettings):
    """
    Unified settings container.
    
    Usage:
        from app.settings import settings
        
        # Access database config
        db_url = settings.database.simulation_url
        
        # Access MQTT config
        broker = settings.mqtt.broker
    """
    
    app: ApplicationSettings = Field(default_factory=ApplicationSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    mqtt: MQTTSettings = Field(default_factory=MQTTSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    simulation: SimulationSettings = Field(default_factory=SimulationSettings)
    
    class Config:
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        """Initialize settings and validate configuration"""
        super().__init__(**kwargs)
        if self.app.environment == 'production':
            self._validate_production_config()
    
    def _validate_production_config(self):
        """Validate production-specific requirements"""
        # Ensure debug is off
        if self.app.debug:
            raise ValueError("Debug mode must be disabled in production")
        
        # Ensure CORS is not wide open
        if '*' in self.security.cors_origins:
            raise ValueError("CORS origins must not include '*' in production")
        
        # Ensure database passwords are set
        if not self.database.simulation_password or not self.database.real_password:
            raise ValueError("Database passwords must be set in production")
    
    def get_database_url(self, mode: str = "simulation") -> str:
        """
        Get database URL for specified mode.
        
        Args:
            mode: 'simulation' or 'real'
            
        Returns:
            Database connection URL
        """
        if mode.lower() == "simulation":
            return self.database.simulation_url
        elif mode.lower() == "real":
            return self.database.real_url
        else:
            raise ValueError(f"Invalid database mode: {mode}")


# Global settings instance
settings = Settings()


# Constants (extracted from hardcoded values)
class Constants:
    """Application constants"""
    
    # Zone types
    ZONE_TYPE_AISLE = "aisle"
    ZONE_TYPE_CHECKOUT = "checkout"
    ZONE_TYPE_ENTRANCE = "entrance"
    ZONE_TYPE_STORAGE = "storage"
    
    # Item statuses
    STATUS_PRESENT = "present"
    STATUS_SOLD = "sold"
    STATUS_MISSING = "missing"
    STATUS_RESTOCKING = "restocking"
    
    # Simulation modes
    MODE_DEMO = "DEMO"
    MODE_REALISTIC = "REALISTIC"
    MODE_STRESS = "STRESS"
    
    # System modes
    SYSTEM_MODE_SIMULATION = "SIMULATION"
    SYSTEM_MODE_REAL = "REAL"
    
    # API limits
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 1000
    
    # Timeouts
    HTTP_TIMEOUT_SECONDS = 30
    MQTT_CONNECTION_TIMEOUT = 5
    DATABASE_QUERY_TIMEOUT = 30


constants = Constants()
