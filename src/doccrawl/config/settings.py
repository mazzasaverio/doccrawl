"""Application configuration module."""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseModel):
    """Database connection settings."""
    host: str = Field(..., description="Database host") 
    port: int = Field(5432, description="Database port")
    user: str = Field(..., description="Database user")
    password: str = Field(..., description="Database password")
    database: str = Field(..., description="Database name")
    sslmode: str = Field("prefer", description="SSL mode")

    def get_connection_string(self) -> str:
        """Get database connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

class CrawlerSettings(BaseModel):
    """Crawler specific settings."""
    request_delay: float = Field(1.0, description="Delay between requests in seconds")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_concurrent_pages: int = Field(5, description="Maximum concurrent pages to process")
    batch_size: int = Field(10, description="Batch size for processing URLs")

class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",  
        extra="ignore",
        env_prefix=""
    )

    # Environment
    environment: str = Field("development", description="Application environment")
    debug: bool = Field(False, description="Debug mode")

    # Database
    database: DatabaseSettings = Field(
        default_factory=lambda: DatabaseSettings(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            database=os.getenv("POSTGRES_DATABASE", "doccrawl"),
            sslmode=os.getenv("POSTGRES_SSLMODE", "prefer")
        )
    )

    # Crawler
    crawler: CrawlerSettings = Field(
        default_factory=lambda: CrawlerSettings(
            request_delay=float(os.getenv("REQUEST_DELAY", "1.0")),
            timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
            max_concurrent_pages=int(os.getenv("MAX_CONCURRENT_PAGES", "5")),
            batch_size=int(os.getenv("BATCH_SIZE", "10"))
        )
    )
    
    scrapegraph_api_key: Optional[str] = Field(
        default=os.getenv("SCRAPEGRAPH_API_KEY"),
        description="ScrapegraphAI API key"
    )

    # Logging
    log_level: str = Field(
        default=os.getenv("LOG_LEVEL", "INFO"),
        description="Logging level"
    )
    logfire_enabled: bool = Field(True, description="Enable Logfire logging")

    @classmethod
    def find_config_file(cls) -> Optional[Path]:
        """Find the configuration file in various locations."""
        # Lista dei possibili percorsi per il file di configurazione
        possible_paths = [
            Path("config/crawler_config.yaml"),
            Path("crawler_config.yaml"),
            Path(__file__).parent.parent.parent.parent / "config" / "crawler_config.yaml",
            Path(__file__).parent.parent.parent / "config" / "crawler_config.yaml",
            Path.home() / ".config" / "doccrawl" / "crawler_config.yaml",
        ]

        for path in possible_paths:
            if path.exists():
                return path
        return None

    @classmethod
    def from_yaml(cls, yaml_file: Optional[Path] = None) -> "Settings":
        """Load settings from YAML file or environment variables."""
        config_data = {}
        
        # Se non è stato specificato un file, cerca nei percorsi standard
        if yaml_file is None:
            yaml_file = cls.find_config_file()

        # Se troviamo un file di configurazione, lo carichiamo
        if yaml_file and yaml_file.exists():
            with yaml_file.open() as f:
                config_data = yaml.safe_load(f)

        # Creiamo le impostazioni combinando i dati del file con le variabili d'ambiente
        return cls(**config_data)

def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings.from_yaml()

# Istanza singleton delle impostazioni
settings = get_settings()