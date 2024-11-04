# src/doccrawl/crud/base_crud.py
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logfire
from psycopg2.extras import execute_values, DictCursor
import psycopg2

class BaseCRUD:
    """Base CRUD operations for database interactions."""
    
    def __init__(self, conn):
        self.conn = conn
        self.logger = logfire

    def execute_query(
        self,
        query: str,
        values: tuple = None,
        fetch: bool = False,
        commit: bool = True
    ) -> Optional[List[Dict]]:
        """
        Execute a database query with error handling and transaction management.
        
        Args:
            query: SQL query to execute
            values: Optional tuple of values for query parameters
            fetch: Whether to fetch and return results
            commit: Whether to commit the transaction
            
        Returns:
            Optional list of dictionaries with query results
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, values)
                
                result = None
                if fetch:
                    result = [dict(row) for row in cur.fetchall()]
                    
                if commit:
                    self.conn.commit()
                    
                return result
                
        except Exception as e:
            if commit:
                self.conn.rollback()
            self.logger.error(
                "Database query execution failed",
                query=query,
                error=str(e)
            )
            raise

    def insert_one(
        self, 
        table: str, 
        data: Dict[str, Any], 
        return_id: bool = True
    ) -> Optional[int]:
        """
        Insert a single record into specified table.
        
        Args:
            table: Table name
            data: Dictionary of column:value pairs
            return_id: Whether to return the inserted record ID
            
        Returns:
            Optional ID of inserted record
        """
        try:
            # Filter out None values
            filtered_data = {k: v for k, v in data.items() if v is not None}
            
            columns = list(filtered_data.keys())
            values = list(filtered_data.values())
            placeholders = ', '.join(['%s'] * len(columns))
            
            query = f"""
            INSERT INTO {table} 
            ({', '.join(columns)}) 
            VALUES ({placeholders})
            """
            
            if return_id:
                query += " RETURNING id"
            
            with self.conn.cursor() as cur:
                cur.execute(query, values)
                record_id = cur.fetchone()[0] if return_id else None
                self.conn.commit()
                
                self.logger.info(
                    'Record inserted successfully',
                    table=table,
                    record_id=record_id if return_id else None
                )
                
                return record_id
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(
                'Error inserting record',
                table=table,
                error=str(e),
                data=str(data)
            )
            raise

    def insert_many(
        self,
        table: str,
        columns: List[str],
        values: List[Tuple],
        page_size: int = 1000
    ) -> None:
        """
        Insert multiple records with batching.
        
        Args:
            table: Table name
            columns: List of column names
            values: List of value tuples
            page_size: Batch size for inserts
        """
        try:
            with self.conn.cursor() as cur:
                # Process in batches
                for i in range(0, len(values), page_size):
                    batch = values[i:i + page_size]
                    
                    query = f"""
                    INSERT INTO {table} 
                    ({', '.join(columns)}) 
                    VALUES %s
                    """
                    
                    execute_values(cur, query, batch)
                    self.conn.commit()
                    
                    self.logger.info(
                        'Batch insert completed',
                        table=table,
                        records=len(batch)
                    )
                    
        except Exception as e:
            self.conn.rollback()
            self.logger.error(
                'Error in batch insert',
                table=table,
                error=str(e)
            )
            raise

    def update(
        self,
        table: str,
        conditions: Dict[str, Any],
        data: Dict[str, Any],
        return_updated: bool = False
    ) -> Optional[List[Dict]]:
        """
        Update records matching conditions.
        
        Args:
            table: Table name
            conditions: Dictionary of where conditions
            data: Dictionary of values to update
            return_updated: Whether to return updated records
            
        Returns:
            Optional list of updated records
        """
        try:
            set_items = [f"{k} = %s" for k in data.keys()]
            set_values = list(data.values())
            
            where_items = [f"{k} = %s" for k in conditions.keys()]
            where_values = list(conditions.values())
            
            query = f"""
            UPDATE {table} 
            SET {', '.join(set_items)}
            WHERE {' AND '.join(where_items)}
            """
            
            if return_updated:
                query += " RETURNING *"
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, set_values + where_values)
                updated = [dict(row) for row in cur.fetchall()] if return_updated else None
                self.conn.commit()
                
                self.logger.info(
                    'Update completed successfully',
                    table=table,
                    conditions=conditions
                )
                
                return updated
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(
                'Error updating records',
                table=table,
                error=str(e)
            )
            raise

    def select(
        self,
        table: str,
        conditions: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        Select records with filtering and pagination.
        
        Args:
            table: Table name
            conditions: Optional filter conditions
            columns: Optional columns to select
            order_by: Optional ORDER BY clause
            limit: Optional LIMIT value
            offset: Optional OFFSET value
            
        Returns:
            List of matching records as dictionaries
        """
        try:
            select_clause = '*' if not columns else ', '.join(columns)
            query_parts = [f"SELECT {select_clause} FROM {table}"]
            values = []
            
            # Build WHERE clause
            if conditions:
                where_conditions = []
                for k, v in conditions.items():
                    if isinstance(v, (list, tuple)):
                        where_conditions.append(f"{k} = ANY(%s)")
                        values.append(list(v))
                    elif v is None:
                        where_conditions.append(f"{k} IS NULL")
                    else:
                        where_conditions.append(f"{k} = %s")
                        values.append(v)
                
                if where_conditions:
                    query_parts.append("WHERE " + " AND ".join(where_conditions))
            
            # Add ordering
            if order_by:
                query_parts.append(f"ORDER BY {order_by}")
            
            # Add pagination
            if limit is not None:
                query_parts.append(f"LIMIT {limit}")
            if offset is not None:
                query_parts.append(f"OFFSET {offset}")
            
            query = " ".join(query_parts)
            
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, values)
                results = [dict(row) for row in cur.fetchall()]
                
                self.logger.info(
                    'Select query executed successfully',
                    table=table,
                    records_found=len(results)
                )
                
                return results
                
        except Exception as e:
            self.logger.error(
                'Error selecting records',
                table=table,
                error=str(e)
            )
            raise

    def delete(
        self,
        table: str,
        conditions: Dict[str, Any]
    ) -> int:
        """
        Delete records matching conditions.
        
        Args:
            table: Table name
            conditions: Dictionary of where conditions
            
        Returns:
            Number of records deleted
        """
        try:
            where_items = [f"{k} = %s" for k in conditions.keys()]
            values = list(conditions.values())
            
            query = f"""
            DELETE FROM {table}
            WHERE {' AND '.join(where_items)}
            RETURNING id
            """
            
            with self.conn.cursor() as cur:
                cur.execute(query, values)
                deleted_ids = cur.fetchall()
                self.conn.commit()
                
                count = len(deleted_ids)
                self.logger.info(
                    'Delete completed successfully',
                    table=table,
                    records_deleted=count
                )
                
                return count
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(
                'Error deleting records',
                table=table,
                error=str(e)
            )
            raise

    def count(
        self,
        table: str,
        conditions: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records matching conditions.
        
        Args:
            table: Table name
            conditions: Optional filter conditions
            
        Returns:
            Count of matching records
        """
        try:
            query = f"SELECT COUNT(*) FROM {table}"
            values = []
            
            if conditions:
                where_items = [f"{k} = %s" for k in conditions.keys()]
                values = list(conditions.values())
                query += f" WHERE {' AND '.join(where_items)}"
            
            with self.conn.cursor() as cur:
                cur.execute(query, values)
                return cur.fetchone()[0]
                
        except Exception as e:
            self.logger.error(
                'Error counting records',
                table=table,
                error=str(e)
            )
            raise

    def exists(
        self,
        table: str,
        conditions: Dict[str, Any]
    ) -> bool:
        """
        Check if records matching conditions exist.
        
        Args:
            table: Table name
            conditions: Dictionary of where conditions
            
        Returns:
            Boolean indicating if matching records exist
        """
        try:
            where_items = [f"{k} = %s" for k in conditions.keys()]
            values = list(conditions.values())
            
            query = f"""
            SELECT EXISTS(
                SELECT 1 FROM {table}
                WHERE {' AND '.join(where_items)}
            )
            """
            
            with self.conn.cursor() as cur:
                cur.execute(query, values)
                return cur.fetchone()[0]
                
        except Exception as e:
            self.logger.error(
                'Error checking existence',
                table=table,
                error=str(e)
            )
            return False
