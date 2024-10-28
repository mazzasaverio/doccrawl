# src/core/strategies/type_0.py
from typing import List
import logfire

from .base_strategy import CrawlerStrategy
from ...models.frontier_model import FrontierUrl
from ...utils.crawler_utils import CrawlerUtils

class Type0Strategy(CrawlerStrategy):
    """Strategy for Type 0 URLs (direct target links)."""
    
    async def execute(self, frontier_url: FrontierUrl) -> List[FrontierUrl]:
        """
        Process a Type 0 URL (direct target).
        Just verifies the URL exists and matches target patterns.
        
        Args:
            frontier_url: FrontierUrl instance to process
            
        Returns:
            Empty list as Type 0 doesn't discover new URLs
        """
        try:
            if not frontier_url.target_patterns:
                self.logger.error(
                    "No target patterns specified for Type 0 URL",
                    url=str(frontier_url.url)
                )
                return []
                
            # Verify URL matches target patterns
            is_target = CrawlerUtils.matches_patterns(
                str(frontier_url.url),
                frontier_url.target_patterns
            )
            
            if not is_target:
                self.logger.warning(
                    "Type 0 URL doesn't match target patterns",
                    url=str(frontier_url.url)
                )
                return []
                
            # Verify URL is accessible
            response = await self.page.goto(str(frontier_url.url))
            if not await CrawlerUtils.is_valid_response(response):
                self.logger.error(
                    "Invalid response for Type 0 URL",
                    url=str(frontier_url.url),
                    status=response.status
                )
                return []
                
            frontier_url.is_target = True
            return []
            
        except Exception as e:
            self.logger.error(
                "Error processing Type 0 URL",
                url=str(frontier_url.url),
                error=str(e)
            )
            return []
