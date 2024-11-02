"""Main application module."""
import asyncio
from pathlib import Path
from pprint import pp
import logfire
from typing import List, Dict, Any

from doccrawl.config.settings import settings
from doccrawl.db.connection import DatabaseConnection
from doccrawl.core.crawler import Crawler
from doccrawl.models.frontier_model import FrontierUrl, UrlType, FrontierBatch, UrlStatus
from doccrawl.crud.frontier_crud import FrontierCRUD
from doccrawl.utils.logging import setup_logging
class CrawlerApp:
    """Main application class for document crawler."""
    
    def __init__(self):
        setup_logging()
        self.logger = logfire
        self.config = None
        self.db_connection = None
        self.frontier_crud = None
        self.crawler = None

    async def _init_crawler(self):
        """Initialize crawler with Playwright."""
        self.crawler = Crawler(
            scrapegraph_api_key=settings.scrapegraph_api_key,
            max_concurrent_pages=settings.crawler.max_concurrent_pages,
            batch_size=settings.crawler.batch_size
        )
        await self.crawler.initialize()

    async def load_config(self) -> dict:
        """Load crawler configuration."""
        with logfire.span('load_config'):
            try:
                self.config = {
                    'crawler': {
                        'categories': settings.get_categories(),
                        'default_settings': settings.crawler.model_dump()
                    }
                }
                logfire.info("Configuration loaded successfully")
                return self.config
            except Exception as e:
                logfire.error("Error loading configuration", error=str(e))
                raise

    async def init_database(self):
        """Initialize database connection and tables."""
        with logfire.span('init_database'):
            try:
                self.db_connection = DatabaseConnection()
                self.db_connection.connect()
                self.db_connection.create_tables()
                self.frontier_crud = FrontierCRUD(self.db_connection)
                logfire.info("Database initialized successfully")
            except Exception as e:
                logfire.error("Database initialization failed", error=str(e))
                raise

    async def process_url_at_depth(
        self, 
        frontier_url: FrontierUrl, 
        current_depth: int
    ) -> List[FrontierUrl]:
        """Process a single URL at a specific depth."""
        try:
            logfire.info(
                "Starting URL processing",
                url=str(frontier_url.url),
                depth=current_depth,
                url_type=frontier_url.url_type.value
            )

            if self.crawler is None:
                raise ValueError("Crawler is not initialized")

            # Se l'URL ha un ID, aggiorna il suo stato
            if frontier_url.id is not None:
                await self.frontier_crud.update_url_status(
                    frontier_url.id, 
                    UrlStatus.PROCESSING
                )

            # Processa l'URL e ottieni nuovi URL
            new_urls = await self.crawler.process_single_url(frontier_url)
            
            # Converti None in lista vuota se necessario
            if new_urls is None:
                logfire.warning(
                    "Crawler returned None instead of empty list",
                    url=str(frontier_url.url)
                )
                new_urls = []

            logfire.info(
                "URL processing completed",
                url=str(frontier_url.url),
                new_urls_found=len(new_urls)
            )

            # Storicizza i nuovi URL trovati
            stored_urls = []
            for url in new_urls:
                try:
                    if not await self.frontier_crud.exists_in_frontier(str(url.url)):
                        url_id = await self.frontier_crud.create_url(url)
                        url.id = url_id
                        stored_urls.append(url)
                        logfire.info(
                            "New URL stored",
                            url=str(url.url),
                            id=url_id
                        )
                except Exception as store_error:
                    logfire.error(
                        "Failed to store URL",
                        url=str(url.url),
                        error=str(store_error)
                    )

            # Aggiorna lo stato dell'URL processato se ha un ID
            if frontier_url.id is not None:
                await self.frontier_crud.update_url_status(
                    frontier_url.id, 
                    UrlStatus.PROCESSED
                )

            return stored_urls

        except Exception as e:
            logfire.error(
                "URL processing failed",
                url=str(frontier_url.url),
                depth=current_depth,
                error=str(e)
            )
            if frontier_url.id is not None:
                await self.frontier_crud.update_url_status(
                    frontier_url.id,
                    UrlStatus.FAILED,
                    error_message=str(e)
                )
            return []

    async def process_url_recursively(self, config_url: FrontierUrl):
        """Process a URL recursively up to its maximum depth."""
        try:
            current_depth = 0
            urls_to_process = [config_url]
            
            while current_depth <= config_url.max_depth:
                logfire.info(
                    "Processing depth level",
                    depth=current_depth,
                    max_depth=config_url.max_depth,
                    urls_count=len(urls_to_process)
                )
                
                next_level_urls = []
                for url in urls_to_process:
                    if url.depth == current_depth:
                        new_urls = await self.process_url_at_depth(url, current_depth)
                        next_level_urls.extend(new_urls)
                
                if not next_level_urls:
                    logfire.info(
                        "No more URLs to process at this depth",
                        depth=current_depth
                    )
                    break
                
                urls_to_process = next_level_urls
                current_depth += 1
                
        except Exception as e:
            logfire.error(
                "Recursive processing failed",
                starting_url=str(config_url.url),
                error=str(e)
            )
            raise

    async def run_crawler(self):
        """Run the crawler processing one config URL at a time."""
        with logfire.span('run_crawler'):
            try:
                await self._init_crawler()
                # Initialize crawler
                self.crawler = Crawler(
                    scrapegraph_api_key=settings.scrapegraph_api_key,
                    max_concurrent_pages=settings.crawler.max_concurrent_pages,
                    batch_size=settings.crawler.batch_size
                )

                # Process each category
                for category in self.config['crawler']['categories']:
                    logfire.info(
                        "Starting category processing",
                        category_name=category.name,
                        category_description=category.description
                    )
                    
                    # Process each URL in the category
                    for url_config in category.urls:
                        config_url = FrontierUrl(
                            url=url_config.url,
                            category=category.name,
                            url_type=UrlType(url_config.type),
                            max_depth=url_config.max_depth,
                            target_patterns=url_config.target_patterns,
                            seed_pattern=url_config.seed_pattern
                        )
                        
                        logfire.info(
                            "Starting config URL processing",
                            url=str(config_url.url),
                            type=config_url.url_type.value,
                            max_depth=config_url.max_depth
                        )
                        
                        await self.process_url_recursively(config_url)
                        
                        logfire.info(
                            "Config URL processing completed",
                            url=str(config_url.url)
                        )

                logfire.info("All categories processed successfully")
                
            except Exception as e:
                logfire.error("Crawler execution failed", error=str(e))
                raise

    async def cleanup(self):
        """Cleanup resources."""
        with logfire.span('cleanup'):
            if self.db_connection:
                self.db_connection.close()
                logfire.info("Database connection closed")

    async def run(self):
        """Main application execution flow."""
        with logfire.span('app_run'):
            try:
                await self.load_config()
                await self.init_database()
                await self.run_crawler()
                logfire.info("Application completed successfully")
            except Exception as e:
                logfire.error("Application failed", error=str(e))
                raise
            finally:
                await self.cleanup()