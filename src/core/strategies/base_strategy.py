# src/core/strategies/base_strategy.py
from abc import ABC, abstractmethod
from typing import List, Optional, Set
import re
from urllib.parse import urljoin, urlparse
import logfire
from playwright.sync_api import Page

from ...models.frontier_model import FrontierUrl, UrlType
from ...crud.frontier_crud import FrontierCRUD

class CrawlerStrategy(ABC):
    """Base class for crawler strategies."""
    
    def __init__(
        self,
        frontier_crud: FrontierCRUD,
        playwright_page: Page,
        scrapegraph_api_key: Optional[str] = None
    ):
        self.frontier_crud = frontier_crud
        self.page = playwright_page
        self.scrapegraph_api_key = scrapegraph_api_key
        self.logger = logfire
        
    @abstractmethod
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute the crawling strategy for a given URL.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List of new FrontierUrl instances discovered
        """
        pass
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format and scheme."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception:
            return False
            
    def _matches_pattern(self, url: str, pattern: str) -> bool:
        """Check if URL matches a regex pattern."""
        try:
            return bool(re.match(pattern, url))
        except re.error as e:
            self.logger.error(
                "Invalid regex pattern",
                pattern=pattern,
                error=str(e)
            )
            return False
            
    def _is_target_url(self, url: str, patterns: List[str]) -> bool:
        """Check if URL matches any target patterns."""
        return any(self._matches_pattern(url, pattern) for pattern in patterns)
        
    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalize relative URL to absolute URL."""
        try:
            absolute_url = urljoin(base_url, url)
            parsed = urlparse(absolute_url)
            return absolute_url if parsed.scheme and parsed.netloc else None
        except Exception as e:
            self.logger.error(
                "Error normalizing URL",
                url=url,
                base_url=base_url,
                error=str(e)
            )
            return None
            
    async def _get_page_urls(self) -> Set[str]:
        """Extract all URLs from current page."""
        try:
            # Get href attributes from all <a> tags
            urls = await self.page.evaluate("""
                () => {
                    const links = document.getElementsByTagName('a');
                    return Array.from(links).map(a => a.href);
                }
            """)
            
            # Filter and normalize URLs
            valid_urls = set()
            base_url = self.page.url
            
            for url in urls:
                normalized_url = self._normalize_url(url, base_url)
                if normalized_url and self._is_valid_url(normalized_url):
                    valid_urls.add(normalized_url)
                    
            return valid_urls
            
        except Exception as e:
            self.logger.error(
                "Error extracting page URLs",
                page_url=self.page.url,
                error=str(e)
            )
            return set()
            
    async def _analyze_with_scrapegraph(self) -> tuple[Set[str], Set[str]]:
        """
        Analyze current page with ScrapegraphAI to identify target and seed URLs.
        
        Returns:
            Tuple of (target_urls, seed_urls)
        """
        if not self.scrapegraph_api_key:
            self.logger.warning("ScrapegraphAI API key not provided")
            return set(), set()
            
        try:
            # Implementation of ScrapegraphAI analysis would go here
            # This is a placeholder that would need to be implemented
            # based on the actual ScrapegraphAI API
            pass
            
        except Exception as e:
            self.logger.error(
                "Error analyzing page with ScrapegraphAI",
                page_url=self.page.url,
                error=str(e)
            )
            return set(), set()
            
    def create_frontier_url(
        self,
        url: str,
        parent: FrontierUrl,
        is_target: bool = False
    ) -> FrontierUrl:
        """
        Create a new FrontierUrl instance based on parent URL.
        
        Args:
            url: URL string
            parent: Parent FrontierUrl instance
            is_target: Whether URL is a target document
            
        Returns:
            New FrontierUrl instance
        """
        return FrontierUrl(
            url=url,
            category=parent.category,
            url_type=parent.url_type,
            depth=parent.depth + 1,
            max_depth=parent.max_depth,
            target_patterns=parent.target_patterns,
            seed_pattern=parent.seed_pattern,
            is_target=is_target,
            parent_url=str(parent.url)
        )