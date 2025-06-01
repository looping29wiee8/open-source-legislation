"""
Base utilities for open-source-legislation scrapers.

This module provides foundational utilities that eliminate code duplication
across all scrapers, particularly the path setup logic that was repeated
in every scraper file.
"""

import os
import sys
from pathlib import Path


def setup_project_path():
    """
    Handle project path setup for all scrapers.
    
    This function replaces the 20+ lines of path setup code that was
    duplicated in every scraper file. It ensures the project root is
    in the Python path so that imports work correctly.
    
    The original duplicated code in every scraper:
    ```python
    import os
    import sys
    from pathlib import Path
    DIR = os.path.dirname(os.path.realpath(__file__))
    current_file = Path(__file__).resolve()
    src_directory = current_file.parent
    while src_directory.name != 'src' and src_directory.parent != src_directory:
        src_directory = src_directory.parent
    project_root = src_directory.parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    ```
    
    Now scrapers only need:
    ```python
    from src.utils.base import setup_project_path
    setup_project_path()
    ```
    """
    # Get the current file's directory (this __init__.py file)
    current_file = Path(__file__).resolve()
    
    # Navigate up to find the 'src' directory
    src_directory = current_file.parent
    while src_directory.name != 'src' and src_directory.parent != src_directory:
        src_directory = src_directory.parent
    
    # Project root is the parent of 'src'
    project_root = src_directory.parent
    
    # Add project root to Python path if not already present
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))


def get_scraper_directory(scraper_file_path: str) -> str:
    """
    Get the directory containing the scraper file.
    
    This replaces the common pattern:
    DIR = os.path.dirname(os.path.realpath(__file__))
    
    Args:
        scraper_file_path: __file__ from the calling scraper
        
    Returns:
        str: Absolute path to the scraper's directory
    """
    return os.path.dirname(os.path.realpath(scraper_file_path))


# Convenience imports for scrapers
from .credentials import CredentialManager
from .config import ScraperConfig, ConfigManager
from .scraper import BaseScraper, SeleniumScraper

__all__ = [
    'setup_project_path',
    'get_scraper_directory', 
    'CredentialManager',
    'ScraperConfig',
    'ConfigManager',
    'BaseScraper',
    'SeleniumScraper'
]