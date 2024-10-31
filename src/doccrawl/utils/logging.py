"""Logging configuration module."""
import logfire

def setup_logging():
    """Configure logging with logfire."""
    # Configura logfire con le impostazioni di base
    logfire.configure()

    # Configurazione metriche per il monitoraggio
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

# Non serve get_logger perché useremo direttamente logfire
logger = logfire