"""
Processing utilities for open-source-legislation.

This module provides standardized processing utilities including:
- Database management and operations
- Text processing and cleaning
- Web fetching and scraping utilities

Key components:
- DatabaseManager: Unified database operations with secure credential management
- TextProcessor: Standardized text cleaning and extraction
- WebFetcher: Rate-limited web fetching with retry logic
- SeleniumWebFetcher: JavaScript-heavy site support
"""

from .database import DatabaseManager, DatabaseError
from .text import TextProcessor, TextAnalyzer
from .web import WebFetcher, SeleniumWebFetcher, WebFetchError, WebFetcherFactory

__all__ = [
    'DatabaseManager', 
    'DatabaseError',
    'TextProcessor',
    'TextAnalyzer', 
    'WebFetcher',
    'SeleniumWebFetcher',
    'WebFetchError',
    'WebFetcherFactory'
]