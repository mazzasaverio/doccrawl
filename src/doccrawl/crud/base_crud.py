# src/crud/base_crud.py
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logfire
from psycopg2.extras import execute_values, DictCursor

class BaseCRUD:
    """
    Base CRUD operations for database interactions.
    Provides generic database operations that can be used across different tables.
    """
    
    def __init__(self, conn):
        """
        Initialize BaseCRUD with a database connection.
        
        Args:
            conn: psycopg2 connection object
        """
        self.conn = conn
        self.logger = logfire

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
            data: Dictionary of column names and values
            return_id: Whether to return the ID of the inserted record
        
        Returns:
            The ID of the inserted record if return_id is True
        """
        with self.conn.cursor() as cur:
            try:
                # Filter out None values unless explicitly needed
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
        Insert multiple records into specified table with pagination.
        
        Args:
            table: Table name
            columns: List of column names
            values: List of tuples containing values
            page_size: Number of records to insert at once
        """
        with self.conn.cursor() as cur:
            try:
                # Insert in batches to handle large datasets
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
                    'Bulk insert completed successfully',
                    table=table,
                    total_records=len(values)
                )
                
            except Exception as e:
                self.conn.rollback()
                self.logger.error(
                    'Error in bulk insert',
                    table=table,
                    error=str(e),
                    batch_size=page_size
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
        Update records that match the conditions.
        
        Args:
            table: Table name
            conditions: Dictionary of column names and values for WHERE clause
            data: Dictionary of columns to update with new values
            return_updated: Whether to return the updated records
            
        Returns:
            List of updated records if return_updated is True
        """
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            try:
                # Prepare SET clause
                set_items = [f"{k} = %s" for k in data.keys()]
                set_values = list(data.values())
                
                # Prepare WHERE clause
                where_items = [f"{k} = %s" for k in conditions.keys()]
                where_values = list(conditions.values())
                
                query = f"""
                UPDATE {table} 
                SET {', '.join(set_items)}
                WHERE {' AND '.join(where_items)}
                """
                
                if return_updated:
                    query += " RETURNING *"
                
                cur.execute(query, set_values + where_values)
                updated_records = [dict(row) for row in cur.fetchall()] if return_updated else None
                self.conn.commit()
                
                self.logger.info(
                    'Update completed successfully',
                    table=table,
                    conditions=str(conditions),
                    records_updated=len(updated_records) if return_updated else 'Unknown'
                )
                
                return updated_records
                
            except Exception as e:
                self.conn.rollback()
                self.logger.error(
                    'Error updating records',
                    table=table,
                    error=str(e),
                    conditions=str(conditions)
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
        Select records based on conditions with pagination support.
        
        Args:
            table: Table name
            conditions: Optional dictionary of column names and values for WHERE clause
            columns: Optional list of columns to select
            order_by: Optional string for ORDER BY clause
            limit: Optional integer for LIMIT clause
            offset: Optional integer for OFFSET clause
        
        Returns:
            List of dictionaries representing the selected records
        """
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            try:
                # Build SELECT clause
                select_clause = '*' if not columns else ', '.join(columns)
                query_parts = [f"SELECT {select_clause} FROM {table}"]
                values = []
                
                # Build WHERE clause if conditions provided
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
                
                # Add optional clauses
                if order_by:
                    query_parts.append(f"ORDER BY {order_by}")
                if limit is not None:
                    query_parts.append(f"LIMIT {limit}")
                if offset is not None:
                    query_parts.append(f"OFFSET {offset}")
                
                query = " ".join(query_parts)
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
                    error=str(e),
                    conditions=str(conditions)
                )
                raise

    def delete(self, table: str, conditions: Dict[str, Any]) -> int:
        """
        Delete records based on conditions.
        
        Args:
            table: Table name
            conditions: Dictionary of column names and values for WHERE clause
        
        Returns:
            Number of records deleted
        """
        with self.conn.cursor() as cur:
            try:
                where_items = [f"{k} = %s" for k in conditions.keys()]
                values = list(conditions.values())
                
                query = f"""
                DELETE FROM {table} 
                WHERE {' AND '.join(where_items)}
                RETURNING id
                """
                
                cur.execute(query, values)
                deleted_count = len(cur.fetchall())
                self.conn.commit()
                
                self.logger.info(
                    'Delete operation completed successfully',
                    table=table,
                    records_deleted=deleted_count
                )
                
                return deleted_count
                
            except Exception as e:
                self.conn.rollback()
                self.logger.error(
                    'Error deleting records',
                    table=table,
                    error=str(e),
                    conditions=str(conditions)
                )
                raise

    def exists(self, table: str, conditions: Dict[str, Any]) -> bool:
        """
        Check if records exist based on conditions.
        
        Args:
            table: Table name
            conditions: Dictionary of column names and values to check
        
        Returns:
            Boolean indicating if matching record exists
        """
        with self.conn.cursor() as cur:
            try:
                where_items = [f"{k} = %s" for k in conditions.keys()]
                values = list(conditions.values())
                
                query = f"""
                SELECT EXISTS(
                    SELECT 1 FROM {table} 
                    WHERE {' AND '.join(where_items)}
                )
                """
                
                cur.execute(query, values)
                return cur.fetchone()[0]
                
            except Exception as e:
                self.logger.error(
                    'Error checking existence',
                    table=table,
                    error=str(e),
                    conditions=str(conditions)
                )
                raise