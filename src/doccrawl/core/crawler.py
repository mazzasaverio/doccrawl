# src/core/crawler.py
from typing import Dict, List, Type, Optional, AsyncIterator
import asyncio
import subprocess
from playwright.async_api import async_playwright, Browser, BrowserContext
import logfire
from contextlib import asynccontextmanager

from .strategies.base_strategy import CrawlerStrategy
from .strategies.type_0 import Type0Strategy
from .strategies.type_1 import Type1Strategy
from .strategies.type_2 import Type2Strategy
from .strategies.type_3 import Type3Strategy
from .strategies.type_4 import Type4Strategy
from ..models.frontier_model import FrontierUrl, UrlType, UrlStatus, FrontierBatch
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
   async def _get_browser_context(self) -> AsyncIterator[BrowserContext]:
       """
       Context manager for browser and context lifecycle.
       
       Yields:
           BrowserContext: A configured browser context
       """
       playwright = None
       browser = None
       context = None
       
       try:
           playwright = await async_playwright().start()
           browser = await playwright.chromium.launch(
               headless=True
           )
           context = await browser.new_context(
               viewport={'width': 1280, 'height': 800},
               ignore_https_errors=True,
               user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
           )
           
           # Set default timeout
           context.set_default_timeout(30000)
           
           yield context
           
       except Exception as e:
           self.logger.error("Failed to create browser context", error=str(e))
           raise
           
       finally:
           if context:
               await context.close()
           if browser:
               await browser.close()
           if playwright:
               await playwright.stop()
   
   async def initialize(self) -> None:
       """Initialize Playwright and verify browser installation."""
       await self._initialize_playwright()

   @staticmethod
   async def _initialize_playwright() -> None:
       """Initialize Playwright and check browser setup."""
       try:
           # Check if browser is installed
           async with async_playwright() as p:
               try:
                   browser = await p.chromium.launch()
                   await browser.close()
                 
               except Exception as e:
                   if "Executable doesn't exist" in str(e):
                       logfire.info("Installing Playwright browser...")
                       result = subprocess.run(
                           ["playwright", "install", "chromium"],
                           capture_output=True,
                           text=True,
                           check=True
                       )
                       if result.returncode == 0:
                           logfire.info("Successfully installed Playwright browser")
                       else:
                           raise RuntimeError(
                               f"Failed to install browser: {result.stderr}"
                           )
                   else:
                       raise
                       
       except Exception as e:
           logfire.error("Failed to initialize Playwright", error=str(e))
           raise
   
   async def _process_url(
       self,
       frontier_url: FrontierUrl,
       frontier_crud: FrontierCRUD,
       browser_context: BrowserContext
   ) -> None:
       """
       Process a single URL using appropriate strategy.
       
       Args:
           frontier_url: FrontierUrl instance to process
           frontier_crud: CRUD operations handler
           browser_context: Browser context for page creation
       """
       try:
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
               
             
               
               # Execute strategy
               new_urls = await strategy.execute(frontier_url)
               
               # Save new URLs to frontier
               if new_urls:
                   batch = FrontierBatch(urls=new_urls)
                   frontier_crud.create_urls_batch(batch)
               
               # Mark URL as processed
               if frontier_url.id:
                   frontier_crud.update_url_status(
                       frontier_url.id,
                       UrlStatus.PROCESSED
                   )
               
               self.logger.info(
                   "URL processed successfully",
                 
                   new_urls_found=len(new_urls)
               )
               
           except Exception as e:
               self.logger.error(
                   "Error processing URL",
                   url=str(frontier_url.url),
                   error=str(e)
               )
               if frontier_url.id:
                   frontier_crud.update_url_status(
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
   async def process_single_url(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
    """
    Process a single URL and return discovered URLs.
    
    Args:
        frontier_url: FrontierUrl instance to process
        
    Returns:
        List of newly discovered FrontierUrls
    """
    try:
        strategy_class = self.strategies.get(frontier_url.url_type)
        if not strategy_class:
            self.logger.error(
                "Unknown URL type",
                url=str(frontier_url.url),
                type=frontier_url.url_type
            )
            return []

        async with self._get_browser_context() as context:
            page = await context.new_page()
            
            try:
                strategy = strategy_class(
                    frontier_crud=None,
                    playwright_page=page,
                    scrapegraph_api_key=self.scrapegraph_api_key
                )

                new_urls = await strategy.execute(frontier_url)
                
       
                
                return new_urls if new_urls else []

            except Exception as e:
                self.logger.error(
                    "Error processing URL",
                    url=str(frontier_url.url),
                    error=str(e)
                )
                return []
            finally:
                await page.close()

    except Exception as e:
        self.logger.error(
            "Critical error in process_single_url",
            url=str(frontier_url.url),
            error=str(e)
        )
        return []
       
   async def run(self, db_connection: DatabaseConnection) -> None:
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
                   pending_urls = frontier_crud.get_pending_urls(
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