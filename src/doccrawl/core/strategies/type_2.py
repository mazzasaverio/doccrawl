from typing import List, Set, Tuple
import logfire
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl, UrlStatus

class Type2Strategy(CrawlerStrategy):
    """
    Strategy for Type 2 URLs (seed and target pages with one level depth).
    
    Features:
    - Process current page for both target and seed URLs
    - Follow seed URLs one level deep for additional targets
    - Skip already processed seeds
    - Max depth must be 1
    - Requires both target and seed patterns
    """

    async def _process_page_for_urls(
        self,
        url: str,
        frontier_url: FrontierUrl
    ) -> Tuple[Set[str], Set[str]]:
        """
        Process a page to extract target and seed URLs.
        
        Args:
            url: URL to process
            frontier_url: Parent FrontierUrl instance
            
        Returns:
            Tuple[Set[str], Set[str]]: Sets of target and seed URLs found
        """
        try:
            # Navigate to page
            response = await self.page.goto(url)
            if not response or response.status != 200:
                return set(), set()

            # Wait for page load and handle dynamic elements
            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            # Get all URLs from page
            all_urls = await self._get_page_urls()
            file_urls = await self._extract_file_urls()
            all_urls.update(file_urls)
            
            # Skip self-referential URLs
            all_urls = {u for u in all_urls if u != url}
            
            # Separate target and seed URLs
            target_urls = {
                u for u in all_urls 
                if self._is_target_url(u, frontier_url.target_patterns)
            }
            
            seed_urls = set()
            if frontier_url.seed_pattern:
                seed_urls = {
                    u for u in all_urls 
                    if self._matches_pattern(u, frontier_url.seed_pattern)
                }
            
            return target_urls, seed_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing page for URLs",
                url=url,
                error=str(e)
            )
            return set(), set()

    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute Type 2 strategy.
        Process root page for targets and seeds, then process each seed for additional targets.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List[FrontierUrl]: List of discovered URLs
        """
        try:
            self.logger.info(
                "Executing Type 2 strategy",
                url=str(frontier_url.url)
            )

            # Validate configuration
            if not frontier_url.target_patterns:
                self.logger.error("No target patterns specified")
                return []

            if frontier_url.max_depth != 1:
                self.logger.error(
                    "Invalid max_depth for Type 2 URL",
                    max_depth=frontier_url.max_depth
                )
                return []

            if not frontier_url.seed_pattern:
                self.logger.error("No seed pattern specified")
                return []

            # Process root page
            root_targets, root_seeds = await self._process_page_for_urls(
                str(frontier_url.url),
                frontier_url
            )

            # Store initial URLs
            new_urls = await self._store_urls(root_targets, root_seeds, frontier_url)

            # Process each seed page for additional targets
            for stored_url in new_urls:
                if not stored_url.is_target:  # Process only seed URLs
                    seed_targets, _ = await self._process_page_for_urls(
                        str(stored_url.url),
                        frontier_url
                    )
                    
                    # Store targets found in seed page (empty seed_urls set as we're at max depth)
                    additional_urls = await self._store_urls(seed_targets, set(), stored_url)
                    new_urls.extend(additional_urls)

                    # Update seed URL status
                    await self._update_url_status(stored_url, UrlStatus.PROCESSED)

            # Update root URL status
            await self._update_url_status(frontier_url, UrlStatus.PROCESSED)

            self.logger.info(
                "Type 2 strategy execution completed",
                url=str(frontier_url.url),
                new_urls_found=len(new_urls),
                targets_found=len([u for u in new_urls if u.is_target]),
                seeds_found=len([u for u in new_urls if not u.is_target])
            )

            return new_urls

        except Exception as e:
            self.logger.error(
                "Error executing Type 2 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            await self._update_url_status(
                frontier_url,
                UrlStatus.FAILED,
                error_message=str(e)
            )
            return []