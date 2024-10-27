# src/db/connection.py
import os

import psycopg2
from psycopg2.extras import DictCursor
import logfire

class DatabaseConnection:
    def __init__(self):
        self.conn = None
        self.logger = logfire

    def connect(self):
        """Establish database connection using environment variables."""
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DATABASE"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("POSTGRES_HOST"),
                port=os.getenv("POSTGRES_PORT"),
                sslmode=os.getenv("POSTGRES_SSLMODE")
            )
            self.logger.info("Successfully connected to the database")
            return self.conn
        except Exception as e:
            self.logger.error(f"Error connecting to database: {str(e)}")
            raise

    def create_tables(self):
        """Create the frontier table if it doesn't exist."""
        with self.conn.cursor() as cur:
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
                        status VARCHAR(50) DEFAULT 'pending'
                    );
                    
                    -- Create indexes for better performance
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_url ON url_frontier(url);
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_status ON url_frontier(status);
                    CREATE INDEX IF NOT EXISTS idx_url_frontier_category ON url_frontier(category);
                """)
                self.conn.commit()
                self.logger.info("Successfully created url_frontier table")
            except Exception as e:
                self.conn.rollback()
                self.logger.error(f"Error creating tables: {str(e)}")
                raise

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()