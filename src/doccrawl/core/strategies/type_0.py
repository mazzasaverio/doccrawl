# src/core/strategies/type_0.py
from typing import List
import logfire
from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl

class Type0Strategy(CrawlerStrategy):
    """
    Strategy for Type 0 URLs (direct target links).
    
    This strategy handles direct target URLs, like direct links to PDF files or documents.
    It only verifies the URL accessibility and target pattern match, without exploring further.
    """
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Execute Type 0 strategy for direct target URLs.
        
        Args:
            frontier_url: Current FrontierUrl to process
            
        Returns:
            List of FrontierUrl: Always empty since Type 0 doesn't discover new URLs
        """
        try:
            self.logger.info(
                "Processing direct target URL",
                url=str(frontier_url.url)
            )

            # Validate target patterns
            if not frontier_url.target_patterns:
                self.logger.error(
                    "No target patterns specified for Type 0 URL",
                    url=str(frontier_url.url)
                )
                return []

            # Verify if URL matches any target pattern
            if not self._is_target_url(str(frontier_url.url), frontier_url.target_patterns):
                self.logger.warning(
                    "URL does not match target patterns",
                    url=str(frontier_url.url),
                    patterns=frontier_url.target_patterns
                )
                return []

            # Verify URL accessibility
            response = await self.page.goto(
                str(frontier_url.url),
                wait_until='domcontentloaded',
                timeout=15000
            )
            if not response or response.status != 200:
                self.logger.error(
                    "URL not accessible or returned error",
                    url=str(frontier_url.url),
                    status=response.status if response else None
                )
                return []

            # Check content type for document types
            content_type = response.headers.get('content-type', '').lower()
            is_document = any(doc_type in content_type for doc_type in [
                'pdf', 'msword', 'vnd.openxmlformats', 'vnd.ms-excel'
            ])

            if not is_document and not any(ext in str(frontier_url.url).lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                self.logger.warning(
                    "URL may not point to a document",
                    url=str(frontier_url.url),
                    content_type=content_type
                )

            # Mark URL as target
            frontier_url.is_target = True
            
            self.logger.info(
                "Direct target URL verified",
                url=str(frontier_url.url),
                content_type=content_type
            )
            
            return []

        except Exception as e:
            self.logger.error(
                "Error processing Type 0 URL",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []