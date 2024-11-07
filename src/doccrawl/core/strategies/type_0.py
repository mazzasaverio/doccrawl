from typing import List, Set, Tuple
import logfire
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl, UrlStatus

class Type0Strategy(CrawlerStrategy):
    """
    Strategy for Type 0 URLs (direct target links).
    
    Features:
    - Handles direct target URLs (e.g., PDF files)
    - Verifies URL accessibility and content type
    - Validates target patterns
    - No crawling depth (max_depth must be 0)
    """
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute Type 0 strategy for direct target URLs.
        
        Args:
            frontier_url: Current FrontierUrl to process
            
        Returns:
            List[FrontierUrl]: List containing the URL if valid, empty otherwise
        """
        try:
            self.logger.info(
                "Processing direct target URL",
                url=str(frontier_url.url)
            )

            # Validate configuration
            if not frontier_url.target_patterns:
                self.logger.error(
                    "No target patterns specified",
                    url=str(frontier_url.url)
                )
                return []

            if frontier_url.max_depth != 0:
                self.logger.error(
                    "Invalid max_depth for Type 0 URL",
                    url=str(frontier_url.url),
                    max_depth=frontier_url.max_depth
                )
                return []

            # Verify if URL matches target patterns
            if not self._is_target_url(str(frontier_url.url), frontier_url.target_patterns):
                self.logger.warning(
                    "URL does not match target patterns",
                    url=str(frontier_url.url),
                    patterns=frontier_url.target_patterns
                )
                return []

            # Verify content type and accessibility
            if not await self._verify_content_type(str(frontier_url.url)):
                self.logger.warning(
                    "Invalid content type or inaccessible URL",
                    url=str(frontier_url.url)
                )
                return []

            # Create a set with single target URL and store it
            target_urls = {str(frontier_url.url)}
            new_urls = await self._store_urls(target_urls, set(), frontier_url)
            
            # Update URL status
            await self._update_url_status(frontier_url, UrlStatus.PROCESSED)

            return new_urls

        except Exception as e:
            self.logger.error(
                "Error executing Type 0 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            await self._update_url_status(
                frontier_url,
                UrlStatus.FAILED,
                error_message=str(e)
            )
            return []