# src/doccrawl/crud/config_url_log_crud.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

from .base_crud import BaseCRUD
from ..models.config_url_log_model import ConfigUrlLog, ConfigUrlStatus
# src/doccrawl/crud/config_url_log_crud.py

class ConfigUrlLogCRUD(BaseCRUD):
    def __init__(self, conn):
        super().__init__(conn)
        self.table = "config_url_logs"

    def create_log(self, log: ConfigUrlLog) -> int:
        """Create a new log entry."""
        data = log.model_dump(exclude={'id'})
        return self.insert_one(self.table, data)

    def update_status(
        self, 
        log_id: int, 
        status: ConfigUrlStatus,
        error_message: Optional[str] = None,
        **metrics
    ) -> Optional[ConfigUrlLog]:
        """Update log status and related metrics."""
        data = {
            'status': status.value,  # Convert enum to string
            'updated_at': datetime.now(),
            'error_message': error_message,
            **metrics
        }
        
        if status in [ConfigUrlStatus.COMPLETED, ConfigUrlStatus.FAILED, 
                     ConfigUrlStatus.PARTIALLY_COMPLETED]:
            data['end_time'] = datetime.now()
            if data.get('start_time'):
                data['processing_duration'] = (
                    data['end_time'] - data['start_time']
                ).total_seconds()
        
        updated = self.update(
            self.table,
            conditions={'id': log_id},
            data=data,
            return_updated=True
        )
        
        return ConfigUrlLog.model_validate(updated[0]) if updated else None

    def start_processing(self, log_id: int) -> Optional[ConfigUrlLog]:
        """Mark a config URL as starting processing."""
        data = {
            'status': ConfigUrlStatus.RUNNING.value,  # Convert enum to string
            'start_time': datetime.now(),
            'updated_at': datetime.now()
        }
        
        updated = self.update(
            self.table,
            conditions={'id': log_id},
            data=data,
            return_updated=True
        )
        
        return ConfigUrlLog.model_validate(updated[0]) if updated else None

    def increment_counters(
        self,
        log_id: int,
        target_urls: int = 0,
        seed_urls: int = 0,
        failed_urls: int = 0
    ) -> None:
        """Increment URL counters for a log entry."""
        total = target_urls + seed_urls
        data = {
            'total_urls_found': total,
            'target_urls_found': target_urls, 
            'seed_urls_found': seed_urls,
            'failed_urls': failed_urls,
            'updated_at': datetime.now()
        }
        
        self.update(
            self.table,
            conditions={'id': log_id},
            data=data
        )

    def add_warning(self, log_id: int, warning: str) -> None:
        """Add a warning message to the log."""
        data = {
            'warning_messages': [warning],  # PostgreSQL will append this to existing array
            'updated_at': datetime.now()
        }
        
        self.update(
            self.table,
            conditions={'id': log_id},
            data=data
        )

    def get_category_summary(self, category: str) -> List[Dict[str, Any]]:
        """Get processing summary for all URLs in a category."""
        return self.select(
            self.table,
            conditions={'category': category},
            columns=[
                'status',
                'COUNT(*) as count',
                'SUM(target_urls_found) as total_targets',
                'SUM(seed_urls_found) as total_seeds',
                'SUM(failed_urls) as total_failures',
                'AVG(processing_duration) as avg_duration',
                'MIN(start_time) as first_started',
                'MAX(end_time) as last_completed'
            ],
            order_by='status'
        )

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get overall processing statistics."""
        results = self.select(
            self.table,
            columns=[
                'COUNT(*) as total_configs',
                "SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed",
                "SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed",
                'SUM(target_urls_found) as total_targets',
                'SUM(seed_urls_found) as total_seeds',
                'SUM(failed_urls) as total_failures',
                'AVG(processing_duration) as avg_duration',
                'MAX(processing_duration) as max_duration'
            ]
        )
        return results[0] if results else {}