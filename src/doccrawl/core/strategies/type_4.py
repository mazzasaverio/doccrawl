from typing import List, Set, Tuple
import logfire
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


class Type4Strategy(CrawlerStrategy):
    """
    Strategy for Type 4 URLs (multi-level crawling with full AI assistance).
    
    Features:
    - AI-assisted URL discovery at all depths except final
    - Target-only collection at final depth
    - Configurable max_depth (≥ 2)
    - Skip already processed seeds
    - URL deduplication with visited set
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_urls = set()

    async def _analyze_with_scrapegraph(self, url: str) -> Tuple[Set[str], Set[str]]:
        """
        Analyze page using ScrapegraphAI.
        Returns sets of target and seed URLs.
        """
        try:
            if not self.scrapegraph_api_key:
                self.logger.error("ScrapegraphAI API key not provided")
                return set(), set()

            # Get configuration from settings
            graph_config = {
                "llm": {
                    "api_key": self.scrapegraph_api_key,
                    "model": settings.crawler_config.default_settings.get(
                        "graph_config", {}).get("model", "openai/gpt-4o-mini"),
                    "temperature": 0,
                },
                "verbose": False,
                "headless": True,
            }

            prompt = settings.crawler_config.default_settings.get(
                "graph_config", {}).get("prompts", {}).get("general")

            # Initialize and run ScrapegraphAI
            search_graph = SmartScraperMultiGraph(
                prompt=prompt,
                config=graph_config,
                source=[url],
                schema=Urls
            )

            result = search_graph.run()
            
            # Process and validate results
            target_urls = set()
            seed_urls = set()
            
            if result and 'urls' in result:
                for url_data in result['urls']:
                    if url_data.get('pagination', 'false').lower() == 'true':
                        continue
                        
                    url = url_data.get('url')
                    if not url or not self._is_valid_url(url):
                        continue

                    normalized_url = self._normalize_url(url, self.page.url)
                    if not normalized_url:
                        continue

                    if url_data.get('url_category') == 'target' and \
                       normalized_url.lower().endswith('.pdf'):
                        target_urls.add(normalized_url)
                    elif url_data.get('url_category') == 'seed':
                        seed_urls.add(normalized_url)

            return target_urls, seed_urls

        except Exception as e:
            self.logger.error(
                "Error in ScrapegraphAI analysis",
                url=url,
                error=str(e)
            )
            return set(), set()

    async def _process_with_ai(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Process a page using AI assistance for URL discovery."""
        try:
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return []

            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            target_urls, seed_urls = await self._analyze_with_scrapegraph(
                str(frontier_url.url)
            )

            # Filter out already visited seed URLs
            seed_urls = {url for url in seed_urls if url not in self.visited_urls}
            self.visited_urls.update(seed_urls)
            
            return await self._store_urls(target_urls, seed_urls, frontier_url)

        except Exception as e:
            self.logger.error(
                "Error in AI processing",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []

    async def _process_final_depth(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Process final depth page, collecting only target URLs."""
        try:
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return []

            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            all_urls = await self._get_page_urls()
            file_urls = await self._extract_file_urls()
            all_urls.update(file_urls)
            
            target_urls = {
                url for url in all_urls
                if url != str(frontier_url.url) and
                frontier_url.target_patterns and
                self._is_target_url(url, frontier_url.target_patterns)
            }
            
            return await self._store_urls(target_urls, set(), frontier_url)

        except Exception as e:
            self.logger.error(
                "Error processing final depth",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Execute Type 4 strategy based on current depth."""
        try:
            # Validate configuration
            if frontier_url.max_depth < 2:
                self.logger.error(
                    "Invalid max_depth for Type 4 URL",
                    max_depth=frontier_url.max_depth
                )
                return []

            if not frontier_url.target_patterns:
                self.logger.error(
                    "No target patterns specified",
                    url=str(frontier_url.url)
                )
                return []

            # Process based on current depth
            if frontier_url.depth < frontier_url.max_depth - 1:
                new_urls = await self._process_with_ai(frontier_url)
            else:
                new_urls = await self._process_final_depth(frontier_url)

            # Update current URL status
            await self._update_url_status(frontier_url, UrlStatus.PROCESSED)

            return new_urls

        except Exception as e:
            self.logger.error(
                "Error executing Type 4 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            await self._update_url_status(
                frontier_url,
                UrlStatus.FAILED,
                error_message=str(e)
            )
            return []