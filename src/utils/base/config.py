"""
Standardized configuration management for scrapers.

This module provides the ScraperConfig class to replace hardcoded global variables
found in every scraper. It centralizes configuration management and provides
computed properties for common patterns.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ScraperConfig:
    """
    Standardized configuration for all scrapers.
    
    This class replaces the hardcoded global variables found in every scraper:
    - COUNTRY, JURISDICTION, CORPUS
    - TABLE_NAME, BASE_URL, TOC_URL
    - SKIP_TITLE, RESERVED_KEYWORDS, etc.
    """
    country: str
    jurisdiction: str
    corpus: str
    base_url: str
    toc_url: str
    skip_title: int = 0
    reserved_keywords: List[str] = field(default_factory=lambda: ["REPEALED", "RESERVED"])
    delay_seconds: float = 1.0  # 🔍 DELAY DEBUGGING: Default delay setting
    debug_mode: bool = False
    max_retries: int = 3
    timeout_seconds: int = 30
    
    @property
    def table_name(self) -> str:
        """Generate table name from country, jurisdiction, and corpus."""
        return f"{self.country}_{self.jurisdiction}_{self.corpus}"
    
    @property  
    def corpus_id(self) -> str:
        """Generate corpus ID for NodeID hierarchy."""
        return f"{self.country}/{self.jurisdiction}/{self.corpus}"
    
    @property
    def display_name(self) -> str:
        """Generate human-readable display name."""
        return f"{self.jurisdiction.upper()} {self.corpus.title()}"
    
    def validate(self) -> List[str]:
        """
        Validate configuration parameters.
        
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.country:
            errors.append("Country is required")
        if not self.jurisdiction:
            errors.append("Jurisdiction is required")
        if not self.corpus:
            errors.append("Corpus is required")
        if not self.base_url:
            errors.append("Base URL is required")
        if not self.toc_url:
            errors.append("Table of Contents URL is required")
        
        # 🔍 DELAY DEBUGGING: Validate delay setting
        if self.delay_seconds < 0:
            errors.append("Delay seconds must be non-negative")
        elif self.delay_seconds == 0:
            # This is actually good for performance!
            pass
        elif self.delay_seconds > 0:
            # This will slow down scraping
            pass
        if self.max_retries < 1:
            errors.append("Max retries must be at least 1")
        if self.timeout_seconds < 1:
            errors.append("Timeout seconds must be at least 1")
            
        return errors


class ConfigManager:
    """Factory for creating standard scraper configurations."""
    
    @staticmethod
    def create_custom_config(
        country: str,
        jurisdiction: str,
        corpus: str,
        base_url: str,
        toc_url: str,
        **kwargs
    ) -> ScraperConfig:
        """
        Create a custom configuration for new scrapers.
        
        Args:
            country: Country code (e.g., 'us', 'ca', 'uk')
            jurisdiction: Jurisdiction code (e.g., 'az', 'ca', 'federal')
            corpus: Corpus type (e.g., 'statutes', 'regulations', 'cases')
            base_url: Base URL for the jurisdiction's legal site
            toc_url: URL for the table of contents/main index
            **kwargs: Additional configuration parameters
            
        Returns:
            ScraperConfig: Configured scraper instance
        """
        return ScraperConfig(
            country=country,
            jurisdiction=jurisdiction,
            corpus=corpus,
            base_url=base_url,
            toc_url=toc_url,
            **kwargs
        )