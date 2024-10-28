# src/core/strategies/type_4.py
from typing import List, Set, Tuple, Optional
import asyncio
from urllib.parse import urljoin
import logfire
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl, UrlStatus
from ...utils.crawler_utils import CrawlerUtils

class Type4Strategy(CrawlerStrategy):
    """
    Strategy for Type 4 URLs (multi-level crawling with full AI assistance).
    
    This strategy uses ScrapegraphAI for intelligent URL discovery at all depths
    except the final one, where it only collects target URLs. The strategy is 
    particularly useful for complex websites where simple pattern matching isn't 
    sufficient to identify relevant URLs.
    
    Features:
    - Full AI assistance for URL discovery
    - Intelligent content analysis
    - Adaptive crawling depth
    - Robust error handling
    - Rate limiting and politeness controls
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_urls = set()
        self.rate_limiter = asyncio.Semaphore(2)  # Limit concurrent requests
        self.last_request_time = {}  # Domain -> timestamp mapping
    
    async def _wait_for_rate_limit(self, domain: str) -> None:
        """
        Implements rate limiting per domain.
        
        Args:
            domain: Domain being accessed
        """
        try:
            async with self.rate_limiter:
                # Ensure minimum delay between requests to same domain
                if domain in self.last_request_time:
                    elapsed = time.time() - self.last_request_time[domain]
                    if elapsed < 2.0:  # 2 second minimum delay
                        await asyncio.sleep(2.0 - elapsed)
                self.last_request_time[domain] = time.time()
                
        except Exception as e:
            self.logger.warning(
                "Rate limiting error",
                domain=domain,
                error=str(e)
            )
    
    async def _analyze_page_content(self, content: str) -> dict:
        """
        Analyzes page content using ScrapegraphAI for enhanced URL discovery.
        
        Args:
            content: HTML content of the page
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Extract metadata and structural information
            metadata = await self.page.evaluate("""
                () => ({
                    title: document.title,
                    metaDescription: document.querySelector('meta[name="description"]')?.content,
                    h1: Array.from(document.getElementsByTagName('h1')).map(h => h.textContent),
                    mainContent: document.querySelector('main')?.textContent,
                })
            """)
            
            # Analyze with ScrapegraphAI
            analysis = await CrawlerUtils.analyze_with_scrapegraph(
                self.page,
                self.scrapegraph_api_key,
                {
                    'task': 'comprehensive_analysis',
                    'content': content,
                    'metadata': metadata,
                    'url': self.page.url
                }
            )
            
            return analysis
            
        except Exception as e:
            self.logger.error(
                "Error analyzing page content",
                url=self.page.url,
                error=str(e)
            )
            return {}
    
    async def _extract_relevant_urls(self, analysis: dict) -> Tuple[Set[str], Set[str]]:
        """
        Extracts relevant URLs from AI analysis results.
        
        Args:
            analysis: Analysis results from ScrapegraphAI
            
        Returns:
            Tuple of (target_urls, seed_urls)
        """
        try:
            target_urls = set()
            seed_urls = set()
            
            # Process AI-identified URLs
            if 'identified_urls' in analysis:
                for url_data in analysis['identified_urls']:
                    url = url_data['url']
                    confidence = url_data.get('confidence', 0)
                    url_type = url_data.get('type', '')
                    
                    # High-confidence targets
                    if confidence > 0.8 and url_type == 'target':
                        target_urls.add(url)
                    # Potential seeds for further exploration
                    elif confidence > 0.6 and url_type == 'seed':
                        seed_urls.add(url)
            
            return target_urls, seed_urls
            
        except Exception as e:
            self.logger.error(
                "Error extracting relevant URLs",
                error=str(e)
            )
            return set(), set()
    
    async def _process_with_ai(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Processes a page using AI assistance for URL discovery.
        
        Args:
            frontier_url: Current FrontierUrl being processed
            
        Returns:
            List of new FrontierUrl instances
        """
        domain = CrawlerUtils.extract_domain(str(frontier_url.url))
        await self._wait_for_rate_limit(domain)
        
        try:
            # Navigate to page
            response = await self.page.goto(
                str(frontier_url.url),
                wait_until='networkidle',
                timeout=30000
            )
            
            if not await CrawlerUtils.is_valid_response(response):
                return []
            
            # Wait for dynamic content
            await CrawlerUtils.wait_for_page_load(self.page)
            
            # Get page content
            content = await self.page.content()
            
            # Analyze page content
            analysis = await self._analyze_page_content(content)
            
            # Extract relevant URLs
            target_urls, seed_urls = await self._extract_relevant_urls(analysis)
            
            # Validate and normalize URLs
            base_url = str(frontier_url.url)
            normalized_targets = {
                CrawlerUtils.clean_url(urljoin(base_url, url))
                for url in target_urls
                if CrawlerUtils.is_valid_url(url)
            }
            
            normalized_seeds = {
                CrawlerUtils.clean_url(urljoin(base_url, url))
                for url in seed_urls
                if CrawlerUtils.is_valid_url(url)
            }
            
            # Create new frontier URLs
            new_urls = []
            
            # Add target URLs
            for url in normalized_targets:
                if not self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))
            
            # Add seed URLs if not at max depth - 1
            if frontier_url.depth < frontier_url.max_depth - 1:
                for url in normalized_seeds:
                    if (not self.frontier_crud.exists_in_frontier(url) and 
                        url not in self.visited_urls):
                        new_urls.append(self.create_frontier_url(
                            url=url,
                            parent=frontier_url
                        ))
                        self.visited_urls.add(url)
            
            return new_urls
            
        except PlaywrightTimeout:
            self.logger.warning(
                "Page load timeout",
                url=str(frontier_url.url)
            )
            return []
            
        except Exception as e:
            self.logger.error(
                "Error in AI processing",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
    
    async def _process_final_depth(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Processes final depth page, collecting only target URLs.
        
        Args:
            frontier_url: Current FrontierUrl being processed
            
        Returns:
            List of new target FrontierUrl instances
        """
        domain = CrawlerUtils.extract_domain(str(frontier_url.url))
        await self._wait_for_rate_limit(domain)
        
        try:
            # Navigate to page
            response = await self.page.goto(
                str(frontier_url.url),
                wait_until='networkidle',
                timeout=30000
            )
            
            if not await CrawlerUtils.is_valid_response(response):
                return []
            
            await CrawlerUtils.wait_for_page_load(self.page)
            
            # Extract all links
            all_urls = await CrawlerUtils.extract_links_from_page(
                self.page,
                str(frontier_url.url)
            )
            
            # Filter and normalize target URLs
            target_urls = {
                CrawlerUtils.clean_url(url) for url in all_urls
                if (CrawlerUtils.matches_patterns(url, frontier_url.target_patterns) and
                    CrawlerUtils.is_valid_url(url))
            }
            
            # Create frontier URLs for targets
            new_urls = []
            for url in target_urls:
                if not self.frontier_crud.exists_in_frontier(url):
                    new_urls.append(self.create_frontier_url(
                        url=url,
                        parent=frontier_url,
                        is_target=True
                    ))
            
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error processing final depth",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
    
    async def _validate_url_accessibility(self, url: str) -> bool:
        """
        Validates if a URL is accessible.
        
        Args:
            url: URL to validate
            
        Returns:
            Boolean indicating if URL is accessible
        """
        try:
            response = await self.page.goto(
                url,
                wait_until='domcontentloaded',
                timeout=15000
            )
            return response.status == 200
            
        except Exception:
            return False
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Executes Type 4 strategy based on current depth.
        
        This method implements the main logic for Type 4 URLs, using AI assistance
        for all depths except the final one. It includes:
        - Comprehensive URL discovery using AI
        - Intelligent content analysis
        - Rate limiting and politeness
        - Error handling and logging
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List of discovered URLs
        """
        try:
            self.logger.info(
                "Processing Type 4 URL",
                url=str(frontier_url.url),
                depth=frontier_url.depth,
                max_depth=frontier_url.max_depth
            )
            
            # Validate URL before processing
            if not await self._validate_url_accessibility(str(frontier_url.url)):
                self.logger.warning(
                    "URL not accessible",
                    url=str(frontier_url.url)
                )
                return []
            
            # Process based on depth
            if frontier_url.depth < frontier_url.max_depth - 1:
                new_urls = await self._process_with_ai(frontier_url)
                self.logger.info(
                    "AI processing completed",
                    url=str(frontier_url.url),
                    new_urls_found=len(new_urls)
                )
                
            elif frontier_url.depth == frontier_url.max_depth - 1:
                new_urls = await self._process_final_depth(frontier_url)
                self.logger.info(
                    "Final depth processing completed",
                    url=str(frontier_url.url),
                    targets_found=len(new_urls)
                )
                
            else:
                self.logger.error(
                    "Invalid depth for Type 4 URL",
                    url=str(frontier_url.url),
                    depth=frontier_url.depth
                )
                return []
            
            # Update frontier URL status
            await self.frontier_crud.update_url_status(
                frontier_url.id,
                UrlStatus.PROCESSED
            )
            
            return new_urls
            
        except Exception as e:
            self.logger.error(
                "Error executing Type 4 strategy",
                url=str(frontier_url.url),
                error=str(e)
            )
            # Update frontier URL status to failed
            await self.frontier_crud.update_url_status(
                frontier_url.id,
                UrlStatus.FAILED,
                error_message=str(e)
            )
            return []