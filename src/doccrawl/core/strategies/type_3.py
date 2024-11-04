from typing import List, Set, Tuple
import logfire
from playwright.async_api import TimeoutError as PlaywrightTimeout
import nest_asyncio
from scrapegraphai.graphs import SmartScraperMultiGraph
from pydantic import BaseModel

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl, UrlStatus
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

class Type3Strategy(CrawlerStrategy):
    """
    Strategy for Type 3 URLs with three-level crawling and AI assistance.
    
    Depth Behavior:
    - Depth 0: Uses regex patterns for both seed and target URLs
    - Depth 1: Uses ScrapegraphAI to identify both seeds and targets
    - Depth 2: Only collects target URLs matching patterns
    
    Features:
    - Pattern-based URL discovery at depth 0
    - AI-assisted URL discovery at depth 1
    - Target-only collection at depth 2
    - Skip already processed seeds
    - Comprehensive error handling
    """
    
    async def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped."""
        if self.frontier_crud is None:
            return False
        return await self.frontier_crud.exists_in_frontier(url)
    
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

            if not frontier_url.target_patterns or not frontier_url.seed_pattern:
                self.logger.error("Missing required patterns for depth 0")
                return []

            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return []

            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            all_urls = await self._get_page_urls()
            file_urls = await self._extract_file_urls()
            all_urls.update(file_urls)
            
            new_urls = []

            for url in all_urls:
                if url == str(frontier_url.url):
                    continue

                if self._is_target_url(url, frontier_url.target_patterns):
                    if not await self._should_skip_url(url):
                        new_urls.append(self.create_frontier_url(
                            url=url,
                            parent=frontier_url,
                            is_target=True
                        ))
                elif self._matches_pattern(url, frontier_url.seed_pattern):
                    if not await self._should_skip_url(url):
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

    async def _analyze_with_scrapegraph(self, url: str) -> Tuple[Set[str], Set[str]]:
        """Analyze page using ScrapegraphAI."""
        try:
            if not self.scrapegraph_api_key:
                self.logger.error("ScrapegraphAI API key not provided")
                return set(), set()

            graph_config = {
                "llm": {
                    "api_key": self.scrapegraph_api_key,
                    "model": settings.crawler_config.default_settings.get("graph_config", {}).get("model", "openai/gpt-4o-mini"),
                    "temperature": 0,
                },
                "verbose": settings.crawler_config.default_settings.get("graph_config", {}).get("verbose", False),
                "headless": settings.crawler_config.default_settings.get("graph_config", {}).get("headless", True),
            }

            prompt = settings.crawler_config.default_settings.get("graph_config", {}).get("prompts", {}).get("general")

            search_graph = SmartScraperMultiGraph(
                prompt=prompt,
                config=graph_config,
                source=[url],
                schema=Urls
            )

            result = search_graph.run()

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
                error=str(e)
            )
            return set(), set()

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
            
            target_urls, seed_urls = await self._analyze_with_scrapegraph(str(frontier_url.url))
            
            new_urls = []

            for url in target_urls:
                if not await self._should_skip_url(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))

            if frontier_url.depth < frontier_url.max_depth - 1:
                for url in seed_urls:
                    if not await self._should_skip_url(url):
                        new_urls.append(self.create_frontier_url(
                            url=url,
                            parent=frontier_url,
                            is_target=False
                        ))

            self.logger.info(
                "Depth 1 processing completed",
                url=str(frontier_url.url),
                targets_found=len([u for u in new_urls if u.is_target]),
                seeds_found=len([u for u in new_urls if not u.is_target])
            )

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
            
            all_urls = await self._get_page_urls()
            file_urls = await self._extract_file_urls()
            all_urls.update(file_urls)
            
            new_urls = []

            for url in all_urls:
                if frontier_url.target_patterns and \
                   self._is_target_url(url, frontier_url.target_patterns):
                    if not await self._should_skip_url(url):
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
        """Execute Type 3 strategy based on current depth."""
        try:
            self.logger.info(
                "Executing Type 3 strategy",
                url=str(frontier_url.url),
                depth=frontier_url.depth
            )

            if not frontier_url.target_patterns:
                self.logger.error("No target patterns specified")
                return []

            if frontier_url.max_depth != 2:
                self.logger.error(
                    "Invalid max_depth for Type 3 URL",
                    max_depth=frontier_url.max_depth
                )
                return []

            if frontier_url.depth == 0:
                new_urls = await self._process_depth_0(frontier_url)
            elif frontier_url.depth == 1:
                new_urls = await self._process_depth_1(frontier_url)
            elif frontier_url.depth == 2:
                new_urls = await self._process_depth_2(frontier_url)
            else:
                self.logger.error("Invalid depth for Type 3 URL")
                return []

            # Update status only if frontier_crud exists
            if self.frontier_crud is not None and frontier_url.id is not None:
                await self.frontier_crud.update_url_status(
                    frontier_url.id,
                    UrlStatus.PROCESSED
                )

            return new_urls

        except Exception as e:
            self.logger.error(
                "Error executing Type 3 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            # Update failed status only if frontier_crud exists
            if self.frontier_crud is not None and frontier_url.id is not None:
                await self.frontier_crud.update_url_status(
                    frontier_url.id,
                    UrlStatus.FAILED,
                    error_message=str(e)
                )
            return []