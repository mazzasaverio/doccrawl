"""Script to clean up all database tables using existing database connection."""
import sys
from pathlib import Path
import logfire

# Aggiungi la directory src al path per importare i moduli
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from doccrawl.db.connection import DatabaseConnection
from doccrawl.utils.logging import setup_logging

def cleanup_database(conn) -> dict:
    """Clean up all tables by deleting all records and resetting sequences."""
    tables = ['url_frontier', 'config_url_logs']
    deleted = {}
    
    try:
        with conn.cursor() as cur:
            for table in tables:
                # Get count before deletion
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                
                # Delete all records and reset sequences
                cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                
                deleted[table] = count
                
                logfire.info(
                    f"Cleaned table {table}",
                    deleted_records=count
                )
            
            conn.commit()
            
            return deleted
            
    except Exception as e:
        conn.rollback()
        logfire.error("Database cleanup failed", error=str(e))
        raise

def main():
    """Main function to clean database tables."""
    # Setup logging
    setup_logging()
    
    db_connection = None
    try:
        # Initialize database connection using existing class
        db_connection = DatabaseConnection()
        db_connection.connect()
        
        # Execute cleanup
        logfire.info("Starting database cleanup")
        deleted = cleanup_database(db_connection.conn)
        
        # Print results
        total_deleted = sum(deleted.values())
        logfire.info(
            "Database cleanup completed",
            total_deleted=total_deleted,
            deleted_by_table=deleted
        )
        
    except Exception as e:
        logfire.error(f"Error: {str(e)}")
        sys.exit(1)
        
    finally:
        if db_connection:
            db_connection.close()
            logfire.info("Database connection closed")

if __name__ == "__main__":
    main()