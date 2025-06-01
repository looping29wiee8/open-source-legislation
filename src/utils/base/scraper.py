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
from pathlib import Path

# Import existing utilities - these will be gradually migrated
from src.utils import utilityFunctions as util
from src.utils.scrapingHelpers import insert_jurisdiction_and_corpus_node
from src.utils.pydanticModels import Node, NodeID

# Import new standardized utilities
from .config import ScraperConfig
from .credentials import CredentialManager
from src.utils.processing import DatabaseManager
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
    
    def __init__(self, config: ScraperConfig, user: Optional[str] = None):
        """
        Initialize the base scraper with configuration and user credentials.
        
        Args:
            config: ScraperConfig instance with jurisdiction-specific settings
            user: Optional database user (if None, will use CredentialManager)
        """
        self.config = config
        
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
        
        # Initialize database management
        self.db = DatabaseManager(config.table_name, self.user)
        
        self.logger.info(f"Initialized {config.display_name} scraper")
        
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
        
    def scrape(self) -> None:
        """
        Template method for the complete scraping process.
        
        This method provides the standardized framework while delegating
        the actual scraping logic to the jurisdiction-specific implementation.
        """
        try:
            self.logger.info(f"Starting scrape for {self.config.table_name}")
            
            # Set up the corpus node structure
            corpus_node = self.setup_corpus()
            self.logger.info(f"Created corpus node: {corpus_node.node_id}")
            
            # Delegate to jurisdiction-specific implementation
            self.scrape_implementation()
            
            self.logger.info("Scraping completed successfully")
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}", exc_info=True)
            raise
            
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
        return self.db.insert_node(
            node, 
            ignore_duplicate=ignore_duplicate, 
            debug=self.config.debug_mode
        )
    
    def create_structure_node(self, **kwargs) -> Node:
        """Helper for standardized Node creation."""
        return NodeFactory.create_structure_node(**kwargs)
        
    def create_content_node(self, **kwargs) -> Node:
        """Helper for standardized content Node creation."""
        return NodeFactory.create_content_node(**kwargs)
    
    def batch_insert_nodes(self, nodes: list[Node], ignore_duplicates: bool = True) -> list[Node]:
        """Helper for batch node insertion."""
        return self.db.batch_insert(
            nodes, 
            ignore_duplicates=ignore_duplicates,
            debug=self.config.debug_mode
        )
                
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


class SeleniumScraper(BaseScraper):
    """
    Specialized base class for scrapers that need Selenium.
    
    This extends BaseScraper with Selenium-specific utilities while
    maintaining the same flexibility for parsing logic.
    """
    
    def __init__(self, config: ScraperConfig, user: Optional[str] = None, 
                 selenium_config: Optional[Dict[str, Any]] = None):
        """
        Initialize Selenium scraper.
        
        Args:
            config: ScraperConfig instance
            user: Optional database user
            selenium_config: Optional Selenium configuration (headless, etc.)
        """
        super().__init__(config, user)
        
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