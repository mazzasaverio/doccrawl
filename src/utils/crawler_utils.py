# src/utils/crawler_utils.py
from typing import Set, Dict, Any, Optional, Tuple
import re
from urllib.parse import urlparse, urljoin, urlunparse
import logfire
from playwright.sync_api import Page, Response
import asyncio
from functools import lru_cache
import hashlib
import json

class CrawlerUtils:
    """Utility functions for crawler operations."""
    
    def __init__(self):
        self.logger = logfire

    @staticmethod
    def clean_url(url: str) -> str:
        """
        Clean and normalize URL.
        
        - Removes fragments
        - Removes default ports
        - Sorts query parameters
        - Ensures trailing slash consistency
        
        Args:
            url: URL to clean
            
        Returns:
            Cleaned URL string
        """
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Remove default ports
            netloc = re.sub(r':80$', '', parsed.netloc)
            netloc = re.sub(r':443$', '', netloc)
            
            # Sort query parameters
            query = '&'.join(sorted(parsed.query.split('&'))) if parsed.query else ''
            
            # Rebuild URL without fragment
            clean = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                query,
                ''  # No fragment
            ))
            
            # Ensure consistency with trailing slash
            if not clean.endswith('/') and '.' not in parsed.path.split('/')[-1]:
                clean += '/'
                
            return clean
            
        except Exception as e:
            logfire.error(
                "Error cleaning URL",
                url=url,
                error=str(e)
            )
            return url

    @staticmethod
    @lru_cache(maxsize=1000)
    def get_url_signature(url: str, content: Optional[str] = None) -> str:
        """
        Generate a unique signature for a URL and optionally its content.
        Used for deduplication and caching.
        
        Args:
            url: URL string
            content: Optional content string
            
        Returns:
            Hash string
        """
        signature = url.encode('utf-8')
        if content:
            signature += content.encode('utf-8')
        return hashlib.sha256(signature).hexdigest()

    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """
        Extract main domain from URL.
        
        Args:
            url: URL string
            
        Returns:
            Domain string or None if invalid
        """
        try:
            return urlparse(url).netloc
        except Exception:
            return None

    @staticmethod
    async def get_page_metadata(page: Page) -> Dict[str, Any]:
        """
        Extract useful metadata from page.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Dictionary of metadata
        """
        try:
            metadata = await page.evaluate("""
                () => {
                    return {
                        title: document.title,
                        description: document.querySelector('meta[name="description"]')?.content,
                        keywords: document.querySelector('meta[name="keywords"]')?.content,
                        canonicalUrl: document.querySelector('link[rel="canonical"]')?.href,
                        lastModified: document.lastModified,
                        contentType: document.contentType
                    }
                }
            """)
            return metadata
        except Exception as e:
            logfire.error(
                "Error extracting page metadata",
                url=page.url,
                error=str(e)
            )
            return {}

    @staticmethod
    def matches_patterns(url: str, patterns: list[str]) -> bool:
        """
        Check if URL matches any of the provided patterns.
        
        Args:
            url: URL to check
            patterns: List of regex patterns
            
        Returns:
            Boolean indicating match
        """
        return any(
            bool(re.search(pattern, url, re.IGNORECASE))
            for pattern in patterns
        )

    @staticmethod
    async def extract_links_from_page(page: Page, base_url: str) -> Set[str]:
        """
        Extract all links from a page using different strategies.
        
        Args:
            page: Playwright Page object
            base_url: Base URL for resolving relative links
            
        Returns:
            Set of normalized URLs
        """
        try:
            # Get links from href attributes
            href_links = await page.evaluate("""
                () => Array.from(
                    document.querySelectorAll('a[href]'),
                    a => a.href
                )
            """)
            
            # Get links from onclick handlers
            onclick_links = await page.evaluate("""
                () => {
                    const links = new Set();
                    document.querySelectorAll('[onclick]').forEach(el => {
                        const match = el.getAttribute('onclick').match(/window\.location\.href='([^']+)'/);
                        if (match) links.add(match[1]);
                    });
                    return Array.from(links);
                }
            """)
            
            # Get links from data attributes
            data_links = await page.evaluate("""
                () => Array.from(
                    document.querySelectorAll('[data-href], [data-url]'),
                    el => el.dataset.href || el.dataset.url
                )
            """)
            
            # Combine and normalize all links
            all_links = set()
            for link in href_links + onclick_links + data_links:
                if link:
                    normalized = urljoin(base_url, link)
                    if urlparse(normalized).scheme in ['http', 'https']:
                        all_links.add(normalized)
                        
            return all_links
            
        except Exception as e:
            logfire.error(
                "Error extracting links from page",
                url=page.url,
                error=str(e)
            )
            return set()

    @staticmethod
    async def is_valid_response(response: Response) -> bool:
        """
        Check if response is valid for processing.
        
        Args:
            response: Playwright Response object
            
        Returns:
            Boolean indicating validity
        """
        try:
            # Check status code
            if response.status != 200:
                return False
                
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('text/html'):
                return False
                
            # Check response size
            content_length = int(response.headers.get('content-length', 0))
            if content_length > 10 * 1024 * 1024:  # 10MB limit
                return False
                
            return True
            
        except Exception:
            return False

    @staticmethod
    async def extract_structured_data(page: Page) -> List[Dict[str, Any]]:
        """
        Extract structured data (JSON-LD, microdata) from page.
        
        Args:
            page: Playwright Page object
            
        Returns:
            List of structured data items
        """
        try:
            # Extract JSON-LD
            json_ld = await page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('script[type="application/ld+json"]');
                    return Array.from(elements).map(el => {
                        try {
                            return JSON.parse(el.textContent);
                        } catch {
                            return null;
                        }
                    }).filter(Boolean);
                }
            """)
            
            # Extract microdata (simplified)
            microdata = await page.evaluate("""
                () => {
                    const items = document.querySelectorAll('[itemscope]');
                    return Array.from(items).map(item => {
                        const data = {};
                        item.querySelectorAll('[itemprop]').forEach(prop => {
                            data[prop.getAttribute('itemprop')] = prop.textContent.trim();
                        });
                        return data;
                    });
                }
            """)
            
            return json_ld + microdata
            
        except Exception as e:
            logfire.error(
                "Error extracting structured data",
                url=page.url,
                error=str(e)
            )
            return []

    @staticmethod
    async def analyze_with_scrapegraph(
        page: Page,
        api_key: str,
        task_type: str = 'extract_links'
    ) -> Tuple[Set[str], Set[str]]:
        """
        Analyze page content using ScrapegraphAI.
        
        Args:
            page: Playwright Page object
            api_key: ScrapegraphAI API key
            task_type: Type of analysis to perform
            
        Returns:
            Tuple of (target_urls, seed_urls)
        """
        try:
            # Get page content and metadata
            content = await page.content()
            metadata = await CrawlerUtils.get_page_metadata(page)
            
            # Prepare request to ScrapegraphAI
            data = {
                'content': content,
                'metadata': metadata,
                'url': page.url,
                'task_type': task_type
            }
            
            # Here you would make the actual API call to ScrapegraphAI
            # This is a placeholder for the API integration
            # response = await make_scrapegraph_api_call(api_key, data)
            
            # For now, return empty sets
            return set(), set()
            
        except Exception as e:
            logfire.error(
                "Error analyzing with ScrapegraphAI",
                url=page.url,
                error=str(e)
            )
            return set(), set()

    @staticmethod
    def should_respect_robots_txt(domain: str) -> bool:
        """
        Check if robots.txt should be respected for domain.
        
        Args:
            domain: Domain to check
            
        Returns:
            Boolean indicating if robots.txt should be respected
        """
        # Add logic here to determine if robots.txt should be respected
        # Could check against a whitelist/blacklist, configuration, etc.
        return True

    @staticmethod
    async def wait_for_page_load(page: Page, timeout: int = 30000) -> bool:
        """
        Wait for page to be fully loaded.
        
        Args:
            page: Playwright Page object
            timeout: Timeout in milliseconds
            
        Returns:
            Boolean indicating success
        """
        try:
            # Wait for network to be idle
            await page.wait_for_load_state('networkidle', timeout=timeout)
            
            # Wait for no visible loading indicators
            await page.wait_for_function("""
                () => !document.querySelector(
                    '[class*="load"], [class*="spin"], [id*="load"], [id*="spin"]'
                )
            """, timeout=timeout)
            
            return True
            
        except Exception as e:
            logfire.error(
                "Error waiting for page load",
                url=page.url,
                error=str(e)
            )
            return False