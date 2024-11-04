from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from urllib.parse import urlparse

from .base_crud import BaseCRUD
from ..models.frontier_model import (
    FrontierUrl, 
    FrontierStatistics, 
    UrlType, 
    UrlStatus, 
    FrontierBatch
)

class FrontierCRUD(BaseCRUD):
    """CRUD operations for the URL frontier table."""
    
    def __init__(self, conn):
        super().__init__(conn)
        self.table = "url_frontier"

    def create_url(self, frontier_url: FrontierUrl) -> int:
        """
        Create a new URL entry in the frontier.
        
        Args:
            frontier_url: FrontierUrl instance to create
            
        Returns:
            int: ID of created URL record
        """
        try:
            data = frontier_url.model_dump(exclude={'id'})
            
            # Convert HttpUrl fields to strings
            data['url'] = str(data['url'])
            if data.get('parent_url'):
                data['parent_url'] = str(data['parent_url'])
                
            # Convert enums to values
            data['url_type'] = data['url_type'].value
            data['status'] = UrlStatus.PENDING.value
            
            # Add timestamps
            data['insert_date'] = datetime.now()
            data['last_update'] = datetime.now()
            
            # Extract main domain if not set
            if not data.get('main_domain'):
                data['main_domain'] = urlparse(str(data['url'])).netloc
            
            with self.conn.cursor() as cur:
                columns = list(data.keys())
                values = list(data.values())
                placeholders = ', '.join(['%s'] * len(columns))
                
                query = f"""
                INSERT INTO {self.table} 
                ({', '.join(columns)}) 
                VALUES ({placeholders})
                RETURNING id
                """
                
                cur.execute(query, values)
                url_id = cur.fetchone()[0]
                self.conn.commit()
                
                self.logger.info(
                    "URL created successfully",
                    url=str(data['url']),
                    id=url_id
                )
                
                return url_id
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(
                "Error creating URL",
                url=str(frontier_url.url),
                error=str(e)
            )
            raise

    def create_urls_batch(self, batch: FrontierBatch) -> None:
        """
        Create multiple URL entries in batch.
        
        Args:
            batch: FrontierBatch instance containing URLs to create
        """
        try:
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
                    data = frontier_url.model_dump()
                    # Convert URL fields to strings
                    data['url'] = str(data['url'])
                    data['parent_url'] = str(data['parent_url']) if data.get('parent_url') else None
                    # Convert enums
                    data['url_type'] = data['url_type'].value
                    data['status'] = UrlStatus.PENDING.value
                    # Add timestamps
                    data['insert_date'] = now
                    data['last_update'] = now
                    
                    row = tuple(data.get(col) if col not in ['insert_date', 'last_update']
                              else now for col in columns)
                    chunk_values.append(row)
                    
                with self.conn.cursor() as cur:
                    query = f"""
                    INSERT INTO {self.table} 
                    ({', '.join(columns)}) 
                    VALUES %s
                    """
                    from psycopg2.extras import execute_values
                    execute_values(cur, query, chunk_values)
                    self.conn.commit()
                
                self.logger.info(
                    "Batch URLs created successfully",
                    urls_count=len(chunk_values)
                )
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(
                "Error creating batch URLs",
                error=str(e)
            )
            raise

    def exists_in_frontier(self, url: str) -> bool:
        """
        Check if URL exists in frontier.
        
        Args:
            url: URL string to check
            
        Returns:
            bool: True if URL exists, False otherwise
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                SELECT EXISTS(
                    SELECT 1 FROM url_frontier 
                    WHERE url = %s
                )
                """
                cur.execute(query, (url,))
                return cur.fetchone()[0]
                
        except Exception as e:
            self.logger.error(
                "Error checking URL existence",
                url=url,
                error=str(e)
            )
            return False

    def get_url_by_url(self, url: str) -> Optional[FrontierUrl]:
        """
        Get URL entry by URL string.
        
        Args:
            url: URL string to lookup
            
        Returns:
            Optional[FrontierUrl]: FrontierUrl instance if found
        """
        try:
            with self.conn.cursor() as cur:
                query = "SELECT * FROM url_frontier WHERE url = %s"
                cur.execute(query, (url,))
                result = cur.fetchone()
                if result:
                    # Convert DB row to dict
                    columns = [desc[0] for desc in cur.description]
                    row_dict = dict(zip(columns, result))
                    # Convert status and url_type back to enums
                    row_dict['status'] = UrlStatus(row_dict['status'])
                    row_dict['url_type'] = UrlType(row_dict['url_type'])
                    # Convert to FrontierUrl model
                    return FrontierUrl.model_validate(row_dict)
                return None
                
        except Exception as e:
            self.logger.error(
                "Error getting URL by string",
                url=url,
                error=str(e)
            )
            return None

    def update_url_status(
        self,
        url_id: int,
        status: UrlStatus,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update URL status and error message.
        
        Args:
            url_id: ID of URL to update
            status: New status
            error_message: Optional error message
        """
        try:
            data = {
                'status': status.value,
                'last_update': datetime.now(),
                'error_message': error_message
            }
            
            with self.conn.cursor() as cur:
                set_items = [f"{k} = %s" for k in data.keys()]
                values = list(data.values())
                
                query = f"""
                UPDATE {self.table}
                SET {', '.join(set_items)}
                WHERE id = %s
                """
                
                cur.execute(query, values + [url_id])
                self.conn.commit()
                
                self.logger.info(
                    "URL status updated",
                    url_id=url_id,
                    status=status.value
                )
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(
                "Error updating URL status",
                url_id=url_id,
                status=status,
                error=str(e)
            )
            raise

    def get_pending_urls(
        self,
        category: Optional[str] = None,
        url_type: Optional[UrlType] = None,
        limit: int = 100
    ) -> List[FrontierUrl]:
        """
        Get pending URLs for processing.
        
        Args:
            category: Optional category filter
            url_type: Optional URL type filter
            limit: Maximum number of URLs to return
            
        Returns:
            List[FrontierUrl]: List of pending URLs
        """
        try:
            conditions = {'status': UrlStatus.PENDING.value}
            if category:
                conditions['category'] = category
            if url_type:
                conditions['url_type'] = url_type.value
            
            with self.conn.cursor() as cur:
                where_parts = [f"{k} = %s" for k in conditions.keys()]
                values = list(conditions.values())
                
                query = f"""
                SELECT * FROM {self.table}
                WHERE {' AND '.join(where_parts)}
                ORDER BY insert_date ASC
                LIMIT %s
                """
                
                cur.execute(query, values + [limit])
                
                results = []
                for row in cur.fetchall():
                    # Convert DB row to dict
                    columns = [desc[0] for desc in cur.description]
                    row_dict = dict(zip(columns, row))
                    # Convert status and url_type back to enums
                    row_dict['status'] = UrlStatus(row_dict['status'])
                    row_dict['url_type'] = UrlType(row_dict['url_type'])
                    # Convert to FrontierUrl model
                    results.append(FrontierUrl.model_validate(row_dict))
                
                return results
                
        except Exception as e:
            self.logger.error(
                "Error getting pending URLs",
                category=category,
                url_type=url_type,
                error=str(e)
            )
            return []

    def get_processed_seed_urls(self, category: str) -> Set[str]:
        """
        Get set of processed seed URLs for a category.
        
        Args:
            category: Category to get processed seeds for
            
        Returns:
            Set[str]: Set of processed seed URLs
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                SELECT url FROM url_frontier
                WHERE category = %s
                AND status = %s
                AND is_target = false
                """
                cur.execute(query, (category, UrlStatus.PROCESSED.value))
                return {row[0] for row in cur.fetchall()}
                
        except Exception as e:
            self.logger.error(
                "Error getting processed seed URLs",
                category=category,
                error=str(e)
            )
            return set()

    def get_category_statistics(self, category: str) -> Optional[FrontierStatistics]:
        """
        Get statistics for a category.
        
        Args:
            category: Category name
            
        Returns:
            Optional[FrontierStatistics]: Statistics if available
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                SELECT 
                    COUNT(*) as total_urls,
                    SUM(CASE WHEN is_target THEN 1 ELSE 0 END) as target_urls,
                    SUM(CASE WHEN status = %s THEN 1 ELSE 0 END) as pending_urls,
                    SUM(CASE WHEN status = %s THEN 1 ELSE 0 END) as processed_urls,
                    SUM(CASE WHEN status = %s THEN 1 ELSE 0 END) as failed_urls,
                    COUNT(DISTINCT main_domain) as unique_domains,
                    MAX(depth) as max_reached_depth,
                    MIN(insert_date) as first_url_date,
                    MAX(last_update) as last_update_date
                FROM url_frontier
                WHERE category = %s
                """
                cur.execute(query, (
                    UrlStatus.PENDING.value,
                    UrlStatus.PROCESSED.value,
                    UrlStatus.FAILED.value,
                    category
                ))
                
                result = dict(zip([desc[0] for desc in cur.description], cur.fetchone()))
                
                if not result['total_urls']:
                    return None
                
                # Calculate success rate
                total_processed = (result['processed_urls'] or 0) + (result['failed_urls'] or 0)
                success_rate = (
                    (result['processed_urls'] / total_processed * 100)
                    if total_processed > 0 else 0
                )
                
                return FrontierStatistics(
                    category=category,
                    success_rate=success_rate,
                    **result
                )
                
        except Exception as e:
            self.logger.error(
                "Error getting category statistics",
                category=category,
                error=str(e)
            )
            return None