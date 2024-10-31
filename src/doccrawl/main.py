"""Main application module."""
import asyncio
from pathlib import Path
from pprint import pp
import logfire

from doccrawl.config.settings import settings
from doccrawl.db.connection import DatabaseConnection
from doccrawl.core.crawler import Crawler
from doccrawl.models.frontier_model import FrontierUrl, UrlType, FrontierBatch
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

    async def load_config(self) -> dict:
        """Load crawler configuration."""
        with logfire.span('load_config'):
            try:
                # Converte la configurazione in un dizionario per mantenere la compatibilità
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

    async def initialize_frontier(self):
        """Initialize frontier with URLs from configuration."""
        with logfire.span('initialize_frontier') as span:
            try:
                urls_to_create = []
                
                # Accedi alle categorie dal config
                categories = self.config['crawler']['categories']
                if not categories:
                    logfire.warning("No categories found in configuration")
                    return

               
                for category in categories:
                   
                
                    for url_config in category.urls:
                       
                        logfire.info('url_config', url_config=url_config)
                        frontier_url = FrontierUrl(
                            url=url_config.url,
                            category=category.name,
                            url_type=UrlType(url_config.type),
                            max_depth=url_config.max_depth,
                            target_patterns=url_config.target_patterns,
                            seed_pattern=url_config.seed_pattern
                        )
                        urls_to_create.append(frontier_url)
                
                if urls_to_create:
                    batch = FrontierBatch(urls=urls_to_create)
                    await self.frontier_crud.create_urls_batch(batch)
                    
                    logfire.info(
                        "Frontier initialized",
                        urls_count=len(urls_to_create)
                    )
                
            except Exception as e:
                logfire.error("Error initializing frontier", error=str(e))
                raise

    async def run_crawler(self):
        """Run the crawler."""
        with logfire.span('run_crawler'):
            try:
                crawler = Crawler(
                    scrapegraph_api_key=settings.scrapegraph_api_key,
                    max_concurrent_pages=settings.crawler.max_concurrent_pages,
                    batch_size=settings.crawler.batch_size
                )
                
                await crawler.run(self.db_connection)
                
                logfire.info("Crawler execution completed")
                
            except Exception as e:
                logfire.error("Error during crawler execution", error=str(e))
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
                await self.initialize_frontier()
                await self.run_crawler()
                
                logfire.info("Application completed successfully")
                
            except Exception as e:
                logfire.error("Application failed", error=str(e))
                raise
            finally:
                await self.cleanup()