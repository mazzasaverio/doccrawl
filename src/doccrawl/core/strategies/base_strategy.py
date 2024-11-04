#src/core/strategies/base_strategy.py
from abc import ABC, abstractmethod
from typing import List, Optional, Set, Tuple
import re
from urllib.parse import urljoin, urlparse
import logfire
from playwright.async_api import Page

from doccrawl.utils.crawler_utils import CrawlerUtils

from ...models.frontier_model import FrontierUrl, UrlType
from ...crud.frontier_crud import FrontierCRUD
from typing import List, Set, Tuple
from scrapegraphai.graphs import SmartScraperMultiGraph
from pydantic import BaseModel
import os

class Url(BaseModel):
    url: str
    url_description: str
    extension: str
    pagination: str
    url_category: str

class Urls(BaseModel):
    urls: List[Url]

class CrawlerStrategy(ABC):
    """Base class for crawler strategies."""
    
    def __init__(
        self,
        frontier_crud: Optional[FrontierCRUD],
        playwright_page: Page,
        scrapegraph_api_key: Optional[str] = None
    ):
        self.frontier_crud = frontier_crud
        self.page = playwright_page
        self.scrapegraph_api_key = scrapegraph_api_key
        self.logger = logfire
        self.utils = CrawlerUtils()
    
    @abstractmethod
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute the crawling strategy for a given URL.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            List of new FrontierUrl instances discovered
        
        Raises:
            NotImplementedError: If the strategy is not implemented
        """
        pass

    async def _handle_dynamic_elements(self):
        """Handle common dynamic page elements like popups, cookies, and load more buttons."""
        try:
            # Gestione cookie e privacy banners
            cookie_selectors = [
                '[id*="cookie"]', 
                '[id*="privacy"]',
                '[id*="gdpr"]',
                'button:has-text("Accetta")',
                'button:has-text("Accept")',
                'button[onclick*="cookiesPolicy"]'
            ]
            for selector in cookie_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=2000)
                    if button:
                        await button.click()
                        self.logger.debug(f"Clicked cookie/privacy button: {selector}")
                        # Attendi che il banner scompaia
                        await self.page.wait_for_timeout(1000)
                        break
                except:
                    continue

            # Gestione pulsanti di caricamento
            load_more_selectors = [
                'button:has-text("carica")', 
                'button:has-text("load")',
                'button:has-text("più")',
                'button:has-text("more")',
                '[class*="load-more"]',
                'text="carica altri"'
            ]
            
            max_clicks = 5  # Limite di sicurezza
            clicks = 0
            while clicks < max_clicks:
                clicked = False
                for selector in load_more_selectors:
                    try:
                        button = await self.page.wait_for_selector(selector, timeout=2000)
                        if button and await button.is_visible():
                            await button.scroll_into_view_if_needed()
                            await button.click()
                            await self.page.wait_for_load_state('networkidle', timeout=5000)
                            clicked = True
                            clicks += 1
                            self.logger.debug(f"Clicked load more button: {selector}")
                            break
                    except:
                        continue
                if not clicked:
                    break

            # Gestione modali
            await self._handle_modals()

        except Exception as e:
            self.logger.warning(
                "Error handling dynamic elements",
                error=str(e)
            )

    async def _handle_modals(self):
        """Handle modal popups that might contain relevant links."""
        try:
            modal_button_selectors = [
                'button[data-bs-toggle="modal"]',
                '[data-toggle="modal"]',
                '[class*="modal-trigger"]',
                'button[onclick*="modal"]'
            ]

            for selector in modal_button_selectors:
                buttons = await self.page.query_selector_all(selector)
                for button in buttons:
                    try:
                        await button.scroll_into_view_if_needed()
                        await button.click()
                        
                        # Attendi che il modal sia visibile
                        modal = await self.page.wait_for_selector(
                            '.modal.show, [role="dialog"][class*="show"]',
                            timeout=3000
                        )
                        
                        if modal:
                            await self.page.wait_for_timeout(500)  # Attendi animazione
                            
                            # Estrai eventuali link dal modal
                            modal_links = await modal.query_selector_all('a[href]')
                            for link in modal_links:
                                href = await link.get_attribute('href')
                                if href:
                                    self.logger.debug(f"Found link in modal: {href}")
                            
                            # Chiudi il modal
                            close_button = await self.page.query_selector(
                                '.modal.show button[data-bs-dismiss="modal"], [role="dialog"][class*="show"] button[aria-label="Close"]'
                            )
                            if close_button:
                                await close_button.click()
                                await self.page.wait_for_selector(
                                    '.modal.show',
                                    state='hidden',
                                    timeout=3000
                                )
                    except Exception as e:
                        self.logger.debug(f"Error handling modal: {str(e)}")
                        continue

        except Exception as e:
            self.logger.warning(
                "Error handling modals",
                error=str(e)
            )
    
    async def _validate_url_accessibility(self, url: str) -> bool:
        """
        Validate if a URL is accessible.
        
        Args:
            url: URL to validate
        
        Returns:
            bool: True if URL is accessible, False otherwise
        """
        try:
            response = await self.page.goto(
                url,
                wait_until='domcontentloaded',
                timeout=15000
            )
            return response and response.status == 200
        except Exception as e:
            self.logger.error(
                "Error validating URL accessibility",
                url=url,
                error=str(e)
            )
            return False

    async def _get_page_urls(self) -> Set[str]:
        """
        Extract all URLs from current page.
        
        Returns:
            Set[str]: Set of normalized valid URLs from the page
        """
        try:
            # Get all anchor tags with href attributes
            links = await self.page.evaluate("""
                () => {
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    return anchors.map(a => {
                        return {
                            href: a.href,
                            text: a.textContent.trim(),
                            rel: a.getAttribute('rel'),
                            onclick: a.getAttribute('onclick')
                        };
                    });
                }
            """)
            
            # Filter and normalize URLs
            valid_urls = set()
            base_url = self.page.url
            
            for link in links:
                # Process href attribute
                url = self._normalize_url(link['href'], base_url)
                if url and self._is_valid_url(url):
                    valid_urls.add(url)
                
                # Check onclick handlers for URLs
                if link['onclick']:
                    onclick_urls = re.findall(r"window\.location(?:\.href)?\s*=\s*['\"](https?://[^'\"]+)", link['onclick'])
                    for onclick_url in onclick_urls:
                        if self._is_valid_url(onclick_url):
                            valid_urls.add(onclick_url)
            
            # Add file URLs
            file_urls = await self._extract_file_urls()
            valid_urls.update(file_urls)
            
            return valid_urls
            
        except Exception as e:
            self.logger.error(
                "Error extracting page URLs",
                page_url=self.page.url,
                error=str(e)
            )
            return set()

    async def _extract_file_urls(self) -> Set[str]:
        """
        Extract URLs that point to files (pdf, doc, etc) using various techniques.
        
        Returns:
            Set[str]: Set of file URLs found
        """
        try:
            file_urls = set()
            
            # Cerca link diretti a file
            file_extensions = r'\.(pdf|doc|docx|xls|xlsx|txt|csv|zip|rar)$'
            links = await self.page.query_selector_all('a[href*=".pdf"], a[href*=".doc"], a[href*=".xls"]')
            
            for link in links:
                href = await link.get_attribute('href')
                if href and re.search(file_extensions, href, re.IGNORECASE):
                    normalized = self._normalize_url(href, self.page.url)
                    if normalized:
                        file_urls.add(normalized)

            # Cerca anche in onclick e altri attributi
            onclick_elements = await self.page.query_selector_all('[onclick*="download"], [onclick*="file"]')
            for element in onclick_elements:
                onclick = await element.get_attribute('onclick')
                if onclick:
                    matches = re.findall(r'https?://[^\s\'"]+(?:\.pdf|\.doc|\.xls)[^\s\'"]*', onclick)
                    file_urls.update(matches)

            return file_urls

        except Exception as e:
            self.logger.error(
                "Error extracting file URLs",
                page_url=self.page.url,
                error=str(e)
            )
            return set()
    async def _analyze_with_scrapegraph(self) -> Tuple[Set[str], Set[str]]:
        """
        Analyze current page with ScrapegraphAI to identify target and seed URLs.
        Uses configuration from crawler_config.yaml for graph settings and prompts.
        
        Returns:
            Tuple[Set[str], Set[str]]: Sets of (target_urls, seed_urls)
        """
        try:
            if not self.scrapegraph_api_key:
                self.logger.error("ScrapegraphAI API key not provided")
                return set(), set()

            # Get current page content and URL
            content = await self.page.content()
            current_url = self.page.url

            # Extract metadata for better context
            metadata = await self.page.evaluate("""
                () => ({
                    title: document.title,
                    metaDescription: document.querySelector('meta[name="description"]')?.content,
                    h1: Array.from(document.getElementsByTagName('h1')).map(h => h.textContent),
                })
            """)

            # Prepare graph config
            graph_config = {
                "llm": {
                    "api_key": self.scrapegraph_api_key,
                    "model": "gpt-4o-mini",  # From config['graph_config']['model']
                    "temperature": 0,
                },
                "verbose": False,  # From config['graph_config']['verbose']
                "headless": True,  # From config['graph_config']['headless']
            }

            # Use general prompt from config
            prompt = """
            Find all URLs that are the main bando of scholarships, research grants, 
            graduation awards, or similar, or URLs that might contain them. 
            Label PDF links (with pdf extension) of scholarships, research grants, 
            graduation awards, or similar academic opportunities as "target". 
            Label URLs that may contain such PDFs but are not PDF links as "seed". 
            Search only in links that could potentially have documents related to 2024, 
            2025, or 2026.
            """

            # Initialize ScrapegraphAI with schema
            search_graph = SmartScraperMultiGraph(
                prompt=prompt,
                config=graph_config,
                source=[current_url],
                schema=Urls
            )

            # Run analysis
            result = search_graph.run()

            # Process results
            target_urls = set()
            seed_urls = set()

            if result and 'urls' in result:
                for url_data in result['urls']:
                    if not url_data.get('pagination', 'false').lower() == 'true':
                        url = url_data.get('url')
                        if url:
                            # Normalize URL
                            normalized_url = self._normalize_url(url, current_url)
                            if normalized_url:
                                # Check if it's a target (PDF) or seed URL
                                if url_data.get('url_category') == 'target' or \
                                (normalized_url.lower().endswith('.pdf') and 
                                    self._is_target_url(normalized_url, [])):  # Empty patterns list as we rely on AI
                                    target_urls.add(normalized_url)
                                elif url_data.get('url_category') == 'seed':
                                    seed_urls.add(normalized_url)

            self.logger.info(
                "ScrapegraphAI analysis completed",
                targets_found=len(target_urls),
                seeds_found=len(seed_urls)
            )

            return target_urls, seed_urls

        except Exception as e:
            self.logger.error(
                "Error in ScrapegraphAI analysis",
                error=str(e),
                url=self.page.url
            )
            return set(), set()
    
    async def _get_page_metadata(self) -> dict:
        """
        Extract useful metadata from the current page.
        
        Returns:
            dict: Dictionary containing page metadata
        """
        try:
            metadata = await self.page.evaluate("""
                () => ({
                    title: document.title,
                    description: document.querySelector('meta[name="description"]')?.content,
                    keywords: document.querySelector('meta[name="keywords"]')?.content,
                    canonical: document.querySelector('link[rel="canonical"]')?.href,
                    h1: Array.from(document.getElementsByTagName('h1')).map(h => h.textContent.trim()),
                    lastModified: document.lastModified
                })
            """)
            return metadata
        except Exception as e:
            self.logger.error(
                "Error extracting page metadata",
                page_url=self.page.url,
                error=str(e)
            )
            return {}

    async def _wait_for_page_ready(self):
        """Wait for page to be completely loaded and stable."""
        try:
            # Attendi caricamento base
            await self.page.wait_for_load_state('domcontentloaded')
            
            # Attendi network idle
            await self.page.wait_for_load_state('networkidle')
            
            # Attendi caricamento immagini e altri contenuti
            await self.page.wait_for_load_state('load')
            
            # Scrolling per caricare contenuto lazy
            await self.page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight);
                window.scrollTo(0, 0);
            """)
            
            # Breve pausa per eventuali reazioni JS
            await self.page.wait_for_timeout(1000)

        except Exception as e:
            self.logger.warning(
                "Error waiting for page ready",
                error=str(e)
            )
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format and scheme.
        
        Args:
            url: URL to validate
            
        Returns:
            bool: True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([
                result.scheme, 
                result.netloc,
                result.scheme in ['http', 'https'],
                not result.netloc.startswith('.')  # Avoid relative domains
            ])
        except Exception:
            return False
            
    def _matches_pattern(self, url: str, pattern: str) -> bool:
        """
        Check if URL matches a regex pattern.
        
        Args:
            url: URL to check
            pattern: Regex pattern to match against
            
        Returns:
            bool: True if URL matches pattern, False otherwise
        """
        try:
            return bool(re.search(pattern, url, re.IGNORECASE))
        except re.error as e:
            self.logger.error(
                "Invalid regex pattern",
                pattern=pattern,
                error=str(e)
            )
            return False
            
    def _is_target_url(self, url: str, patterns: List[str]) -> bool:
        """
        Check if URL matches any target patterns.
        
        Args:
            url: URL to check
            patterns: List of regex patterns to match against
            
        Returns:
            bool: True if URL matches any pattern, False otherwise
        """
        return any(self._matches_pattern(url, pattern) for pattern in patterns)
        
    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """
        Normalize relative URL to absolute URL.
        
        Args:
            url: URL to normalize
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Optional[str]: Normalized URL if valid, None otherwise
        """
        try:
            # Clean the URL first
            url = url.strip()
            
            # Skip invalid or empty URLs
            if not url or url.startswith(('javascript:', 'mailto:', 'tel:')):
                return None
                
            absolute_url = urljoin(base_url, url)
            parsed = urlparse(absolute_url)
            
            # Additional validation
            if not all([parsed.scheme, parsed.netloc]):
                return None
                
            # Normalize the URL
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized += f"?{parsed.query}"
                
            return normalized
            
        except Exception as e:
            self.logger.error(
                "Error normalizing URL",
                url=url,
                base_url=base_url,
                error=str(e)
            )
            return None
       
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
            FrontierUrl: New FrontierUrl instance
        """
        try:
            return FrontierUrl(
                url=url,
                category=parent.category,
                url_type=parent.url_type,
                depth=parent.depth + 1,
                max_depth=parent.max_depth,
                target_patterns=parent.target_patterns,
                seed_pattern=parent.seed_pattern,
                is_target=is_target,
                parent_url=str(parent.url),
                main_domain=urlparse(url).netloc
            )
        except Exception as e:
            self.logger.error(
                "Error creating frontier URL",
                url=url,
                parent_url=str(parent.url),
                error=str(e)
            )
            raise