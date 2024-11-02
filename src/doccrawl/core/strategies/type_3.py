# src/core/strategies/type_3.py
from typing import List, Set, Tuple
import logfire
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl

class Type3Strategy(CrawlerStrategy):
    """
    Strategy for Type 3 URLs with AI assistance.
    
    Depth 0: Uses regex patterns
    Depth 1: Uses ScrapegraphAI
    Depth 2: Only collects targets
    """
    
    async def _process_depth_0(
        self, 
        frontier_url: FrontierUrl
    ) -> List[FrontierUrl]:
        """Process initial page using regex patterns."""
        try:
            self.logger.info(
                "Processing depth 0",
                url=str(frontier_url.url)
            )
            
            # Navigate and wait for page
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return []

            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            # Get all URLs
            all_urls = await self._get_page_urls()
            new_urls = []

            # Process URLs
            for url in all_urls:
                # Skip self-referential URLs
                if url == str(frontier_url.url):
                    continue
                    
                # Check for target URLs
                if frontier_url.target_patterns and \
                   self._is_target_url(url, frontier_url.target_patterns):
                    if not self.frontier_crud or \
                       not await self.frontier_crud.exists_in_frontier(url):
                        new_urls.append(self.create_frontier_url(
                            url=url,
                            parent=frontier_url,
                            is_target=True
                        ))
                        
                # Check for seed URLs
                elif frontier_url.seed_pattern and \
                     self._matches_pattern(url, frontier_url.seed_pattern):
                    if not self.frontier_crud or \
                       not await self.frontier_crud.exists_in_frontier(url):
                        new_urls.append(self.create_frontier_url(
                            url=url,
                            parent=frontier_url,
                            is_target=False
                        ))
                        
            return new_urls

        except Exception as e:
            self.logger.error(
                "Error processing depth 0",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []

    async def _process_depth_1(
        self,
        frontier_url: FrontierUrl
    ) -> List[FrontierUrl]:
        """Process page using ScrapegraphAI at depth 1."""
        try:
            self.logger.info(
                "Processing depth 1 with AI",
                url=str(frontier_url.url)
            )
            
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return []

            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            # Analyze with ScrapegraphAI
            target_urls, seed_urls = await self._analyze_with_scrapegraph()
            
            new_urls = []
            
            # Process target URLs
            for url in target_urls:
                if not self.frontier_crud or \
                   not await self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))

            # Process seed URLs if not at max depth
            if frontier_url.depth < frontier_url.max_depth - 1:
                for url in seed_urls:
                    if not self.frontier_crud or \
                       not await self.frontier_crud.exists_in_frontier(url):
                        new_urls.append(self.create_frontier_url(
                            url=url,
                            parent=frontier_url,
                            is_target=False
                        ))
            
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing depth 1",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []

    async def _process_depth_2(
        self, 
        frontier_url: FrontierUrl
    ) -> List[FrontierUrl]:
        """Process final depth, collecting only target URLs."""
        try:
            self.logger.info(
                "Processing depth 2",
                url=str(frontier_url.url)
            )
            
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

            # At this depth, only collect target URLs
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
            self.logger.info(
                "Executing Type 3 strategy",
                url=str(frontier_url.url),
                depth=frontier_url.depth
            )

            if not frontier_url.target_patterns:
                self.logger.error("No target patterns specified")
                return []

            # Process based on depth
            if frontier_url.depth == 0:
                return await self._process_depth_0(frontier_url)
            elif frontier_url.depth == 1:
                return await self._process_depth_1(frontier_url)
            elif frontier_url.depth == 2:
                return await self._process_depth_2(frontier_url)
            else:
                self.logger.error(
                    "Invalid depth for Type 3 URL",
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