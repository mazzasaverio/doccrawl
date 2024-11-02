"""Application configuration module."""
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
import yaml
from pydantic import BaseModel, Field, SecretStr, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

class DatabaseSettings(BaseModel):
    """Database connection settings."""
    host: str = Field(default=os.getenv("POSTGRES_HOST", "localhost"))
    port: int = Field(default=int(os.getenv("POSTGRES_PORT", "5432")))
    user: str = Field(default=os.getenv("POSTGRES_USER", "postgres"))
    password: SecretStr = Field(default=SecretStr(os.getenv("POSTGRES_PASSWORD", "")))
    database: str = Field(default=os.getenv("POSTGRES_DATABASE", "doccrawl"))
    sslmode: str = Field(default=os.getenv("POSTGRES_SSLMODE", "prefer"))

    def get_connection_string(self) -> str:
        """Get database connection string."""
        return (
            f"postgresql://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump to handle SecretStr."""
        d = super().model_dump(*args, **kwargs)
        if 'password' in d:
            d['password'] = self.password.get_secret_value()
        return d

# src/doccrawl/config/settings.py

class CrawlerSettings(BaseModel):
    """Crawler specific settings."""
    request_delay: float = Field(
        default=float(os.getenv("REQUEST_DELAY", "1.0")),
        description="Delay between requests in seconds"
    )
    timeout: int = Field(
        default=int(os.getenv("REQUEST_TIMEOUT", "30")),
        description="Request timeout in seconds"
    )
    max_concurrent_pages: int = Field(
        default=int(os.getenv("MAX_CONCURRENT_PAGES", "5")),
        description="Maximum concurrent pages to process"
    )
    batch_size: int = Field(
        default=int(os.getenv("BATCH_SIZE", "10")),
        description="Batch size for processing URLs"
    )
    headless: bool = Field(
        default=bool(os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"),
        description="Run browser in headless mode"
    )

class UrlConfig(BaseModel):
    """Configuration for a single URL."""
    url: AnyHttpUrl
    type: int = Field(..., ge=0, le=4)
    target_patterns: Optional[List[str]] = None
    seed_pattern: Optional[str] = None
    max_depth: int = Field(..., ge=0)

class CategoryConfig(BaseModel):
    """Configuration for a category of URLs."""
    name: str
    description: Optional[str] = None
    urls: List[UrlConfig]

class CrawlerYamlConfig(BaseModel):
    """Structure for the YAML configuration file."""
    default_settings: Optional[Dict[str, Any]] = None
    categories: List[CategoryConfig] = Field(default_factory=list)

class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix=""
    )

    # Environment
    environment: str = Field(
        default=os.getenv("ENVIRONMENT", "development"),
        description="Application environment"
    )
    debug: bool = Field(
        default=os.getenv("DEBUG", "false").lower() == "true",
        description="Debug mode"
    )

    # Database
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    # Crawler
    crawler: CrawlerSettings = Field(default_factory=CrawlerSettings)
    
    # Crawler configuration from YAML
    crawler_config: CrawlerYamlConfig = Field(default_factory=CrawlerYamlConfig)
    
    # API Keys
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
            try:
                with yaml_file.open() as f:
                    yaml_config = yaml.safe_load(f)
                    if yaml_config and isinstance(yaml_config, dict):
                        # Validiamo la configurazione YAML usando il modello
                        crawler_config = CrawlerYamlConfig(**yaml_config.get('crawler', {}))
                        config_data['crawler_config'] = crawler_config
            except Exception as e:
                raise ValueError(f"Error loading YAML configuration: {str(e)}")

        # Creiamo le impostazioni combinando i dati del file con le variabili d'ambiente
        instance = cls(**config_data)
        
        # Aggiorna le impostazioni del crawler con quelle dal YAML se presenti
        if instance.crawler_config.default_settings:
            # Aggiorna solo i valori che sono effettivamente presenti nel YAML
            crawler_dict = instance.crawler.model_dump()
            crawler_dict.update(instance.crawler_config.default_settings)
            instance.crawler = CrawlerSettings(**crawler_dict)
        
        return instance

    def get_categories(self) -> List[CategoryConfig]:
        """Get list of configured categories."""
        return self.crawler_config.categories

    def get_database_url(self) -> str:
        """Get database URL string."""
        return self.database.get_connection_string()

def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings.from_yaml()

# Istanza singleton delle impostazioni
settings = get_settings()