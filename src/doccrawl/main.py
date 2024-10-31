import asyncio
import sys
from pathlib import Path
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
        self.logger = logfire.getLogger(__name__)
        self.config = None
        self.db_connection = None
        self.frontier_crud = None

    async def load_config(self) -> dict:
        """Load crawler configuration."""
        with logfire.span('load_config'):
            try:
                self.config = settings.model_dump()
                self.logger.info("Configuration loaded successfully")
                return self.config
                
            except Exception as e:
                self.logger.error(
                    "Error loading configuration",
                    error=str(e),
                    config_locations=str([
                        "config/crawler_config.yaml",
                        "crawler_config.yaml",
                        str(Path(__file__).parent.parent.parent / "config" / "crawler_config.yaml"),
                        str(Path.home() / ".config" / "doccrawl" / "crawler_config.yaml")
                    ])
                )
                raise

    async def init_database(self):
        """Initialize database connection and tables."""
        with logfire.span('init_database'):
            try:
                self.db_connection = DatabaseConnection()
                self.db_connection.connect()
                self.db_connection.create_tables()
                self.frontier_crud = FrontierCRUD(self.db_connection)
                
                self.logger.info("Database initialized successfully")
                
            except Exception as e:
                self.logger.error("Database initialization failed", error=str(e))
                raise


    async def initialize_frontier(self):
        """Initialize frontier with URLs from configuration."""
        with logfire.span('initialize_frontier') as span:
            try:
                urls_to_create = []
                
                for category in self.config['crawler']['categories']:
                    span.set_attribute('current_category', category['name'])
                    
                    for url_config in category['urls']:
                        frontier_url = FrontierUrl(
                            url=url_config['url'],
                            category=category['name'],
                            url_type=UrlType(url_config['type']),
                            max_depth=url_config['max_depth'],
                            target_patterns=url_config.get('target_patterns'),
                            seed_pattern=url_config.get('seed_pattern')
                        )
                        urls_to_create.append(frontier_url)
                
                if urls_to_create:
                    batch = FrontierBatch(urls=urls_to_create)
                    await self.frontier_crud.create_urls_batch(batch)
                    
                    self.logger.info(
                        "Frontier initialized",
                        urls_count=len(urls_to_create)
                    )
                
            except Exception as e:
                self.logger.error("Error initializing frontier", error=str(e))
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
                
                self.logger.info("Crawler execution completed")
                
            except Exception as e:
                self.logger.error("Error during crawler execution", error=str(e))
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
                await self.initialize_frontier()
                await self.run_crawler()
                
                self.logger.info("Application completed successfully")
                
            except Exception as e:
                self.logger.error("Application failed", error=str(e))
                raise
            finally:
                await self.cleanup()

async def main():
    """Entry point for the application."""
    app = CrawlerApp()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())