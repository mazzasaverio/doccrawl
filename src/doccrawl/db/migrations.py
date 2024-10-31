"""Database migrations module."""
import logging
from pathlib import Path
from typing import List, Optional

import psycopg2
from psycopg2.extensions import connection

from ..config.settings import settings

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def get_current_version(conn: connection) -> int:
    """Get current database schema version."""
    with conn.cursor() as cur:
        # Create versions table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Get highest version
        cur.execute("SELECT COALESCE(MAX(version), 0) FROM schema_versions")
        return cur.fetchone()[0]

def get_migration_files() -> List[Path]:
    """Get all migration files sorted by version."""
    if not MIGRATIONS_DIR.exists():
        return []
    
    migrations = []
    for file in MIGRATIONS_DIR.glob("*.sql"):
        try:
            version = int(file.stem.split("_")[0])
            migrations.append((version, file))
        except (ValueError, IndexError):
            logger.warning(f"Invalid migration filename: {file.name}")
            continue
            
    return [m[1] for m in sorted(migrations)]

def apply_migration(conn: connection, migration_file: Path) -> None:
    """Apply a single migration file."""
    version = int(migration_file.stem.split("_")[0])
    
    with conn.cursor() as cur:
        # Read and execute migration
        sql = migration_file.read_text()
        cur.execute(sql)
        
        # Record migration
        cur.execute(
            "INSERT INTO schema_versions (version) VALUES (%s)",
            (version,)
        )
    
    conn.commit()
    logger.info(f"Applied migration {migration_file.name}")

def migrate(target_version: Optional[int] = None) -> None:
    """Run database migrations up to target version."""
    conn = psycopg2.connect(settings.database.get_connection_string())
    
    try:
        current_version = get_current_version(conn)
        migrations = get_migration_files()
        
        if not migrations:
            logger.info("No migrations found")
            return
            
        if target_version is None:
            target_version = int(migrations[-1].stem.split("_")[0])
            
        if current_version >= target_version:
            logger.info("Database is up to date")
            return
            
        logger.info(f"Current version: {current_version}")
        logger.info(f"Target version: {target_version}")
        
        # Apply migrations in order
        for migration_file in migrations:
            version = int(migration_file.stem.split("_")[0])
            if current_version < version <= target_version:
                apply_migration(conn, migration_file)
                
        logger.info("Migrations completed successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {str(e)}")
        raise
        
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()