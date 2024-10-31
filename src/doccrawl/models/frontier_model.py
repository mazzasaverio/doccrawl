# src/models/frontier.py
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator
from urllib.parse import urlparse

class UrlStatus(str, Enum):
    """Enumeration of possible URL statuses in the frontier."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    PROCESSED = 'processed'
    FAILED = 'failed'
    SKIPPED = 'skipped'

class UrlType(int, Enum):
    """Enumeration of URL types with their descriptions."""
    DIRECT_TARGET = 0  # Direct links to target documents
    SINGLE_PAGE = 1    # Pages containing target document links
    SEED_TARGET = 2    # Pages with both seed URLs and target documents
    COMPLEX_AI = 3     # Three-level crawling with AI assistance
    FULL_AI = 4        # Multi-level crawling with full AI assistance

class FrontierUrl(BaseModel):
    """Model representing a URL in the frontier."""
    
    # Required fields
    url: HttpUrl
    category: str = Field(..., min_length=1, max_length=255)
    url_type: UrlType
    max_depth: int = Field(..., ge=0)

    # Optional fields
    id: Optional[int] = None
    depth: int = Field(default=0, ge=0)
    main_domain: Optional[str] = None
    target_patterns: Optional[List[str]] = Field(default=None)
    seed_pattern: Optional[str] = None
    is_target: bool = False
    parent_url: Optional[HttpUrl] = None
    status: UrlStatus = UrlStatus.PENDING
    error_message: Optional[str] = None
    insert_date: Optional[datetime] = None
    last_update: Optional[datetime] = None

    @field_validator('main_domain', mode='before', check_fields=True)
    def set_main_domain(cls, v, info):
        """Extract and validate main domain from URL if not provided."""
        if not v and 'url' in info.data:
            return urlparse(str(info.data['url'])).netloc
        return v

    @field_validator('max_depth')
    def validate_max_depth(cls, v, info):
        """Validate max_depth based on URL type."""
        if 'url_type' in info.data:
            url_type = info.data['url_type']
            if url_type == UrlType.DIRECT_TARGET and v != 0:
                raise ValueError("Type 0 (DIRECT_TARGET) must have max_depth = 0")
            elif url_type == UrlType.SINGLE_PAGE and v != 0:
                raise ValueError("Type 1 (SINGLE_PAGE) must have max_depth = 0")
            elif url_type == UrlType.SEED_TARGET and v != 1:
                raise ValueError("Type 2 (SEED_TARGET) must have max_depth = 1")
            elif url_type == UrlType.COMPLEX_AI and v != 2:
                raise ValueError("Type 3 (COMPLEX_AI) must have max_depth = 2")
            elif url_type == UrlType.FULL_AI and v < 2:
                raise ValueError("Type 4 (FULL_AI) must have max_depth >= 2")
        return v

    @field_validator('target_patterns')
    @classmethod
    def validate_target_patterns(cls, v, info):
        """Validate target patterns based on URL type."""
        if 'url_type' in info.data:
            url_type = info.data['url_type']
            if url_type in [UrlType.DIRECT_TARGET] and not v:
                raise ValueError("Type 0 (DIRECT_TARGET) must have target patterns")
        return v

    @field_validator('seed_pattern')
    @classmethod
    def validate_seed_pattern(cls, v, info):
        """Validate seed pattern based on URL type."""
        if 'url_type' in info.data:
            url_type = info.data['url_type']
            if url_type in [UrlType.SEED_TARGET, UrlType.COMPLEX_AI] and not v:
                raise ValueError(f"Type {url_type} must have a seed pattern")
        return v

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "url": "https://example.com/docs/page1",
                "category": "documentation",
                "url_type": 2,
                "max_depth": 1,
                "depth": 0,
                "target_patterns": [".*\\.pdf$"],
                "seed_pattern": "/docs/.*",
                "is_target": False
            }
        }

class FrontierStatistics(BaseModel):
    """Model representing frontier statistics for a category."""
    
    category: str
    total_urls: int
    target_urls: int
    pending_urls: int
    processed_urls: int
    failed_urls: int
    unique_domains: int
    max_reached_depth: int
    success_rate: float = Field(..., ge=0, le=100)
    first_url_date: datetime
    last_update_date: datetime

    @field_validator('success_rate')
    @classmethod
    def calculate_success_rate(cls, v, info):
        """Recalculate success rate if not provided."""
        if v == 0 and 'processed_urls' in info.data and 'failed_urls' in info.data:
            total = info.data['processed_urls'] + info.data['failed_urls']
            if total > 0:
                return (info.data['processed_urls'] / total) * 100
        return v

class FrontierBatch(BaseModel):
    """Model representing a batch of URLs for bulk operations."""
    
    urls: List[FrontierUrl]
    batch_size: Optional[int] = Field(default=100, gt=0)
    
    @field_validator('urls')
    def validate_batch(cls, v):
        """Validate the batch of URLs."""
        if not v:
            raise ValueError("Batch cannot be empty")
        return v

    def chunk_urls(self) -> List[List[FrontierUrl]]:
        """Split URLs into chunks based on batch_size."""
        return [
            self.urls[i:i + self.batch_size] 
            for i in range(0, len(self.urls), self.batch_size)
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "urls": [
                    {
                        "url": "https://example.com/docs/page1",
                        "category": "documentation",
                        "url_type": 2,
                        "max_depth": 1
                    },
                    {
                        "url": "https://example.com/docs/page2",
                        "category": "documentation",
                        "url_type": 2,
                        "max_depth": 1
                    }
                ],
                "batch_size": 100
            }
        }
