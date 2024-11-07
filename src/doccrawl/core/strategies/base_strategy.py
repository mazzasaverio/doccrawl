from abc import ABC, abstractmethod
from typing import List, Optional, Set, Tuple
import re
from urllib.parse import urljoin, urlparse
import logfire
from playwright.async_api import Page

from ...models.frontier_model import FrontierUrl, UrlType, UrlStatus
from ...crud.frontier_crud import FrontierCRUD
from ...utils.crawler_utils import CrawlerUtils

class CrawlerStrategy(ABC):
    """
    Base class for crawler strategies.
    Provides common functionality for all crawling strategies.
    """
    
    def __init__(
        self,
        frontier_crud: Optional[FrontierCRUD],
        playwright_page: Page,
        scrapegraph_api_key: Optional[str] = None
    ):
        """Initialize strategy with necessary components."""
        self.frontier_crud = frontier_crud
        self.page = playwright_page
        self.scrapegraph_api_key = scrapegraph_api_key
        self.logger = logfire
        self.utils = CrawlerUtils()

    async def _wait_for_page_ready(self):
        """Wait for page to be completely loaded and stable."""
        try:
            # Wait for basic load
            await self.page.wait_for_load_state('domcontentloaded')
            
            # Wait for network idle
            await self.page.wait_for_load_state('networkidle')
            
            # Wait for full page load
            await self.page.wait_for_load_state('load')
            
            # Scroll for lazy content
            await self.page.evaluate("""
                window.scrollTo(0, document.body.scrollHeight);
                window.scrollTo(0, 0);
            """)
            
            # Short pause for JS reactions
            await self.page.wait_for_timeout(1000)

        except Exception as e:
            self.logger.warning(
                "Error waiting for page ready",
                error=str(e)
            )

    async def _handle_dynamic_elements(self):
        """Handle common dynamic page elements like popups, cookies, and load more buttons."""
        try:
            # Handle cookie and privacy banners
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
                        # Wait for banner to disappear
                        await self.page.wait_for_timeout(1000)
                        break
                except:
                    continue

            # Handle load more buttons
            load_more_selectors = [
                'button:has-text("carica")', 
                'button:has-text("load")',
                'button:has-text("più")',
                'button:has-text("more")',
                '[class*="load-more"]',
                'text="carica altri"'
            ]
            
            max_clicks = 5  # Safety limit
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

            # Handle modals
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
                        
                        # Wait for modal to be visible
                        modal = await self.page.wait_for_selector(
                            '.modal.show, [role="dialog"][class*="show"]',
                            timeout=3000
                        )
                        
                        if modal:
                            await self.page.wait_for_timeout(500)  # Wait for animation
                            
                            # Extract links from modal
                            modal_links = await modal.query_selector_all('a[href]')
                            for link in modal_links:
                                href = await link.get_attribute('href')
                                if href:
                                    self.logger.debug(f"Found link in modal: {href}")
                            
                            # Close modal
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

    async def _get_page_urls(self) -> Set[str]:
        """Extract all URLs from current page."""
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
            
            return valid_urls
            
        except Exception as e:
            self.logger.error(
                "Error extracting page URLs",
                page_url=self.page.url,
                error=str(e)
            )
            return set()

    async def _extract_file_urls(self) -> Set[str]:
        """Extract URLs that point to files (pdf, doc, etc)."""
        try:
            file_urls = set()
            
            # Look for direct file links
            file_extensions = r'\.(pdf|doc|docx|xls|xlsx|txt|csv|zip|rar)$'
            links = await self.page.query_selector_all('a[href*=".pdf"], a[href*=".doc"], a[href*=".xls"]')
            
            for link in links:
                href = await link.get_attribute('href')
                if href and re.search(file_extensions, href, re.IGNORECASE):
                    normalized = self._normalize_url(href, self.page.url)
                    if normalized:
                        file_urls.add(normalized)

            # Check onclick and other attributes
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

    async def _store_urls(
        self, 
        target_urls: Set[str],
        seed_urls: Set[str],
        parent: FrontierUrl
    ) -> List[FrontierUrl]:
        """Store discovered URLs in frontier."""
        new_urls = []
        
        # Process target URLs first
        for url in target_urls:
            try:
                # Skip if URL already exists and frontier_crud is available
                if self.frontier_crud is not None:
                    if await self.frontier_crud.exists_in_frontier(url):
                        continue

                frontier_url = self.create_frontier_url(
                    url=url,
                    parent=parent,
                    is_target=True
                )

                # Store in database if frontier_crud is available
                if self.frontier_crud is not None:
                    url_id = await self.frontier_crud.create_url(frontier_url)
                    frontier_url.id = url_id
                    
                new_urls.append(frontier_url)
                
                self.logger.info(
                    "Stored target URL",
                    url=url,
                    parent_url=str(parent.url),
                    depth=parent.depth + 1
                )

            except Exception as e:
                self.logger.error(
                    "Error storing target URL",
                    url=url,
                    error=str(e)
                )

        # Process seed URLs if not at max depth
        if parent.depth < parent.max_depth - 1:
            for url in seed_urls:
                try:
                    # Skip if seed URL was already processed and frontier_crud is available
                    if self.frontier_crud is not None:
                        existing_url = await self.frontier_crud.get_url_by_url(url)
                        if existing_url is not None and \
                           not existing_url.is_target and \
                           existing_url.status == UrlStatus.PROCESSED:
                            self.logger.info(
                                "Skipping already processed seed URL",
                                url=url
                            )
                            continue
                        
                        if await self.frontier_crud.exists_in_frontier(url):
                            continue

                    frontier_url = self.create_frontier_url(
                        url=url,
                        parent=parent,
                        is_target=False
                    )

                    # Store in database if frontier_crud is available
                    if self.frontier_crud is not None:
                        url_id = await self.frontier_crud.create_url(frontier_url)
                        frontier_url.id = url_id
                        
                    new_urls.append(frontier_url)
                    
                    self.logger.info(
                        "Stored seed URL",
                        url=url,
                        parent_url=str(parent.url),
                        depth=parent.depth + 1
                    )

                except Exception as e:
                    self.logger.error(
                        "Error storing seed URL",
                        url=url,
                        error=str(e)
                    )

        return new_urls

    async def _update_url_status(
        self,
        frontier_url: FrontierUrl,
        status: UrlStatus,
        error_message: Optional[str] = None
    ) -> None:
        """Update URL status in frontier."""
        if self.frontier_crud is not None and frontier_url.id is not None:
            await self.frontier_crud.update_url_status(
                frontier_url.id,
                status,
                error_message=error_message
            )

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format and scheme."""
        try:
            result = urlparse(url)
            return all([
                result.scheme, 
                result.netloc,
                result.scheme in ['http', 'https'],
                not result.netloc.startswith('.')
            ])
        except Exception:
            return False
            
    def _matches_pattern(self, url: str, pattern: str) -> bool:
        """Check if URL matches a regex pattern."""
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
        """Check if URL matches any target patterns."""
        return any(self._matches_pattern(url, pattern) for pattern in patterns)
        
    def _normalize_url(self, url: str, base_url: str) -> Optional[str]:
        """Normalize relative URL to absolute URL."""
        try:
            url = url.strip()
            if not url or url.startswith(('javascript:', 'mailto:', 'tel:')):
                return None
                
            absolute_url = urljoin(base_url, url)
            parsed = urlparse(absolute_url)
            
            if not all([parsed.scheme, parsed.netloc]):
                return None
                
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
        """Create a new FrontierUrl instance based on parent URL."""
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

    @abstractmethod
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """Execute the crawling strategy for a given URL."""
        pass