import asyncio
from datetime import datetime
from pathlib import Path
import logfire
from typing import List, Dict, Any, Optional

from doccrawl.config.settings import settings
from doccrawl.db.connection import DatabaseConnection
from doccrawl.core.crawler import Crawler
from doccrawl.models.frontier_model import FrontierUrl, UrlType, FrontierBatch, UrlStatus
from doccrawl.models.config_url_log_model import ConfigUrlLog, ConfigUrlStatus
from doccrawl.crud.frontier_crud import FrontierCRUD
from doccrawl.crud.config_url_log_crud import ConfigUrlLogCRUD
from doccrawl.utils.logging import setup_logging

class CrawlerApp:
    """Main application class for document crawler."""
    
    def __init__(self):
        setup_logging()
        self.logger = logfire
        self.config = None
        self.db_connection = None
        self.frontier_crud = None
        self.config_log_crud = None
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
                self.config_log_crud = ConfigUrlLogCRUD(self.db_connection)
                logfire.info("Database initialized successfully")
            except Exception as e:
                logfire.error("Database initialization failed", error=str(e))
                raise

    async def process_config_url(self, config_url: FrontierUrl) -> None:
        """Process a single config URL (root URL) and all its descendants."""
        try:
            # Create log entry for config URL
            config_log = ConfigUrlLog(
                url=str(config_url.url),
                category=config_url.category,
                url_type=config_url.url_type.value,
                max_depth=config_url.max_depth,
                target_patterns=config_url.target_patterns,
                seed_pattern=config_url.seed_pattern,
                status=ConfigUrlStatus.PENDING
            )
            
            log_id = await self.config_log_crud.create_log(config_log)
            await self.config_log_crud.start_processing(log_id)
            
            # Process URL tree
            await self.process_seed_recursively(
                config_url,
                log_id,
                is_root_url=True
            )

            # Update log status
            await self.config_log_crud.update_status(
                log_id,
                ConfigUrlStatus.COMPLETED
            )
            
            self.logger.info(
                "Config URL processing completed",
                url=str(config_url.url)
            )
            
        except Exception as e:
            self.logger.error(
                "Error processing config URL",
                url=str(config_url.url),
                error=str(e)
            )
            try:
                await self.config_log_crud.update_status(
                    log_id,
                    ConfigUrlStatus.FAILED,
                    error_message=str(e)
                )
            except NameError:
                self.logger.error("log_id not available, unable to update log status")

    async def process_seed_recursively(
        self, 
        frontier_url: FrontierUrl, 
        config_log_id: int,
        is_root_url: bool = False
    ):
        """
        Process a seed URL and all its child seeds recursively.
        
        Args:
            frontier_url: The URL to process
            config_log_id: ID of the config log entry
            is_root_url: Whether this is a root URL from config file
        """
        try:
            # Process current URL
            new_urls = await self.process_url_sequentially(
                frontier_url, 
                config_log_id,
                is_root_url
            )
            
            self.logger.info(
                "URL processed successfully",
                url=str(frontier_url.url),
                new_urls=len(new_urls)
            )
            
            # Process discovered seed URLs recursively
            for url in new_urls:
                if not url.is_target and url.depth <= url.max_depth:
                    await self.process_seed_recursively(
                        url,
                        config_log_id,
                        is_root_url=False
                    )
                    
        except Exception as e:
            self.logger.error(
                "Error in recursive seed processing",
                url=str(frontier_url.url),
                error=str(e)
            )

    async def run_crawler(self):
        """Run the crawler processing URLs sequentially."""
        with logfire.span('run_crawler'):
            try:
                await self._init_crawler()
                
                # Process categories sequentially
                for category in self.config['crawler']['categories']:
                    # Process URLs in category sequentially
                    for url_config in category.urls:
                        config_url = FrontierUrl(
                            url=url_config.url,
                            category=category.name,
                            url_type=UrlType(url_config.type),
                            max_depth=url_config.max_depth,
                            target_patterns=url_config.target_patterns,
                            seed_pattern=url_config.seed_pattern
                        )
                        
                        await self.process_config_url(config_url)

                    self.logger.info(
                        "Category processing completed",
                        category_name=category.name
                    )

                self.logger.info("All categories processed successfully")
                
            except Exception as e:
                self.logger.error("Crawler execution failed", error=str(e))
                raise

    async def cleanup(self):
        """Cleanup resources."""
        with logfire.span('cleanup'):
            if self.db_connection:
                self.db_connection.close()
                self.logger.info("Database connection closed")

    async def run(self):
        """Main application execution flow."""
        with logfire.span('app_run'):
            try:
                await self.load_config()
                await self.init_database()
                await self.run_crawler()
                self.logger.info("Application completed successfully")
            except Exception as e:
                self.logger.error("Application failed", error=str(e))
                raise
            finally:
                await self.cleanup()