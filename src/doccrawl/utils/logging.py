import logfire

def setup_logging():
    """Configure logging with logfire based on official documentation."""
    
    logfire.configure()  # Configura logfire con le impostazioni di base

    # Configurazione metriche di base per il monitoraggio
    logfire.metric_counter(
        'processed_urls',
        unit='1',
        description='Number of processed URLs'
    )

    logfire.metric_counter(
        'failed_urls',
        unit='1',
        description='Number of failed URLs'
    )

    logfire.metric_histogram(
        'url_processing_time',
        unit='s',
        description='Time taken to process URLs'
    )

def get_logger(name: str):
    """Get a logfire logger instance."""
    return logfire.getLogger(name)