import os
import asyncio
import yaml
import logfire
from pathlib import Path
from dotenv import load_dotenv

from .db.connection import DatabaseConnection
from .core.crawler import Crawler
from .models.frontier_model import FrontierUrl, UrlType, FrontierBatch
from .crud.frontier_crud import FrontierCRUD

class CrawlerApp:
    """Main application class for document crawler."""
    
    def __init__(self):
        self.logger = logfire.getLogger(__name__)
        self.config = None
        self.db_connection = None
        self.frontier_crud = None
        
    async def load_config(self) -> dict:
        """
        Load crawler configuration from YAML file.
        
        Returns:
            Dictionary containing configuration
        """
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'crawler_config.yaml'
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                self.logger.info("Configuration loaded successfully")
                return self.config
        except Exception as e:
            self.logger.error(
                "Error loading configuration",
                error=str(e)
            )
            raise

    async def init_database(self):
        """Initialize database connection and tables."""
        try:
            self.db_connection = DatabaseConnection()
            self.db_connection.connect()
            self.db_connection.create_tables()
            self.frontier_crud = FrontierCRUD(self.db_connection)
            self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(
                "Database initialization failed",
                error=str(e)
            )
            raise

    async def initialize_frontier(self):
        """Initialize frontier with URLs from configuration."""
        try:
            urls_to_create = []
            
            for category in self.config['crawler']['categories']:
                self.logger.info(
                    "Processing category",
                    category=category['name']
                )
                
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
            
            # Create URLs in batch
            if urls_to_create:
                batch = FrontierBatch(urls=urls_to_create)
                await self.frontier_crud.create_urls_batch(batch)
                
                self.logger.info(
                    "Frontier initialized",
                    urls_count=len(urls_to_create)
                )
                
        except Exception as e:
            self.logger.error(
                "Error initializing frontier",
                error=str(e)
            )
            raise

    async def run_crawler(self):
        """Create and run the crawler."""
        try:
            crawler = Crawler(
                scrapegraph_api_key=os.getenv('SCRAPEGRAPH_API_KEY'),
                max_concurrent_pages=int(os.getenv('MAX_CONCURRENT_PAGES', '5')),
                batch_size=int(os.getenv('BATCH_SIZE', '10'))
            )
            
            await crawler.run(self.db_connection)
            
            self.logger.info("Crawler execution completed")
            
        except Exception as e:
            self.logger.error(
                "Error during crawler execution",
                error=str(e)
            )
            raise

    async def cleanup(self):
        """Cleanup resources."""
        if self.db_connection:
            self.db_connection.close()
            self.logger.info("Database connection closed")

    async def run(self):
        """Main application execution flow."""
        try:
            # Configure logging
            logfire.configure(
                level=os.getenv('LOG_LEVEL', 'INFO'),
                format="{time} | {level} | {message}"
            )
            
            # Load environment variables
            load_dotenv()
            
            # Application flow
            await self.load_config()
            await self.init_database()
            await self.initialize_frontier()
            await self.run_crawler()
            
            self.logger.info("Application completed successfully")
            
        except Exception as e:
            self.logger.error(
                "Application failed",
                error=str(e)
            )
            raise
        finally:
            await self.cleanup()

async def main():
    """Entry point for the application."""
    app = CrawlerApp()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())