"""Command-line entry point for doccrawl."""
import asyncio
import os
import sys
from pathlib import Path
import logfire

def setup_environment():
    """Configura l'ambiente prima di eseguire l'applicazione."""
    # Aggiungi la directory 'src' al percorso di ricerca di Python
    src_path = str(Path(__file__).parent.parent)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    # Configura Logfire per inviare i log alla console
    logfire.configure(console=logfire.ConsoleOptions(min_log_level='info', verbose=True))

def main():
    """Main entry point for the application."""
    setup_environment()
    try:
        from doccrawl.main import CrawlerApp
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        app = CrawlerApp()
        try:
            loop.run_until_complete(app.run())
        except Exception as e:
            logfire.error(f"Application error: {str(e)}")
            if "Executable doesn't exist" in str(e):
                logfire.info("Try running 'playwright install chromium' manually")
            sys.exit(1)
        
    except Exception as e:
        logfire.error(f"Application failed to start: {str(e)}")
        sys.exit(1)
    finally:
        try:
            loop.close()
        except:
            pass

if __name__ == "__main__":
    main()