from typing import List, Set, Tuple
import logfire

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl
from ...utils.crawler_utils import CrawlerUtils

class Type2Strategy(CrawlerStrategy):
    """Strategy for Type 2 URLs (seed and target pages with one level depth)."""
    
    async def _process_seed_page(self, seed_url: str, parent: FrontierUrl) -> Tuple[List[str], List[str]]:
        """
        Process a seed page to extract both target and seed URLs.
        
        Args:
            seed_url: URL of the seed page
            parent: Parent FrontierUrl instance
            
        Returns:
            Tuple of (target_urls, seed_urls)
        """
        try:
            response = await self.page.goto(seed_url)
            if not await CrawlerUtils.is_valid_response(response):
                return [], []
                
            await CrawlerUtils.wait_for_page_load(self.page)
            
            # Extract all links
            all_urls = await CrawlerUtils.extract_links_from_page(
                self.page,
                seed_url
            )
            
            # Separate target and seed URLs
            target_urls = [
                url for url in all_urls
                if CrawlerUtils.matches_patterns(url, parent.target_patterns)
            ]
            
            seed_urls = [
                url for url in all_urls
                if CrawlerUtils.matches_patterns(url, [parent.seed_pattern])
            ] if parent.seed_pattern else []
            
            return target_urls, seed_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing seed page",
                url=seed_url,
                error=str(e)
            )
            return [], []
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Process a Type 2 URL.
        First extracts target URLs from the current page,
        then follows seed URLs one level deep to find more targets.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List of discovered URLs (both targets and seeds)
        """
        try:
            new_urls = []
            current_depth = frontier_url.depth
            
            # Process the initial page
            target_urls, seed_urls = await self._process_seed_page(
                str(frontier_url.url),
                frontier_url
            )
            
            # Add target URLs from initial page
            for url in target_urls:
                if not self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))
            
            # If we haven't reached max depth, process seed URLs
            if current_depth < frontier_url.max_depth:
                for seed_url in seed_urls:
                    # Skip if already in frontier
                    if self.frontier_crud.exists_in_frontier(seed_url):
                        continue
                        
                    # Create frontier URL for seed
                    seed_frontier_url = self.create_frontier_url(
                        url=seed_url,
                        parent=frontier_url
                    )
                    new_urls.append(seed_frontier_url)
                    
                    # Process the seed page
                    seed_targets, _ = await self._process_seed_page(
                        seed_url,
                        frontier_url
                    )
                    
                    # Add target URLs from seed page
                    for target_url in seed_targets:
                        if not self.frontier_crud.exists_in_frontier(target_url):
                            new_urls.append(self.create_frontier_url(
                                url=target_url,
                                parent=seed_frontier_url,
                                is_target=True
                            ))
            
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error executing Type 2 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
