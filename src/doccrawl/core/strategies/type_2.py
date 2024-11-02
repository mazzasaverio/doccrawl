# src/core/strategies/type_2.py
from typing import List, Set, Tuple
import logfire
from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl

class Type2Strategy(CrawlerStrategy):
    """
    Strategy for Type 2 URLs (seed and target pages with one level depth).
    Combines target URL collection with one level of seed URL exploration.
    """
    
    async def _extract_page_urls(
        self, 
        url: str,
        frontier_url: FrontierUrl
    ) -> Tuple[Set[str], Set[str]]:
        """
        Extract both target and seed URLs from a page.
        
        Args:
            url: Current URL to process
            frontier_url: Parent FrontierUrl instance
            
        Returns:
            Tuple[Set[str], Set[str]]: Sets of target and seed URLs
        """
        try:
            # Navigate to page
            response = await self.page.goto(url)
            if not response or response.status != 200:
                return set(), set()

            # Wait for page load and handle dynamic elements
            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            # Get all URLs
            all_urls = await self._get_page_urls()
            
            # Get additional file URLs
            file_urls = await self._extract_file_urls()
            all_urls.update(file_urls)
            
            # Separate target and seed URLs
            target_urls = {
                url for url in all_urls 
                if self._is_target_url(url, frontier_url.target_patterns)
            }
            
            seed_urls = {
                url for url in all_urls
                if frontier_url.seed_pattern and 
                self._matches_pattern(url, frontier_url.seed_pattern) and
                url != str(frontier_url.url)  # Exclude self-referential URLs
            }
                    
            return target_urls, seed_urls

        except Exception as e:
            self.logger.error(
                "Error extracting URLs from page",
                url=url,
                error=str(e)
            )
            return set(), set()

    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute Type 2 strategy.
        First processes current page for targets, then follows seeds one level deep.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List of FrontierUrl: Combined list of discovered URLs
        """
        try:
            self.logger.info(
                "Processing Type 2 URL",
                url=str(frontier_url.url),
                depth=frontier_url.depth
            )

            new_urls = []
            current_depth = frontier_url.depth

            if not frontier_url.target_patterns:
                self.logger.error("No target patterns specified")
                return []

            # Process current page
            target_urls, seed_urls = await self._extract_page_urls(
                str(frontier_url.url),
                frontier_url
            )

            # Add found target URLs
            for url in target_urls:
                if not self.frontier_crud or \
                   not await self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))

            # If not at max depth, process seed URLs
            if current_depth < frontier_url.max_depth:
                for seed_url in seed_urls:
                    # Skip if seed already in frontier
                    if self.frontier_crud and \
                       await self.frontier_crud.exists_in_frontier(seed_url):
                        self.logger.debug(
                            "Seed URL already in frontier",
                            url=seed_url
                        )
                        continue
                    
                    # Create frontier URL for seed
                    seed_frontier_url = self.create_frontier_url(
                        url=seed_url,
                        parent=frontier_url,
                        is_target=False
                    )
                    new_urls.append(seed_frontier_url)
                    
                    # Process seed page for targets
                    seed_targets, _ = await self._extract_page_urls(
                        seed_url,
                        frontier_url
                    )
                    
                    # Add target URLs found in seed
                    for target_url in seed_targets:
                        if not self.frontier_crud or \
                           not await self.frontier_crud.exists_in_frontier(target_url):
                            new_urls.append(self.create_frontier_url(
                                url=target_url,
                                parent=seed_frontier_url,
                                is_target=True
                            ))

            self.logger.info(
                "Type 2 processing completed",
                url=str(frontier_url.url),
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
            return []