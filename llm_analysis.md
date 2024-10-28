# Doccrawl - Project Analysis Request

Generated on: 2024-10-28 10:29:44

## Analysis Objectives

Please analyze this codebase focusing on:

1. Code architecture and organization

2. Dependency management and requirements

3. Implementation of Python best practices

4. Potential improvements and optimizations

5. Security considerations

6. Scalability aspects


# Project Structure

├── LICENSE
├── README.md
├── config
│   └── crawler_config.yaml
├── docker
│   ├── Dockerfile
│   └── docker-compose.yml
├── env.example
├── hello_world.py
├── pyproject.toml
├── src
│   ├── core
│   │   ├── crawler.py
│   │   └── strategies
│   │       ├── type_0.py
│   │       ├── type_1.py
│   │       ├── type_2.py
│   │       ├── type_3.py
│   │       └── type_4.py
│   ├── crud
│   │   ├── base_crud.py
│   │   └── frontier_crud.py
│   ├── db
│   │   └── connection.py
│   ├── models
│   │   └── frontier_model.py
│   └── utils
│       └── logging.py
├── tests
└── uv.lock
# Code Contents


# hello_world.py
```py
import logfire

logfire.configure()  
logfire.info('Hello, {name}!', name='world')
```


# pyproject.toml
```toml
[project]
name = "doccrawl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "logfire>=1.3.0",
    "pandas>=2.2.3",
    "playwright>=1.48.0",
    "psycopg2-binary>=2.9.10",
    "scrapegraphai>=1.27.0",
]

```


# config/crawler_config.yaml
```yaml
# config/crawler_config.yaml
# Document Crawler Configuration Guide
# 
# This configuration file defines the crawling strategy for different types of document sources.
# Each URL is classified into one of five types (0-4), each with specific behaviors:
#
# Type 0 - Direct Target URLs:
#   - Direct links to target documents (e.g., direct PDF links)
#   - No crawling depth (max_depth must be 0)
#   - No seed_pattern needed
#   - Example use: Known document URLs that don't require crawling
#
# Type 1 - Single Page with Targets:
#   - Pages containing target document links
#   - No crawling depth (max_depth must be 0)
#   - No seed_pattern needed
#   - Uses target_patterns to identify document links
#   - Example use: Archive pages with document listings
#
# Type 2 - Seed and Target Pages:
#   - Pages containing both seed URLs and target documents
#   - Crawls one level deep (max_depth must be 1)
#   - Requires seed_pattern to identify next-level pages
#   - Uses target_patterns to identify documents
#   - Example use: Index pages with links to archive sections
#   - Skip seeds already present in frontier table
#
# Type 3 - Complex AI-Assisted:
#   - Three-level crawling strategy:
#     * Depth 0: Uses seed_pattern and target_patterns
#     * Depth 1: Uses ScrapegraphAI to identify both seeds and targets
#     * Depth 2: Only collects targets matching target_patterns
#   - Requires max_depth = 2
#   - Requires seed_pattern for initial crawling
#   - Skip seeds already present in frontier table
#
# Type 4 - Full AI-Assisted:
#   - Multi-level crawling with AI assistance:
#     * Depth 0-1: Uses ScrapegraphAI to identify both seeds and targets
#     * Final depth: Only collects targets matching target_patterns
#   - Configurable max_depth (must be ≥ 2)
#   - No initial seed_pattern required (fully AI-driven)
#   - Skip seeds already present in frontier table
#
# Common Configuration Elements:
# - target_patterns: List of regex patterns identifying target documents
#   Examples:
#   - ".*\.pdf$" : Matches URLs ending in .pdf
#   - ".*/doc/\d+$" : Matches URLs like "/doc/123"
#   - ".*/document/[a-zA-Z0-9-]+$" : Matches document URLs with alphanumeric IDs
#
# - seed_pattern: Regex pattern identifying URLs to crawl next
#   Examples:
#   - "/archive/\d{4}/$" : Matches year-based archive sections
#   - "/section/[a-zA-Z0-9-]+/$" : Matches section URLs

crawler:
  default_settings:
    request_delay: 1.0  # Delay between requests in seconds
    timeout: 30  # Request timeout in seconds

  categories:
    - name: "documenti_ministeriali"
      description: "Documenti e circolari ministeriali"
      urls:
        # Type 0: Direct target URL example
        - url: "https://example.com/docs/circolare123.pdf"
          type: 0
          target_patterns:
            - ".*\.pdf$"
          max_depth: 0
          
        # Type 1: Single page with target URLs
        - url: "https://example.com/documenti-2024"
          type: 1
          target_patterns:
            - ".*\.pdf$"
            - ".*/doc/circolare-\d+$"
          max_depth: 0
          
        # Type 2: Page with both target and seed URLs
        - url: "https://example.com/archivio-circolari"
          type: 2
          target_patterns:
            - ".*\.pdf$"
            - ".*/circolari/\d{4}/\d+$"
          seed_pattern: "/archivio-circolari/\d{4}/$"
          max_depth: 1
          
        # Type 3: Complex crawling with AI assistance at depth 1
        - url: "https://example.com/amministrazione"
          type: 3
          target_patterns:
            - ".*\.pdf$"
            - ".*/documento/[a-zA-Z0-9-]+$"
          seed_pattern: "/amministrazione/[a-zA-Z0-9-]+/$"
          max_depth: 2
          
        # Type 4: Full AI-assisted crawling
        - url: "https://example.com/portale"
          type: 4
          target_patterns:
            - ".*\.pdf$"
            - ".*/files/.*documento.*"
          max_depth: 3

    - name: "documenti_tecnici"
      description: "Documentazione tecnica e specifiche"
      urls:
        - url: "https://example.com/specs/technical_doc_v1.pdf"
          type: 0
          target_patterns:
            - ".*\.pdf$"
          max_depth: 0
          
        - url: "https://example.com/technical-library"
          type: 1
          target_patterns:
            - ".*\.pdf$"
            - ".*/technical-specs/.*"
          max_depth: 0
          
        - url: "https://example.com/documentation"
          type: 2
          target_patterns:
            - ".*\.pdf$"
            - ".*/docs/v\d+/.*"
          seed_pattern: "/documentation/section-.*/$"
          max_depth: 1

database:
  frontier_table: "url_frontier"

```


# docker/docker-compose.yml
```yml

```


# src/utils/logging.py
```py

```


# src/db/connection.py
```py
# src/db/connection.py
import os

import psycopg2
from psycopg2.extras import DictCursor
import logfire

class DatabaseConnection:
    def __init__(self):
        self.conn = None
        self.logger = logfire

    def connect(self):
        """Establish database connection using environment variables."""
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DATABASE"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT"),
                sslmode=os.getenv("POSTGRES_SSLMODE")
            )
            self.logger.info("Successfully connected to the database")
            return self.conn
        except Exception as e:
            self.logger.error(f"Error connecting to database: {str(e)}")
            raise

    def create_tables(self):
        """Create the frontier table if it doesn't exist."""
        with self.conn.cursor() as cur:
            try:
                # Create frontier table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS url_frontier (
                        id SERIAL PRIMARY KEY,
                        category VARCHAR(255) NOT NULL,
                        url TEXT NOT NULL,
                        url_type INTEGER NOT NULL,
                        depth INTEGER NOT NULL DEFAULT 0,
                        main_domain TEXT NOT NULL,
                        target_patterns TEXT[],
                        seed_pattern TEXT,
                        max_depth INTEGER NOT NULL,
                        is_target BOOLEAN NOT NULL DEFAULT FALSE,
                        parent_url TEXT,
                        insert_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'pending'
                    );
                    
                    -- Create indexes for better performance
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_url ON url_frontier(url);
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_status ON url_frontier(status);
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_category ON url_frontier(category);
                """)
                self.conn.commit()
                self.logger.info("Successfully created url_frontier table")
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"Error creating tables: {str(e)}")
                raise

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
```


# src/core/crawler.py
```py

```


# src/core/strategies/type_0.py
```py

```


# src/core/strategies/type_1.py
```py

```


# src/core/strategies/type_2.py
```py

```


# src/core/strategies/type_3.py
```py

```


# src/core/strategies/type_4.py
```py

```


# src/crud/base_crud.py
```py
# src/crud/base_crud.py
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logfire
from psycopg2.extras import execute_values, DictCursor

class BaseCRUD:
    """
    Base CRUD operations for database interactions.
    Provides generic database operations that can be used across different tables.
    """
    
    def __init__(self, conn):
        """
        Initialize BaseCRUD with a database connection.
        
        Args:
            conn: psycopg2 connection object
        """
        self.conn = conn
        self.logger = logfire

    def insert_one(
        self, 
        table: str, 
        data: Dict[str, Any], 
        return_id: bool = True
    ) -> Optional[int]:
        """
        Insert a single record into specified table.
        
        Args:
            table: Table name
            data: Dictionary of column names and values
            return_id: Whether to return the ID of the inserted record
        
        Returns:
            The ID of the inserted record if return_id is True
        """
        with self.conn.cursor() as cur:
            try:
                # Filter out None values unless explicitly needed
                filtered_data = {k: v for k, v in data.items() if v is not None}
                
                columns = list(filtered_data.keys())
                values = list(filtered_data.values())
                placeholders = ', '.join(['%s'] * len(columns))
                
                query = f"""
                INSERT INTO {table} 
                ({', '.join(columns)}) 
                VALUES ({placeholders})
                """
                
                if return_id:
                    query += " RETURNING id"
                
                cur.execute(query, values)
                record_id = cur.fetchone()[0] if return_id else None
                self.conn.commit()
                
                self.logger.info(
                    'Record inserted successfully',
                    table=table,
                    record_id=record_id if return_id else None
                )
                
                return record_id
                
            except Exception as e:
                self.conn.rollback()
                self.logger.error(
                    'Error inserting record',
                    table=table,
                    error=str(e),
                    data=str(data)
                )
                raise

    def insert_many(
        self, 
        table: str, 
        columns: List[str], 
        values: List[Tuple],
        page_size: int = 1000
    ) -> None:
        """
        Insert multiple records into specified table with pagination.
        
        Args:
            table: Table name
            columns: List of column names
            values: List of tuples containing values
            page_size: Number of records to insert at once
        """
        with self.conn.cursor() as cur:
            try:
                # Insert in batches to handle large datasets
                for i in range(0, len(values), page_size):
                    batch = values[i:i + page_size]
                    query = f"""
                    INSERT INTO {table} 
                    ({', '.join(columns)}) 
                    VALUES %s
                    """
                    
                    execute_values(cur, query, batch)
                    self.conn.commit()
                
                self.logger.info(
                    'Bulk insert completed successfully',
                    table=table,
                    total_records=len(values)
                )
                
            except Exception as e:
                self.conn.rollback()
                self.logger.error(
                    'Error in bulk insert',
                    table=table,
                    error=str(e),
                    batch_size=page_size
                )
                raise

    def update(
        self, 
        table: str, 
        conditions: Dict[str, Any], 
        data: Dict[str, Any],
        return_updated: bool = False
    ) -> Optional[List[Dict]]:
        """
        Update records that match the conditions.
        
        Args:
            table: Table name
            conditions: Dictionary of column names and values for WHERE clause
            data: Dictionary of columns to update with new values
            return_updated: Whether to return the updated records
            
        Returns:
            List of updated records if return_updated is True
        """
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            try:
                # Prepare SET clause
                set_items = [f"{k} = %s" for k in data.keys()]
                set_values = list(data.values())
                
                # Prepare WHERE clause
                where_items = [f"{k} = %s" for k in conditions.keys()]
                where_values = list(conditions.values())
                
                query = f"""
                UPDATE {table} 
                SET {', '.join(set_items)}
                WHERE {' AND '.join(where_items)}
                """
                
                if return_updated:
                    query += " RETURNING *"
                
                cur.execute(query, set_values + where_values)
                updated_records = [dict(row) for row in cur.fetchall()] if return_updated else None
                self.conn.commit()
                
                self.logger.info(
                    'Update completed successfully',
                    table=table,
                    conditions=str(conditions),
                    records_updated=len(updated_records) if return_updated else 'Unknown'
                )
                
                return updated_records
                
            except Exception as e:
                self.conn.rollback()
                self.logger.error(
                    'Error updating records',
                    table=table,
                    error=str(e),
                    conditions=str(conditions)
                )
                raise

    def select(
        self,
        table: str,
        conditions: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        Select records based on conditions with pagination support.
        
        Args:
            table: Table name
            conditions: Optional dictionary of column names and values for WHERE clause
            columns: Optional list of columns to select
            order_by: Optional string for ORDER BY clause
            limit: Optional integer for LIMIT clause
            offset: Optional integer for OFFSET clause
        
        Returns:
            List of dictionaries representing the selected records
        """
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            try:
                # Build SELECT clause
                select_clause = '*' if not columns else ', '.join(columns)
                query_parts = [f"SELECT {select_clause} FROM {table}"]
                values = []
                
                # Build WHERE clause if conditions provided
                if conditions:
                    where_conditions = []
                    for k, v in conditions.items():
                        if isinstance(v, (list, tuple)):
                            where_conditions.append(f"{k} = ANY(%s)")
                            values.append(list(v))
                        elif v is None:
                            where_conditions.append(f"{k} IS NULL")
                        else:
                            where_conditions.append(f"{k} = %s")
                            values.append(v)
                    
                    if where_conditions:
                        query_parts.append("WHERE " + " AND ".join(where_conditions))
                
                # Add optional clauses
                if order_by:
                    query_parts.append(f"ORDER BY {order_by}")
                if limit is not None:
                    query_parts.append(f"LIMIT {limit}")
                if offset is not None:
                    query_parts.append(f"OFFSET {offset}")
                
                query = " ".join(query_parts)
                cur.execute(query, values)
                
                results = [dict(row) for row in cur.fetchall()]
                
                self.logger.info(
                    'Select query executed successfully',
                    table=table,
                    records_found=len(results)
                )
                
                return results
                
            except Exception as e:
                self.logger.error(
                    'Error selecting records',
                    table=table,
                    error=str(e),
                    conditions=str(conditions)
                )
                raise

    def delete(self, table: str, conditions: Dict[str, Any]) -> int:
        """
        Delete records based on conditions.
        
        Args:
            table: Table name
            conditions: Dictionary of column names and values for WHERE clause
        
        Returns:
            Number of records deleted
        """
        with self.conn.cursor() as cur:
            try:
                where_items = [f"{k} = %s" for k in conditions.keys()]
                values = list(conditions.values())
                
                query = f"""
                DELETE FROM {table} 
                WHERE {' AND '.join(where_items)}
                RETURNING id
                """
                
                cur.execute(query, values)
                deleted_count = len(cur.fetchall())
                self.conn.commit()
                
                self.logger.info(
                    'Delete operation completed successfully',
                    table=table,
                    records_deleted=deleted_count
                )
                
                return deleted_count
                
            except Exception as e:
                self.conn.rollback()
                self.logger.error(
                    'Error deleting records',
                    table=table,
                    error=str(e),
                    conditions=str(conditions)
                )
                raise

    def exists(self, table: str, conditions: Dict[str, Any]) -> bool:
        """
        Check if records exist based on conditions.
        
        Args:
            table: Table name
            conditions: Dictionary of column names and values to check
        
        Returns:
            Boolean indicating if matching record exists
        """
        with self.conn.cursor() as cur:
            try:
                where_items = [f"{k} = %s" for k in conditions.keys()]
                values = list(conditions.values())
                
                query = f"""
                SELECT EXISTS(
                    SELECT 1 FROM {table} 
                    WHERE {' AND '.join(where_items)}
                )
                """
                
                cur.execute(query, values)
                return cur.fetchone()[0]
                
            except Exception as e:
                self.logger.error(
                    'Error checking existence',
                    table=table,
                    error=str(e),
                    conditions=str(conditions)
                )
                raise
```


# src/crud/frontier_crud.py
```py

```


# src/models/frontier_model.py
```py
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

```
