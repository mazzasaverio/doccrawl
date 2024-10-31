
# src/core/strategies/type_1.py
from typing import List, Set
import logfire

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl
from ...utils.crawler_utils import CrawlerUtils

class Type1Strategy(CrawlerStrategy):
    """Strategy for Type 1 URLs (single page with target links)."""
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Process a Type 1 URL.
        Extracts target document links from the page.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List of discovered target URLs
        """
        try:
            # Navigate to page
            response = await self.page.goto(str(frontier_url.url))
            if not await CrawlerUtils.is_valid_response(response):
                return []
                
            # Wait for page to load
            if not await CrawlerUtils.wait_for_page_load(self.page):
                return []
                
            # Extract all links
            base_url = str(frontier_url.url)
            all_urls = await CrawlerUtils.extract_links_from_page(
                self.page,
                base_url
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
                    new_url = self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    )
                    new_urls.append(new_url)
                    
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing Type 1 URL",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []

