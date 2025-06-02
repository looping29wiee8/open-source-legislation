"""
Base scraper framework for open-source-legislation.

This module provides the BaseScraper class that standardizes infrastructure
while preserving complete flexibility for jurisdiction-specific parsing logic.
The design uses composition over inheritance to allow scrapers to maintain
their hard-won parsing logic while benefiting from standardized infrastructure.
"""

from abc import ABC, abstractmethod
import logging
from typing import Optional, Dict, Any
import sys
import signal
import time
import threading
import platform
from pathlib import Path

# Import existing utilities - these will be gradually migrated
from src.utils import utilityFunctions as util
from src.utils.scrapingHelpers import insert_jurisdiction_and_corpus_node
from src.utils.pydanticModels import Node, NodeID

# Import new standardized utilities
from .config import ScraperConfig
from .credentials import CredentialManager
from src.utils.processing import DatabaseManager
from src.utils.processing.database import ScrapingMode
from src.utils.data import NodeFactory


class BaseScraper(ABC):
    """
    Base class providing standardized infrastructure for all scrapers.
    
    This class follows the composition pattern - it provides infrastructure
    (logging, configuration, database access) while allowing complete flexibility
    in parsing logic through the abstract scrape_implementation method.
    
    Key features:
    - Standardized logging setup
    - Secure credential management
    - Configuration management
    - Database abstraction layer
    - Error handling framework
    - NO assumptions about web fetching or parsing logic
    """
    
    def __init__(self, config: ScraperConfig, user: Optional[str] = None, 
                 mode: ScrapingMode = ScrapingMode.RESUME, skip_title: Optional[int] = None,
                 timeout_minutes: Optional[int] = None, max_titles: Optional[int] = None,
                 max_nodes: Optional[int] = None, validation_mode: bool = False):
        """
        Initialize the base scraper with configuration and user credentials.
        
        Args:
            config: ScraperConfig instance with jurisdiction-specific settings
            user: Optional database user (if None, will use CredentialManager)
            mode: Scraping mode (resume, clean, skip)
            skip_title: Optional title number to skip to (overrides mode for SKIP)
            timeout_minutes: Optional timeout in minutes for debugging/validation
            max_titles: Optional maximum number of titles to process (for validation)
            max_nodes: Optional maximum number of nodes to create (for validation)
            validation_mode: Enable validation mode (automatically sets limits)
        """
        self.config = config
        self.mode = mode
        self.skip_title = skip_title
        self.timeout_minutes = timeout_minutes
        self.max_titles = max_titles
        self.max_nodes = max_nodes
        self.validation_mode = validation_mode
        self.start_time = None
        
        # Set validation mode defaults
        if validation_mode:
            self.timeout_minutes = self.timeout_minutes or 2  # 2 minutes for validation
            self.max_titles = self.max_titles or 3  # Process max 3 titles
            self.max_nodes = self.max_nodes or 100  # Create max 100 nodes
            
        # Timeout management
        self._timeout_timer = None
        self._should_stop = False
        self._stop_reason = None
        
        # Progress tracking for stopping conditions
        self._processed_titles = 0
        self._created_nodes = 0
        
        # Validate configuration
        config_errors = config.validate()
        if config_errors:
            raise ValueError(f"Invalid configuration: {config_errors}")
        
        # Get user credentials securely
        if user is None:
            self.user = CredentialManager.get_database_user()
        else:
            self.user = user
            
        # Set up logging
        self.logger = self._setup_logger()
        
        # Initialize database management with mode
        self.db = DatabaseManager(config.table_name, self.user, mode)
        
        # Determine starting point based on mode and skip_title
        self._determine_starting_point()
        
        self.logger.info(f"Initialized {config.display_name} scraper in {mode.value} mode")
        
    def _setup_logger(self) -> logging.Logger:
        """Set up standardized logging for the scraper."""
        logger_name = f"{self.config.country}_{self.config.jurisdiction}_{self.config.corpus}"
        logger = logging.getLogger(logger_name)
        
        # Only add handler if logger doesn't already have one
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        logger.setLevel(logging.DEBUG if self.config.debug_mode else logging.INFO)
        return logger
    
    def _determine_starting_point(self) -> None:
        """
        Determine where to start scraping based on mode and skip_title.
        
        This intelligently sets config.skip_title based on:
        - CLEAN mode: Start from 0
        - RESUME mode: Auto-detect from database
        - SKIP mode: Use provided skip_title
        """
        if self.mode == ScrapingMode.CLEAN:
            self.config.skip_title = 0
            self.logger.info("CLEAN mode: Starting from title 0")
            
        elif self.mode == ScrapingMode.RESUME:
            if self.skip_title is not None:
                self.config.skip_title = self.skip_title
                self.logger.info(f"RESUME mode with manual override: Starting from title {self.skip_title}")
            else:
                # Auto-detect resume point
                resume_point = self.db.get_resume_point()
                self.config.skip_title = resume_point or 0
                if resume_point:
                    self.logger.info(f"RESUME mode: Auto-detected resume point at title {resume_point}")
                else:
                    self.logger.info("RESUME mode: No existing data found, starting from title 0")
                    
        elif self.mode == ScrapingMode.SKIP:
            if self.skip_title is not None:
                self.config.skip_title = self.skip_title
                self.logger.info(f"SKIP mode: Starting from title {self.skip_title}")
            else:
                raise ValueError("SKIP mode requires skip_title parameter")
    
    def _setup_timeout(self) -> None:
        """Set up cross-platform timeout for debugging/validation runs."""
        if not self.timeout_minutes:
            return
            
        def timeout_handler():
            self._should_stop = True
            self._stop_reason = f"timeout after {self.timeout_minutes} minutes"
            
        self._timeout_timer = threading.Timer(
            self.timeout_minutes * 60,  # Convert minutes to seconds
            timeout_handler
        )
        self._timeout_timer.daemon = True
        self._timeout_timer.start()
        
    def _cleanup_timeout(self) -> None:
        """Clean up timeout timer."""
        if self._timeout_timer:
            self._timeout_timer.cancel()
            self._timeout_timer = None
            
    def should_continue(self) -> bool:
        """
        Check if scraper should continue based on all stopping conditions.
        
        Returns:
            bool: True if should continue, False if should stop
        """
        # Check timeout condition
        if self._should_stop:
            return False
            
        # Check title limit
        if self.max_titles and self._processed_titles >= self.max_titles:
            self._should_stop = True
            self._stop_reason = f"processed {self.max_titles} titles (limit reached)"
            return False
            
        # Check node limit
        if self.max_nodes and self._created_nodes >= self.max_nodes:
            self._should_stop = True
            self._stop_reason = f"created {self.max_nodes} nodes (limit reached)"
            return False
            
        return True
        
    def increment_title_count(self) -> None:
        """Track title processing for stopping conditions."""
        self._processed_titles += 1
        
    def increment_node_count(self, count: int = 1) -> None:
        """Track node creation for stopping conditions."""
        self._created_nodes += count
        
    def scrape(self) -> None:
        """
        Template method for the complete scraping process.
        
        This method provides the standardized framework while delegating
        the actual scraping logic to the jurisdiction-specific implementation.
        """
        # Set up timeout if specified
        self._setup_timeout()
            
        try:
            self.start_time = time.time()
            self.logger.info(f"Starting scrape for {self.config.table_name}")
            
            # Log stopping conditions
            conditions = []
            if self.timeout_minutes:
                conditions.append(f"timeout: {self.timeout_minutes} min")
            if self.max_titles:
                conditions.append(f"max titles: {self.max_titles}")
            if self.max_nodes:
                conditions.append(f"max nodes: {self.max_nodes}")
            if self.validation_mode:
                conditions.append("validation mode")
                
            if conditions:
                self.logger.info(f"Stopping conditions: {', '.join(conditions)}")
            
            # Set up the corpus node structure
            corpus_node = self.setup_corpus()
            self.logger.info(f"Created corpus node: {corpus_node.node_id}")
            
            # Delegate to jurisdiction-specific implementation
            self.scrape_implementation()
            
            if self._should_stop:
                self.logger.info(f"🛑 SCRAPING STOPPED: {self._stop_reason}")
                self._log_partial_results()
            else:
                self.logger.info("✅ Scraping completed successfully")
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}", exc_info=True)
            raise
        finally:
            # Clean up timeout
            self._cleanup_timeout()
            
    def _log_partial_results(self) -> None:
        """Log statistics about partial results when scraping stops early."""
        elapsed = (time.time() - self.start_time) / 60 if self.start_time else 0
        
        self.logger.info("=== PARTIAL RESULTS SUMMARY ===")
        self.logger.info(f"Elapsed time: {elapsed:.1f} minutes")
        self.logger.info(f"Titles processed: {self._processed_titles}")
        self.logger.info(f"Nodes created: {self._created_nodes}")
        
        if self.validation_mode:
            self.logger.info("This is normal for validation mode - use data for health checks")
        else:
            self.logger.info("Partial results available in database for analysis")
            
    def setup_corpus(self) -> Node:
        """
        Set up jurisdiction and corpus nodes in the database.
        
        This creates the base hierarchy that all scrapers need:
        - Country level (e.g., "us")
        - Jurisdiction level (e.g., "us/az") 
        - Corpus level (e.g., "us/az/statutes")
        
        Returns:
            Node: The corpus node that was created
        """
        self.logger.info(f"Setting up corpus for {self.config.corpus_id}")
        
        corpus_node = insert_jurisdiction_and_corpus_node(
            self.config.country,
            self.config.jurisdiction, 
            self.config.corpus
        )
        
        return corpus_node
        
    @abstractmethod
    def scrape_implementation(self) -> None:
        """
        Implement jurisdiction-specific scraping logic.
        
        This method has NO restrictions - jurisdictions can implement
        ANY logic they need here. The base class provides infrastructure
        but makes no assumptions about parsing approaches.
        
        Scrapers can:
        - Use any web fetching method (requests, selenium, etc.)
        - Implement any parsing logic
        - Use any data structures
        - Handle errors in their own way
        - Use or ignore the helper methods provided
        """
        pass
        
    # Optional helper methods - scrapers can use or ignore these
    
    def insert_node_safely(self, node: Node, ignore_duplicate: bool = True) -> Node:
        """
        Helper method for standardized database operations.
        
        Args:
            node: Node to insert
            ignore_duplicate: Whether to ignore duplicate key errors
            
        Returns:
            Node: The inserted node (potentially with modified ID if duplicate)
        """
        inserted_node = self.db.insert_node(
            node, 
            ignore_duplicate=ignore_duplicate, 
            debug=self.config.debug_mode
        )
        
        # Track node creation for stopping conditions
        self.increment_node_count(1)
        
        return inserted_node
    
    def create_structure_node(self, **kwargs) -> Node:
        """Helper for standardized Node creation."""
        return NodeFactory.create_structure_node(**kwargs)
        
    def create_content_node(self, **kwargs) -> Node:
        """Helper for standardized content Node creation."""
        return NodeFactory.create_content_node(**kwargs)
    
    def batch_insert_nodes(self, nodes: list[Node], ignore_duplicates: bool = True) -> list[Node]:
        """Helper for batch node insertion."""
        inserted_nodes = self.db.batch_insert(
            nodes, 
            ignore_duplicates=ignore_duplicates,
            debug=self.config.debug_mode
        )
        
        # Track node creation for stopping conditions
        self.increment_node_count(len(inserted_nodes))
        
        return inserted_nodes
                
    def log_progress(self, message: str, level: str = "info") -> None:
        """
        Helper method for consistent progress logging.
        
        Args:
            message: Progress message to log
            level: Log level ('debug', 'info', 'warning', 'error')
        """
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message)
        
    def get_scraper_directory(self) -> str:
        """
        Get the directory containing the scraper file.
        
        Returns:
            str: Absolute path to the scraper's directory
        """
        # Get the caller's file path (the scraper that inherits from this)
        frame = sys._getframe(1)
        caller_file = frame.f_globals.get('__file__')
        if caller_file:
            return str(Path(caller_file).parent.absolute())
        else:
            raise RuntimeError("Could not determine scraper directory")
    
    def track_title_progress(self, title_index: int, title_url: str, metadata: Optional[Dict] = None) -> None:
        """
        Track progress for reliable resuming after interruptions.
        
        Args:
            title_index: Current title index being processed  
            title_url: URL being processed
            metadata: Optional additional metadata
        """
        self.db.track_progress(title_index, title_url, metadata)


class SeleniumScraper(BaseScraper):
    """
    Specialized base class for scrapers that need Selenium.
    
    This extends BaseScraper with Selenium-specific utilities while
    maintaining the same flexibility for parsing logic.
    """
    
    def __init__(self, config: ScraperConfig, user: Optional[str] = None, 
                 mode: ScrapingMode = ScrapingMode.RESUME, skip_title: Optional[int] = None,
                 timeout_minutes: Optional[int] = None, max_titles: Optional[int] = None,
                 max_nodes: Optional[int] = None, validation_mode: bool = False,
                 selenium_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Selenium scraper.
        
        Args:
            config: ScraperConfig instance
            user: Optional database user
            mode: Scraping mode (resume, clean, skip)
            skip_title: Optional title number to skip to
            timeout_minutes: Optional timeout in minutes for debugging/validation
            max_titles: Optional maximum number of titles to process (for validation)
            max_nodes: Optional maximum number of nodes to create (for validation)
            validation_mode: Enable validation mode (automatically sets limits)
            selenium_config: Optional Selenium configuration (headless, etc.)
        """
        super().__init__(config, user, mode, skip_title, timeout_minutes, max_titles, max_nodes, validation_mode)
        
        self.selenium_config = selenium_config or {"headless": True}
        self.driver = None  # Will be initialized when needed
        
        self.logger.info("Selenium scraper initialized")
        
    def init_driver(self):
        """Initialize Selenium WebDriver when needed."""
        if self.driver is None:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            if self.selenium_config.get("headless", True):
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(options=options)
            self.logger.info("Selenium WebDriver initialized")
            
    def cleanup_driver(self):
        """Clean up Selenium WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logger.info("Selenium WebDriver cleaned up")
            
    def __enter__(self):
        """Context manager entry."""
        self.init_driver()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup_driver()