"""Command-line entry point for doccrawl."""
import asyncio
import os
import sys
from pathlib import Path
import logfire

def setup_environment():
    """Setup environment before running the application."""
    # Add src directory to Python path
    src_path = str(Path(__file__).parent.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Setup basic logging
    logfire.configure()

async def main() -> None:
    """Main entry point for the application."""
    try:
        setup_environment()
        
        # Import after environment setup
        from doccrawl.main import CrawlerApp
        
        app = CrawlerApp()
        await app.run()
        
    except Exception as e:
        logfire.error(f"Application failed to start: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())