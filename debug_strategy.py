import time
import asyncio
from typing import Any, Dict, Optional, List
from functools import wraps
import logfire
from contextlib import contextmanager
from pprint import pformat
import traceback

from doccrawl.config.settings import settings
from doccrawl.models.frontier_model import FrontierUrl, UrlType
from doccrawl.core.crawler import Crawler
from doccrawl.core.strategies.type_0 import Type0Strategy
from doccrawl.core.strategies.type_1 import Type1Strategy
from doccrawl.core.strategies.type_2 import Type2Strategy
from doccrawl.core.strategies.type_3 import Type3Strategy
from doccrawl.core.strategies.type_4 import Type4Strategy

class CrawlerDebugger:
    """
    Debugger per monitorare e analizzare il comportamento del crawler.
    Permette di:
    - Tracciare il flusso di esecuzione
    - Misurare i tempi
    - Ispezionare i dati
    - Catturare errori con contesto
    """
    
    def __init__(self, enabled: bool = True, verbose: bool = False):
        self.enabled = enabled
        self.verbose = verbose
        self.step_count = 0
        self.timings = {}
        self.errors = []
        self.data_snapshots = {}
        
        # Configura logfire per il debugger
        self.logger = logfire
        
        # Metriche
        self.logger.metric_histogram(
            'step_duration',
            unit='s',
            description='Duration of each step'
        )
        
        self.logger.metric_counter(
            'errors_count',
            unit='1',
            description='Number of errors encountered'
        )
        
        self.logger.metric_gauge(
            'memory_usage',
            unit='MB',
            description='Memory usage at each step'
        )

    @contextmanager
    def step(self, name: str, data: Optional[Any] = None):
        """
        Context manager per tracciare uno step di esecuzione.
        
        Args:
            name: Nome dello step
            data: Dati opzionali da loggare
        """
        if not self.enabled:
            yield
            return
            
        self.step_count += 1
        step_id = f"Step {self.step_count}: {name}"
        
        try:
            start_time = time.time()
            self.logger.info(f"\n{'='*20} {step_id} Start {'='*20}")
            
            if data and self.verbose:
                self.logger.info(
                    "Input data:",
                    data=pformat(data, indent=2)
                )
            
            yield
            
            duration = time.time() - start_time
            self.timings[step_id] = duration
            
            self.logger.info(
                f"{'='*20} {step_id} End {'='*20}",
                duration=f"{duration:.2f}s"
            )
            
            # Registra la metrica
            self.logger.metric_histogram('step_duration').record(duration)
            
        except Exception as e:
            self.errors.append({
                'step': step_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            self.logger.error(
                f"Error in {step_id}",
                error=str(e),
                traceback=traceback.format_exc()
            )
            self.logger.metric_counter('errors_count').add(1)
            raise

    def snapshot(self, name: str, data: Any):
        """
        Salva uno snapshot dei dati per analisi.
        
        Args:
            name: Nome dello snapshot
            data: Dati da salvare
        """
        if not self.enabled:
            return
            
        self.data_snapshots[name] = data
        if self.verbose:
            self.logger.info(
                f"Data snapshot: {name}",
                data=pformat(data, indent=2)
            )

    def print_summary(self):
        """Stampa un riepilogo dell'esecuzione."""
        if not self.enabled:
            return
            
        print("\n" + "="*50)
        print("CRAWLER DEBUG SUMMARY")
        print("="*50)
        
        print("\nStep Timings:")
        for step, duration in self.timings.items():
            print(f"{step}: {duration:.2f}s")
            
        if self.errors:
            print("\nErrors Encountered:")
            for error in self.errors:
                print(f"\nIn {error['step']}:")
                print(f"Error: {error['error']}")
                if self.verbose:
                    print("Traceback:")
                    print(error['traceback'])
                    
        if self.verbose and self.data_snapshots:
            print("\nData Snapshots:")
            for name, data in self.data_snapshots.items():
                print(f"\n{name}:")
                print(pformat(data, indent=2))

    async def debug_strategy(self, strategy_func):
        """
        Decorator per debuggare una strategia di crawling.
        
        Args:
            strategy_func: Funzione della strategia da debuggare
        """
        @wraps(strategy_func)
        async def wrapper(*args, **kwargs):
            if not self.enabled:
                return await strategy_func(*args, **kwargs)
                
            with self.step(f"Strategy: {strategy_func.__name__}", kwargs):
                frontier_url = kwargs.get('frontier_url')
                if frontier_url:
                    self.snapshot("Input URL", {
                        'url': str(frontier_url.url),
                        'type': frontier_url.url_type.name,
                        'depth': frontier_url.depth,
                        'max_depth': frontier_url.max_depth,
                        'patterns': {
                            'target': frontier_url.target_patterns,
                            'seed': frontier_url.seed_pattern
                        }
                    })
                
                try:
                    # Pre-execution snapshot
                    with self.step("Pre-processing"):
                        self.snapshot("Strategy Arguments", {
                            'args': args,
                            'kwargs': kwargs
                        })
                    
                    # Execute strategy
                    results = await strategy_func(*args, **kwargs)
                    
                    # Post-execution snapshot
                    with self.step("Post-processing"):
                        if results:
                            self.snapshot("Results", {
                                'count': len(results),
                                'targets': len([u for u in results if u.is_target]),
                                'seeds': len([u for u in results if not u.is_target]),
                                'urls': [str(u.url) for u in results]
                            })
                    
                    return results
                    
                except Exception as e:
                    self.logger.error(
                        "Strategy execution failed",
                        strategy=strategy_func.__name__,
                        error=str(e)
                    )
                    raise
                    
        return wrapper

async def test_strategy(frontier_url: FrontierUrl) -> List[FrontierUrl]:
    """Test una specifica strategia di crawling."""
    crawler = Crawler(
        scrapegraph_api_key=settings.scrapegraph_api_key,
        max_concurrent_pages=settings.crawler.max_concurrent_pages,
        batch_size=settings.crawler.batch_size
    )
    
    # Usa il context manager del crawler per gestire il browser
    async with crawler._get_browser_context() as context:
        page = await context.new_page()
        
        try:
            # Seleziona la strategia appropriata
            strategy_map = {
                UrlType.DIRECT_TARGET: Type0Strategy,
                UrlType.SINGLE_PAGE: Type1Strategy,
                UrlType.SEED_TARGET: Type2Strategy,
                UrlType.COMPLEX_AI: Type3Strategy,
                UrlType.FULL_AI: Type4Strategy
            }
            
            strategy_class = strategy_map[frontier_url.url_type]
            
            # Inizializza la strategia
            strategy = strategy_class(
                frontier_crud=None,
                playwright_page=page,
                scrapegraph_api_key=crawler.scrapegraph_api_key
            )
            
            # Esegui la strategia
            results = await strategy.execute(frontier_url)
            
            return results
            
        finally:
            await page.close()

# Helper per il debugger
debugger = CrawlerDebugger(enabled=True, verbose=True)

async def debug_url_from_config(category_name: str, url_index: int = 0) -> List[FrontierUrl]:
    """Versione debug di test_url_from_config."""
    with debugger.step("URL Test Initialization"):
        # Ottieni la categoria dal crawler_config
        categories = settings.crawler_config.categories
        category = next(
            (cat for cat in categories 
             if cat.name == category_name),
            None
        )
        
        debugger.snapshot("Selected Category", {
            'name': category_name,
            'category': category.model_dump() if category else None
        })
        
        if not category:
            raise ValueError(f"Category {category_name} not found")
        
        # Create FrontierUrl
        url_config = category.urls[url_index]
        frontier_url = FrontierUrl(
            url=url_config.url,
            category=category_name,
            url_type=UrlType(url_config.type),
            max_depth=url_config.max_depth,
            target_patterns=url_config.target_patterns,
            seed_pattern=url_config.seed_pattern
        )
        
        debugger.snapshot("Created FrontierUrl", frontier_url.model_dump())
    
    # Esegui il test con debug
    with debugger.step("Strategy Execution"):
        results = await test_strategy(frontier_url)
        debugger.snapshot("Strategy Results", {
            'total_urls': len(results),
            'targets': len([u for u in results if u.is_target]),
            'seeds': len([u for u in results if not u.is_target])
        })
        
    return results