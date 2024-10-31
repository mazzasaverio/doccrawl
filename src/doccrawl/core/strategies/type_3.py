
# src/core/strategies/type_3.py
from typing import List, Set, Tuple
import logfire

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl
from ...utils.crawler_utils import CrawlerUtils

class Type3Strategy(CrawlerStrategy):
    """
    Strategy for Type 3 URLs (three-level crawling with AI assistance).
    
    Depth 0: Uses regex patterns
    Depth 1: Uses ScrapegraphAI
    Depth 2: Only collects targets
    """
    
    async def _process_depth_0(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Process initial page using regex patterns."""
        try:
            response = await self.page.goto(str(frontier_url.url))
            if not await CrawlerUtils.is_valid_response(response):
                return []
                
            await CrawlerUtils.wait_for_page_load(self.page)
            
            # Extract links using patterns
            all_urls = await CrawlerUtils.extract_links_from_page(
                self.page,
                str(frontier_url.url)
            )
            
            new_urls = []
            
            # Find target URLs
            target_urls = {
                url for url in all_urls
                if CrawlerUtils.matches_patterns(url, frontier_url.target_patterns)
            }
            
            # Find seed URLs
            seed_urls = {
                url for url in all_urls
                if frontier_url.seed_pattern and 
                CrawlerUtils.matches_patterns(url, [frontier_url.seed_pattern])
            }
            
            # Create frontier URLs
            for url in target_urls:
                if not self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))
                    
            for url in seed_urls:
                if not self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url
                    ))
                    
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing depth 0",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
    
    async def _process_depth_1(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Process page using ScrapegraphAI."""
        try:
            response = await self.page.goto(str(frontier_url.url))
            if not await CrawlerUtils.is_valid_response(response):
                return []
                
            await CrawlerUtils.wait_for_page_load(self.page)
            
            # Use ScrapegraphAI to identify URLs
            target_urls, seed_urls = await CrawlerUtils.analyze_with_scrapegraph(
                self.page,
                self.scrapegraph_api_key,
                'extract_links'
            )
            
            new_urls = []
            
            # Create frontier URLs
            for url in target_urls:
                if not self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))
                    
            for url in seed_urls:
                if not self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url
                    ))
                    
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing depth 1",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
    
    async def _process_depth_2(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Process final depth, collecting only target URLs."""
        try:
            response = await self.page.goto(str(frontier_url.url))
            if not await CrawlerUtils.is_valid_response(response):
                return []
                
            await CrawlerUtils.wait_for_page_load(self.page)
            
            # Extract all links
            all_urls = await CrawlerUtils.extract_links_from_page(
                self.page,
                str(frontier_url.url)
            )
            
            # Filter target URLs
            target_urls = {
                url for url in all_urls
                if CrawlerUtils.matches_patterns(url, frontier_url.target_patterns)
            }
            
            # Create frontier URLs for targets
            new_urls = []
            for url in target_urls:
                if not self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))
                    
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing depth 2",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute Type 3 strategy based on current depth.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List of discovered URLs
        """
        try:
            if frontier_url.depth == 0:
                return await self._process_depth_0(frontier_url)
            elif frontier_url.depth == 1:
                return await self._process_depth_1(frontier_url)
            elif frontier_url.depth == 2:
                return await self._process_depth_2(frontier_url)
            else:
                self.logger.error(
                    "Invalid depth for Type 3 URL",
                    url=str(frontier_url.url),
                    depth=frontier_url.depth
                )
                return []
                
        except Exception as e:
            self.logger.error(
                "Error executing Type 3 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
