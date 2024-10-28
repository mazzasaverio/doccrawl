# src/core/crawler.py
from typing import Dict, Type, Optional
import asyncio
from playwright.async_api import async_playwright
import logfire
from contextlib import asynccontextmanager

from .strategies.base_strategy import CrawlerStrategy
from .strategies.type_0 import Type0Strategy
from .strategies.type_1 import Type1Strategy
from .strategies.type_2 import Type2Strategy
from .strategies.type_3 import Type3Strategy
from .strategies.type_4 import Type4Strategy
from ..models.frontier_model import FrontierUrl, UrlType, UrlStatus
from ..crud.frontier_crud import FrontierCRUD
from ..db.connection import DatabaseConnection

class Crawler:
    """Main crawler class that orchestrates the crawling process."""
    
    def __init__(
        self,
        scrapegraph_api_key: Optional[str] = None,
        max_concurrent_pages: int = 5,
        batch_size: int = 10
    ):
        self.logger = logfire
        self.scrapegraph_api_key = scrapegraph_api_key
        self.max_concurrent_pages = max_concurrent_pages
        self.batch_size = batch_size
        
        # Map URL types to their corresponding strategies
        self.strategies: Dict[UrlType, Type[CrawlerStrategy]] = {
            UrlType.DIRECT_TARGET: Type0Strategy,
            UrlType.SINGLE_PAGE: Type1Strategy,
            UrlType.SEED_TARGET: Type2Strategy,
            UrlType.COMPLEX_AI: Type3Strategy,
            UrlType.FULL_AI: Type4Strategy
        }
    
    @asynccontextmanager
    async def _get_browser_context(self):
        """Creates and manages browser context."""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            try:
                yield context
            finally:
                await context.close()
                await browser.close()
    
    async def _process_url(
        self,
        frontier_url: FrontierUrl,
        frontier_crud: FrontierCRUD,
        browser_context
    ):
        """Process a single URL using appropriate strategy."""
        try:
            # Create new page
            page = await browser_context.new_page()
            
            try:
                # Get appropriate strategy
                strategy_class = self.strategies.get(frontier_url.url_type)
                if not strategy_class:
                    raise ValueError(f"Unknown URL type: {frontier_url.url_type}")
                
                # Initialize strategy
                strategy = strategy_class(
                    frontier_crud=frontier_crud,
                    playwright_page=page,
                    scrapegraph_api_key=self.scrapegraph_api_key
                )
                
                # Mark URL as processing
                await frontier_crud.update_url_status(
                    frontier_url.id,
                    UrlStatus.PROCESSING
                )
                
                # Execute strategy
                new_urls = await strategy.execute(frontier_url)
                
                # Save new URLs to frontier
                if new_urls:
                    await frontier_crud.create_urls_batch(new_urls)
                
                # Mark URL as processed
                await frontier_crud.update_url_status(
                    frontier_url.id,
                    UrlStatus.PROCESSED
                )
                
                self.logger.info(
                    "URL processed successfully",
                    url=str(frontier_url.url),
                    new_urls_found=len(new_urls)
                )
                
            except Exception as e:
                self.logger.error(
                    "Error processing URL",
                    url=str(frontier_url.url),
                    error=str(e)
                )
                await frontier_crud.update_url_status(
                    frontier_url.id,
                    UrlStatus.FAILED,
                    error_message=str(e)
                )
                
            finally:
                await page.close()
                
        except Exception as e:
            self.logger.error(
                "Error in page creation",
                url=str(frontier_url.url),
                error=str(e)
            )
    
    async def run(self, db_connection: DatabaseConnection):
        """
        Main crawling loop.
        
        Args:
            db_connection: Database connection instance
        """
        frontier_crud = FrontierCRUD(db_connection)
        
        async with self._get_browser_context() as browser_context:
            while True:
                try:
                    # Get batch of pending URLs
                    pending_urls = await frontier_crud.get_pending_urls(
                        limit=self.batch_size
                    )
                    
                    if not pending_urls:
                        self.logger.info("No pending URLs found. Crawler finished.")
                        break
                    
                    # Process URLs concurrently
                    tasks = [
                        self._process_url(url, frontier_crud, browser_context)
                        for url in pending_urls
                    ]
                    
                    await asyncio.gather(*tasks)
                    
                except Exception as e:
                    self.logger.error(
                        "Error in crawler run loop",
                        error=str(e)
                    )
                    await asyncio.sleep(5)  # Wait before retrying