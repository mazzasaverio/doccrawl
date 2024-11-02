# src/core/strategies/type_1.py
from typing import List, Set
import logfire
from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl

class Type1Strategy(CrawlerStrategy):
    """
    Strategy for Type 1 URLs (single page with target links).
    
    This strategy handles pages that contain target document links.
    It processes a single page to find and collect all matching target URLs.
    """
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute Type 1 strategy for pages containing target links.
        
        Args:
            frontier_url: Current FrontierUrl to process
            
        Returns:
            List of FrontierUrl: List of target URLs found
        """
        try:
            self.logger.info(
                "Processing page for target links",
                url=str(frontier_url.url)
            )

            # Validate target patterns
            if not frontier_url.target_patterns:
                self.logger.error(
                    "No target patterns specified for Type 1 URL",
                    url=str(frontier_url.url)
                )
                return []

            # Navigate to page
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                self.logger.error(
                    "Failed to access URL",
                    url=str(frontier_url.url),
                    status=response.status if response else None
                )
                return []

            # Wait for page to be ready
            await self._wait_for_page_ready()
            
            # Handle dynamic elements (popups, load more buttons, etc)
            await self._handle_dynamic_elements()
            
            # Extract all URLs from the page
            all_urls = await self._get_page_urls()
            
            # Extract file-specific URLs
            file_urls = await self._extract_file_urls()
            all_urls.update(file_urls)
            
            new_urls = []
            
            # Process found URLs
            for url in all_urls:
                # Skip same URL as parent
                if url == str(frontier_url.url):
                    continue
                    
                # Check if URL matches target patterns
                if self._is_target_url(url, frontier_url.target_patterns):
                    # Skip if URL already exists in frontier
                    if self.frontier_crud and \
                       await self.frontier_crud.exists_in_frontier(url):
                        self.logger.debug(
                            "Target URL already in frontier",
                            url=url
                        )
                        continue
                        
                    # Create new frontier URL
                    new_frontier_url = self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    )
                    new_urls.append(new_frontier_url)
                    
                    self.logger.debug(
                        "Found new target URL",
                        url=url
                    )

            self.logger.info(
                "Page processing completed",
                url=str(frontier_url.url),
                targets_found=len(new_urls)
            )
            
            return new_urls

        except Exception as e:
            self.logger.error(
                "Error processing Type 1 URL",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []