"""Document crawling and archiving system."""

__version__ = "0.1.0"

# Avoid circular imports by importing only what's needed
from .models.frontier_model import FrontierUrl, UrlType, FrontierBatch
from .core.crawler import Crawler
from .config.settings import settings

__all__ = ["FrontierUrl", "UrlType", "FrontierBatch", "Crawler", "settings"]