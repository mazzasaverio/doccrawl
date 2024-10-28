# src/crud/frontier_crud.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from .base_crud import BaseCRUD
from ..models.frontier_model import FrontierUrl, UrlStatus, FrontierStatistics, FrontierBatch

class FrontierCRUD(BaseCRUD):
    """CRUD operations for the URL frontier table."""
    
    def __init__(self, conn):
        super().__init__(conn)
        self.table = "url_frontier"

    def create_url(self, frontier_url: FrontierUrl) -> int:
        """
        Create a new URL entry in the frontier.
        
        Args:
            frontier_url: FrontierUrl model instance
            
        Returns:
            ID of the created record
        """
        data = frontier_url.model_dump(exclude={'id'})
        data['insert_date'] = datetime.now()
        data['last_update'] = datetime.now()
        
        return self.insert_one(self.table, data)

    def create_urls_batch(self, batch: FrontierBatch) -> None:
        """
        Create multiple URL entries in batch.
        
        Args:
            batch: FrontierBatch model containing multiple URLs
        """
        now = datetime.now()
        columns = [
            'url', 'category', 'url_type', 'depth', 'main_domain',
            'target_patterns', 'seed_pattern', 'max_depth', 'is_target',
            'parent_url', 'insert_date', 'last_update', 'status'
        ]
        
        values = []
        for url_chunk in batch.chunk_urls():
            chunk_values = []
            for frontier_url in url_chunk:
                data = frontier_url.model_dump(exclude={'id'})
                row = tuple(data.get(col) if col not in ['insert_date', 'last_update']
                          else now for col in columns)
                chunk_values.append(row)
            values.extend(chunk_values)
            
        self.insert_many(self.table, columns, values)

    def get_pending_urls(
        self,
        category: Optional[str] = None,
        url_type: Optional[int] = None,
        limit: int = 100
    ) -> List[FrontierUrl]:
        """
        Get pending URLs for processing.
        
        Args:
            category: Optional category filter
            url_type: Optional URL type filter
            limit: Maximum number of URLs to return
            
        Returns:
            List of FrontierUrl instances
        """
        conditions = {'status': UrlStatus.PENDING}
        if category:
            conditions['category'] = category
        if url_type is not None:
            conditions['url_type'] = url_type
            
        results = self.select(
            self.table,
            conditions=conditions,
            order_by='insert_date ASC',
            limit=limit
        )
        
        return [FrontierUrl.model_validate(result) for result in results]

    def update_url_status(
        self,
        url_id: int,
        status: UrlStatus,
        error_message: Optional[str] = None
    ) -> Optional[FrontierUrl]:
        """
        Update the status of a URL.
        
        Args:
            url_id: ID of the URL to update
            status: New status
            error_message: Optional error message for failed status
            
        Returns:
            Updated FrontierUrl instance
        """
        data = {
            'status': status,
            'last_update': datetime.now(),
            'error_message': error_message
        }
        
        updated = self.update(
            self.table,
            conditions={'id': url_id},
            data=data,
            return_updated=True
        )
        
        return FrontierUrl.model_validate(updated[0]) if updated else None

    def get_url_by_url(self, url: str) -> Optional[FrontierUrl]:
        """
        Get a URL entry by its URL string.
        
        Args:
            url: URL string to look up
            
        Returns:
            FrontierUrl instance if found
        """
        results = self.select(self.table, conditions={'url': url})
        return FrontierUrl.model_validate(results[0]) if results else None

    def get_category_statistics(self, category: str) -> FrontierStatistics:
        """
        Get statistics for a specific category.
        
        Args:
            category: Category to get statistics for
            
        Returns:
            FrontierStatistics instance
        """
        with self.conn.cursor() as cur:
            query = """
            SELECT 
                COUNT(*) as total_urls,
                SUM(CASE WHEN is_target THEN 1 ELSE 0 END) as target_urls,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_urls,
                SUM(CASE WHEN status = 'processed' THEN 1 ELSE 0 END) as processed_urls,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_urls,
                COUNT(DISTINCT main_domain) as unique_domains,
                MAX(depth) as max_reached_depth,
                MIN(insert_date) as first_url_date,
                MAX(last_update) as last_update_date
            FROM url_frontier
            WHERE category = %s
            """
            
            cur.execute(query, (category,))
            result = dict(zip([desc[0] for desc in cur.description], cur.fetchone()))
            
            # Calculate success rate
            total_processed = result['processed_urls'] + result['failed_urls']
            success_rate = (result['processed_urls'] / total_processed * 100 
                          if total_processed > 0 else 0)
            
            return FrontierStatistics(
                category=category,
                success_rate=success_rate,
                **result
            )

    def exists_in_frontier(self, url: str) -> bool:
        """
        Check if a URL exists in the frontier.
        
        Args:
            url: URL to check
            
        Returns:
            Boolean indicating if URL exists
        """
        return self.exists(self.table, {'url': url})

    def mark_urls_as_skipped(self, urls: List[str]) -> int:
        """
        Mark multiple URLs as skipped.
        
        Args:
            urls: List of URLs to mark as skipped
            
        Returns:
            Number of URLs updated
        """
        data = {
            'status': UrlStatus.SKIPPED,
            'last_update': datetime.now()
        }
        
        updated = self.update(
            self.table,
            conditions={'url': urls},
            data=data,
            return_updated=True
        )
        
        return len(updated) if updated else 0