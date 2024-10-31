"""Database connection module."""
import psycopg2
from psycopg2.extras import DictCursor
import logfire
from ..config.settings import settings

class DatabaseConnection:
    """Database connection handler."""
    
    def __init__(self):
        self.conn = None
        self._cursor = None

    def connect(self):
        """Establish database connection using settings."""
        try:
            db_settings = settings.database
            
            # Log connection attempt (senza password)
            logfire.info(
                "Attempting database connection",
                host=db_settings.host,
                port=db_settings.port,
                user=db_settings.user,
                database=db_settings.database
            )
            
            self.conn = psycopg2.connect(
                dbname=db_settings.database,
                user=db_settings.user,
                password=db_settings.password.get_secret_value(),
                host=db_settings.host,
                port=db_settings.port,
                sslmode=db_settings.sslmode
            )
            
            logfire.info("Successfully connected to the database")
            return self.conn
            
        except psycopg2.Error as e:
            logfire.error(
                "Database connection error",
                error_type=type(e).__name__,
                error_code=e.pgcode if hasattr(e, 'pgcode') else None,
                error_message=str(e)
            )
            raise

    def cursor(self, *args, **kwargs):
        """Get database cursor."""
        if not self.conn:
            self.connect()
        return self.conn.cursor(*args, **kwargs)

    def create_tables(self):
        """Create required tables if they don't exist."""
        if not self.conn:
            self.connect()
            
        with self.cursor() as cur:
            try:
                # Create frontier table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS url_frontier (
                        id SERIAL PRIMARY KEY,
                        category VARCHAR(255) NOT NULL,
                        url TEXT NOT NULL,
                        url_type INTEGER NOT NULL,
                        depth INTEGER NOT NULL DEFAULT 0,
                        main_domain TEXT NOT NULL,
                        target_patterns TEXT[],
                        seed_pattern TEXT,
                        max_depth INTEGER NOT NULL,
                        is_target BOOLEAN NOT NULL DEFAULT FALSE,
                        parent_url TEXT,
                        insert_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'pending',
                        error_message TEXT
                    );
                    
                    -- Create indexes for better performance
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_url ON url_frontier(url);
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_status ON url_frontier(status);
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_category ON url_frontier(category);
                """)
                self.conn.commit()
                logfire.info("Successfully created/verified tables")
                
            except Exception as e:
                self.conn.rollback()
                logfire.error("Error creating tables", error=str(e))
                raise

    def commit(self):
        """Commit current transaction."""
        if self.conn:
            self.conn.commit()

    def rollback(self):
        """Rollback current transaction."""
        if self.conn:
            self.conn.rollback()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logfire.info("Database connection closed")

    def __enter__(self):
        """Context manager enter."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()