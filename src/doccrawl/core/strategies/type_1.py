from typing import List, Set
import logfire
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl, UrlStatus

class Type1Strategy(CrawlerStrategy):
    """
    Strategy for Type 1 URLs (single page with target links).
    
    Features:
    - Process single page to find target URLs
    - Extract file URLs specifically
    - No crawling depth (max_depth must be 0)
    - No seed URLs required
    """
    
    async def _extract_target_urls(self, frontier_url: FrontierUrl) -> Set[str]:
        """
        Extract all target URLs from the page.
        
        Args:
            frontier_url: Current FrontierUrl being processed
            
        Returns:
            Set[str]: Set of target URLs found
        """
        try:
            # Navigate to page
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return set()

            # Wait for page to be ready and handle dynamic elements
            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            # Get all URLs including file URLs
            all_urls = await self._get_page_urls()
            file_urls = await self._extract_file_urls()
            all_urls.update(file_urls)
            
            # Filter target URLs
            target_urls = {
                url for url in all_urls
                if url != str(frontier_url.url) and
                self._is_target_url(url, frontier_url.target_patterns)
            }
            
            return target_urls
            
        except Exception as e:
            self.logger.error(
                "Error extracting target URLs",
                url=str(frontier_url.url),
                error=str(e)
            )
            return set()

    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute Type 1 strategy for pages containing target links.
        
        Args:
            frontier_url: Current FrontierUrl to process
            
        Returns:
            List[FrontierUrl]: List of target URLs found
        """
        try:
            self.logger.info(
                "Processing page for target links",
                url=str(frontier_url.url)
            )

            # Validate configuration
            if not frontier_url.target_patterns:
                self.logger.error("No target patterns specified")
                return []

            if frontier_url.max_depth != 0:
                self.logger.error(
                    "Invalid max_depth for Type 1 URL",
                    max_depth=frontier_url.max_depth
                )
                return []

            # Extract and store target URLs
            target_urls = await self._extract_target_urls(frontier_url)
            new_urls = await self._store_urls(target_urls, set(), frontier_url)

            # Update current URL status
            await self._update_url_status(frontier_url, UrlStatus.PROCESSED)

            self.logger.info(
                "Page processing completed",
                url=str(frontier_url.url),
                targets_found=len(new_urls)
            )
            
            return new_urls

        except Exception as e:
            self.logger.error(
                "Error executing Type 1 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            await self._update_url_status(
                frontier_url,
                UrlStatus.FAILED,
                error_message=str(e)
            )
            return []