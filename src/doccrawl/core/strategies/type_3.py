import os
from typing import List, Set, Tuple
import logfire
import nest_asyncio
from scrapegraphai.graphs import SmartScraperMultiGraph
from pydantic import BaseModel
import yaml

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
    - Pattern-based crawling at depth 0
    - AI-assisted crawling at depth 1
    - Target-only collection at depth 2
    - Max depth must be 2
    - Skip already processed seeds
    """
    
    async def _analyze_with_scrapegraph(self, url: str) -> Tuple[Set[str], Set[str]]:
        """
        Analyze page using ScrapegraphAI.
        Returns sets of target and seed URLs.
        """
        try:
            if not self.scrapegraph_api_key:
                self.logger.error("ScrapegraphAI API key not provided")
                return set(), set()

            config_path = "/home/sam/github/doccrawl/config/crawler_config.yaml"
            def load_config(config_path: str) -> dict:
                with open(config_path, 'r') as file:
                    return yaml.safe_load(file)
            config = load_config(config_path)
            config = load_config(config_path)
            graph_config = {
                
                "llm": {
                    "api_key": os.getenv("SCRAPEGRAPH_API_KEY"),
                    "model": "openai/gpt-4o-mini",
                    "temperature": 0,
                },
                "verbose": True,
                "headless": config['crawler']['graph_config']['headless'],
            }
            prompt = config['crawler']['graph_config']['prompts']['general']

            search_graph = SmartScraperMultiGraph(
                prompt=prompt,
                config=graph_config,
                source= url,
                schema=Urls
            )


            # Initialize and run ScrapegraphAI
            search_graph = SmartScraperMultiGraph(
                prompt=prompt,
                config=graph_config,
                source=[url],
                schema=Urls
            )

   
            
            result = search_graph.run()

            logfire.info(f"ScrapegraphAI result: {result}")

            # Convert result to Urls model
            urls_model = Urls(**result)

            seed_urls = [
                url_data.url for url_data in urls_model.urls
                if url_data.url_category == 'seed' and url_data.pagination != 'true'
            ]

            target_urls = [
                url_data.url for url_data in urls_model.urls
                if url_data.url_category == 'target'
            ]

            return set(target_urls), set(seed_urls)

        except Exception as e:
            self.logger.error(
                "Error in ScrapegraphAI analysis",
                url=url,
                error=str(e)
            )
            return set(), set()

    async def _process_depth_0(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Process initial page using regex patterns."""
        try:
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
            
            target_urls = {
                url for url in all_urls 
                if url != str(frontier_url.url) and
                self._is_target_url(url, frontier_url.target_patterns)
            }
            
            seed_urls = {
                url for url in all_urls
                if url != str(frontier_url.url) and
                self._matches_pattern(url, frontier_url.seed_pattern)
            }
            
            return await self._store_urls(target_urls, seed_urls, frontier_url)

        except Exception as e:
            self.logger.error(
                "Error processing depth 0",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []

    async def _process_depth_1(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Process page using ScrapegraphAI."""
        try:
            response = await self.page.goto(str(frontier_url.url))
            if not response or response.status != 200:
                return []

            await self._wait_for_page_ready()
            await self._handle_dynamic_elements()
            
            target_urls, seed_urls = await self._analyze_with_scrapegraph(
                str(frontier_url.url)
            )

            logfire.info(f"ScrapegraphAI target_urls: {target_urls}")
            
            return await self._store_urls(target_urls, seed_urls, frontier_url)

        except Exception as e:
            self.logger.error(
                "Error processing depth 1",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []

    async def _process_depth_2(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Process final depth, collecting only target URLs."""
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
                "Error processing depth 2",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
        
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Execute Type 3 strategy based on current depth."""
        try:
            # Validate configuration
            if not frontier_url.target_patterns:
                self.logger.error("No target patterns specified")
                return []

            if frontier_url.max_depth != 2:
                self.logger.error(
                    "Invalid max_depth for Type 3 URL",
                    max_depth=frontier_url.max_depth
                )
                return []

            # Process based on current depth
            new_urls = []
            if frontier_url.depth == 0:
                new_urls = await self._process_depth_0(frontier_url)
            elif frontier_url.depth == 1:
                new_urls = await self._process_depth_1(frontier_url)
            elif frontier_url.depth == 2:
                new_urls = await self._process_depth_2(frontier_url)
            else:
                self.logger.error("Invalid depth for Type 3 URL")
                return []

            # Update current URL status
            await self._update_url_status(frontier_url, UrlStatus.PROCESSED)

            return new_urls

        except Exception as e:
            self.logger.error(
                "Error executing Type 3 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            await self._update_url_status(
                frontier_url,
                UrlStatus.FAILED,
                error_message=str(e)
            )
            return []