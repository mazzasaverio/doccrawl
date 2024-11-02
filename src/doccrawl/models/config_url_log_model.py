# src/doccrawl/models/config_url_log_model.py
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl
from urllib.parse import urlparse

class ConfigUrlStatus(str, Enum):
    """Enumeration of possible config URL processing statuses."""
    PENDING = 'pending'           
    RUNNING = 'running'           
    COMPLETED = 'completed'       
    FAILED = 'failed'            
    PARTIALLY_COMPLETED = 'partially_completed'  

class ConfigUrlLog(BaseModel):
    """Model representing a log entry for a configuration URL."""
    
    id: Optional[int] = None
    # Cambiato il tipo da HttpUrl a str
    url: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1, max_length=255)
    status: ConfigUrlStatus = ConfigUrlStatus.PENDING
    
    # Metriche di elaborazione
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_duration: Optional[float] = None  # in secondi
    
    # Contatori
    total_urls_found: int = Field(default=0, ge=0)
    target_urls_found: int = Field(default=0, ge=0)
    seed_urls_found: int = Field(default=0, ge=0)
    failed_urls: int = Field(default=0, ge=0)
    
    # Dettagli errori e warnings
    error_message: Optional[str] = None
    warning_messages: Optional[list[str]] = Field(default_factory=list)
    
    # Informazioni di configurazione
    url_type: int = Field(..., ge=0, le=4)
    max_depth: int = Field(..., ge=0)
    reached_depth: int = Field(default=0, ge=0)
    target_patterns: Optional[list[str]] = None
    seed_pattern: Optional[str] = None
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True