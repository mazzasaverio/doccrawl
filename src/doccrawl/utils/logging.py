import logging
import logfire


def setup_logging():
    """Configure logging with logfire."""
    # Configurazione base
    logfire.configure(console=logfire.ConsoleOptions(min_log_level='info', verbose=True,  show_project_link =False, ))

    handler = logfire.LogfireLoggingHandler()
    logging.basicConfig(handlers=[handler], level=logging.INFO)
    # Metriche per tracciare le URL processate
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

    # Metriche per il tempo di processamento
    logfire.metric_histogram(
        'url_processing_time',
        unit='s',
        description='Time taken to process URLs'
    )

    # Metriche per la distribuzione della profondità
    logfire.metric_histogram(
        'url_depth_distribution',
        unit='count',
        description='Distribution of URL depths'
    )

    # Metriche per la dimensione della frontier
    logfire.metric_gauge(
        'frontier_size',
        unit='count', 
        description='Total URLs in frontier'
    )

    # Metrica per il rate di crawling
    logfire.metric_gauge(
        'crawling_rate',
        unit='urls/min',
        description='URLs processed per minute'
    )

    # Metrica per gli errori
    logfire.metric_counter(
        'crawler_errors',
        unit='1',
        description='Number of crawler errors'
    )

    # Log dell'inizializzazione
    logfire.info(
        "Logging system initialized",
        metrics_configured=True
    )

# Esportiamo logfire direttamente
logger = logfire