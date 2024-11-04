from typing import List, Set, Tuple, Optional
import asyncio
import time
from urllib.parse import urljoin
import logfire
import nest_asyncio
from playwright.async_api import TimeoutError as PlaywrightTimeout
from scrapegraphai.graphs import SmartScraperMultiGraph
from pydantic import BaseModel

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl, UrlStatus
from ...utils.crawler_utils import CrawlerUtils
from ...config.settings import settings

# Enable nested asyncio for ScrapegraphAI
nest_asyncio.apply()

class Url(BaseModel):
    url: str
    url_description: str
    extension: str
    pagination: str
    url_category: str

class Urls(BaseModel):
    urls: List[Url]

class Type4Strategy(CrawlerStrategy):
    """
    Strategy for Type 4 URLs (multi-level crawling with full AI assistance).
    
    This strategy uses ScrapegraphAI for intelligent URL discovery at all depths
    except the final one. Particularly useful for complex websites where pattern 
    matching isn't sufficient.
    
    Features:
    - Full AI assistance for URL discovery
    - Flexible depth configuration (must be ≥ 2)
    - Rate limiting and politeness controls
    - Skip already processed seeds
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_urls = set()
        self.rate_limiter = asyncio.Semaphore(2)
        self.last_request_time = {}
    
    async def _wait_for_rate_limit(self, domain: str) -> None:
        """
        Implements rate limiting per domain.
        
        Args:
            domain: Domain being accessed
        """
        try:
            async with self.rate_limiter:
                if domain in self.last_request_time:
                    elapsed = time.time() - self.last_request_time[domain]
                    if elapsed < 2.0:  # 2 second minimum delay
                        await asyncio.sleep(2.0 - elapsed)
                self.last_request_time[domain] = time.time()
                
        except Exception as e:
            self.logger.warning(
                "Rate limiting error",
                domain=domain,
                error=str(e)
            )

    async def _analyze_with_scrapegraph(self, url: str) -> Tuple[Set[str], Set[str]]:
        """
        Analyze page using ScrapegraphAI.
        
        Args:
            url: URL to analyze
            
        Returns:
            Tuple[Set[str], Set[str]]: Sets of (target_urls, seed_urls)
        """
        try:
            if not self.scrapegraph_api_key:
                self.logger.error("ScrapegraphAI API key not provided")
                return set(), set()

            # Get configuration from settings
            graph_config = {
                "llm": {
                    "api_key": self.scrapegraph_api_key,
                    "model": settings.crawler_config.default_settings.get("graph_config", {}).get("model", "openai/gpt-4o-mini"),
                    "temperature": 0,
                },
                "verbose": settings.crawler_config.default_settings.get("graph_config", {}).get("verbose", False),
                "headless": settings.crawler_config.default_settings.get("graph_config", {}).get("headless", True),
            }

            # Get prompt from settings
            prompt = settings.crawler_config.default_settings.get("graph_config", {}).get("prompts", {}).get("general")

            # Initialize and run ScrapegraphAI
            search_graph = SmartScraperMultiGraph(
                prompt=prompt,
                config=graph_config,
                source=[url],
                schema=Urls
            )

            result = search_graph.run()

            # Extract seed and target URLs
            seed_urls = {
                url_data['url'] 
                for url_data in result['urls']
                if url_data['url_category'] == 'seed' and url_data['pagination'] != 'true'
            }

            target_urls = {
                url_data['url']
                for url_data in result['urls']
                if url_data['url_category'] == 'target'
            }

            return target_urls, seed_urls

        except Exception as e:
            self.logger.error(
                "Error in ScrapegraphAI analysis",
                url=url,
                error=str(e)
            )
            return set(), set()
    
    async def _process_with_ai(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Process a page using AI assistance for URL discovery.
        
        Args:
            frontier_url: Current FrontierUrl being processed
            
        Returns:
            List of new FrontierUrl instances
        """
        domain = CrawlerUtils.extract_domain(str(frontier_url.url))
        await self._wait_for_rate_limit(domain)
        
        try:
            # Navigate to page
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return []

            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            # Analyze with ScrapegraphAI
            target_urls, seed_urls = await self._analyze_with_scrapegraph(str(frontier_url.url))
            
            # Create new frontier URLs
            new_urls = []
            
            # Add target URLs
            for url in target_urls:
                # Skip if URL already exists
                if not self.frontier_crud or not await self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))
            
            # Add seed URLs if not at max depth
            if frontier_url.depth < frontier_url.max_depth - 1:
                for url in seed_urls:
                    # Skip if URL already exists or was visited
                    if (not self.frontier_crud or not await self.frontier_crud.exists_in_frontier(url)) and \
                       url not in self.visited_urls:
                        new_urls.append(self.create_frontier_url(
                            url=url,
                            parent=frontier_url,
                            is_target=False
                        ))
                        self.visited_urls.add(url)
            
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error in AI processing",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
    
    async def _process_final_depth(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Process final depth page, collecting only target URLs.
        
        Args:
            frontier_url: Current FrontierUrl being processed
            
        Returns:
            List of new target FrontierUrl instances
        """
        domain = CrawlerUtils.extract_domain(str(frontier_url.url))
        await self._wait_for_rate_limit(domain)
        
        try:
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return []

            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            # Get all URLs including file URLs
            all_urls = await self._get_page_urls()
            file_urls = await self._extract_file_urls()
            all_urls.update(file_urls)
            
            new_urls = []

            # At final depth, only collect target URLs
            for url in all_urls:
                if frontier_url.target_patterns and \
                   self._is_target_url(url, frontier_url.target_patterns):
                    if not self.frontier_crud or \
                       not await self.frontier_crud.exists_in_frontier(url):
                        new_urls.append(self.create_frontier_url(
                            url=url,
                            parent=frontier_url,
                            is_target=True
                        ))
            
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing final depth",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute Type 4 strategy based on current depth.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List of discovered URLs
        """
        try:
            self.logger.info(
                "Processing Type 4 URL",
                url=str(frontier_url.url),
                depth=frontier_url.depth,
                max_depth=frontier_url.max_depth
            )
            
            # Validate configuration
            if frontier_url.max_depth < 2:
                self.logger.error(
                    "Invalid max_depth for Type 4 URL",
                    url=str(frontier_url.url),
                    max_depth=frontier_url.max_depth
                )
                return []

            # Process based on depth
            if frontier_url.depth < frontier_url.max_depth - 1:
                # Use AI for URL discovery at non-final depths
                new_urls = await self._process_with_ai(frontier_url)
                self.logger.info(
                    "AI processing completed",
                    url=str(frontier_url.url),
                    new_urls_found=len(new_urls),
                    targets_found=len([u for u in new_urls if u.is_target]),
                    seeds_found=len([u for u in new_urls if not u.is_target])
                )
                
            elif frontier_url.depth == frontier_url.max_depth - 1:
                # At final depth, only collect target URLs
                new_urls = await self._process_final_depth(frontier_url)
                self.logger.info(
                    "Final depth processing completed",
                    url=str(frontier_url.url),
                    targets_found=len(new_urls)
                )
                
            else:
                self.logger.error(
                    "Invalid depth for Type 4 URL",
                    url=str(frontier_url.url),
                    depth=frontier_url.depth
                )
                return []
            
            # Update frontier URL status
            if frontier_url.id is not None:
                await self.frontier_crud.update_url_status(
                    frontier_url.id,
                    UrlStatus.PROCESSED
                )
            
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error executing Type 4 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            if frontier_url.id is not None:
                await self.frontier_crud.update_url_status(
                    frontier_url.id,
                    UrlStatus.FAILED,
                    error_message=str(e)
                )
            return []