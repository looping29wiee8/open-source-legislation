"""
Standardized web fetching utilities for open-source-legislation.

This module provides unified web fetching capabilities with retry logic,
rate limiting, and error handling, replacing the inconsistent approaches
found across scrapers.

Key features:
- Standardized retry logic with exponential backoff
- Configurable rate limiting and delays
- Session management for performance
- BeautifulSoup integration
- Selenium support for JavaScript-heavy sites
- Request/response logging and monitoring
"""

import time
import logging
from typing import Optional, Dict, Any, Union, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


class WebFetcher:
    """
    Standardized web fetching with retry logic and rate limiting.
    
    This replaces the different approaches to web fetching found across scrapers:
    
    Basic approach (many scrapers):
    ```python
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    ```
    
    Advanced approach (scrapingHelpers.py):
    ```python
    @retry(retry=retry_if_exception_type(HTTPError), wait=wait_exponential(multiplier=1, max=60))
    def get_url_as_soup(url: str, delay_time: Optional[int] = None) -> BeautifulSoup:
        headers = {'User-Agent': 'Mozilla/5.0...'}
        response = requests.get(url, headers=headers)
        # ... error handling
    ```
    """
    
    def __init__(
        self, 
        delay_seconds: float = 1.0, 
        max_retries: int = 3,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize WebFetcher with configuration.
        
        Args:
            delay_seconds: Default delay between requests (rate limiting)
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            user_agent: Custom User-Agent string
            custom_headers: Additional headers to include in requests
        """
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Set up session with retry strategy
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,  # Exponential backoff
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set up headers
        if user_agent is None:
            user_agent = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        if custom_headers:
            headers.update(custom_headers)
            
        self.session.headers.update(headers)
        
        # Request statistics
        self.stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_delay_time': 0.0
        }
        
    def get_soup(
        self, 
        url: str, 
        delay: Optional[float] = None,
        parser: str = 'html.parser',
        encoding: Optional[str] = None
    ) -> BeautifulSoup:
        """
        Fetch URL and return BeautifulSoup object with standardized error handling.
        
        This is the primary method that replaces get_url_as_soup() and other
        ad-hoc fetching approaches found across scrapers.
        
        Args:
            url: URL to fetch
            delay: Optional delay override for this request
            parser: BeautifulSoup parser to use
            encoding: Optional response encoding override
            
        Returns:
            BeautifulSoup: Parsed HTML content
            
        Raises:
            WebFetchError: If request fails after all retry attempts
            
        Example:
            ```python
            fetcher = WebFetcher(delay_seconds=1.5, max_retries=5)
            soup = fetcher.get_soup("https://example.gov/statutes")
            
            # With custom delay for this request
            soup = fetcher.get_soup(url, delay=3.0)
            ```
        """
        # Apply rate limiting
        delay_time = delay if delay is not None else self.delay_seconds
        if delay_time > 0:
            self.logger.debug(f"Applying rate limit delay: {delay_time}s")
            time.sleep(delay_time)
            self.stats['total_delay_time'] += delay_time
        
        self.stats['requests_made'] += 1
        
        try:
            self.logger.debug(f"Fetching URL: {url}")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Set encoding if specified
            if encoding:
                response.encoding = encoding
            elif response.encoding is None:
                response.encoding = 'utf-8'
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, parser)
            
            self.stats['successful_requests'] += 1
            self.logger.debug(f"Successfully fetched {url} ({len(response.text)} characters)")
            
            return soup
            
        except requests.exceptions.RequestException as e:
            self.stats['failed_requests'] += 1
            error_msg = f"Failed to fetch {url} after {self.max_retries} attempts: {e}"
            self.logger.error(error_msg)
            raise WebFetchError(error_msg) from e
    
    def get_raw_response(
        self, 
        url: str, 
        delay: Optional[float] = None,
        **kwargs
    ) -> requests.Response:
        """
        Get raw response object for advanced processing.
        
        Args:
            url: URL to fetch
            delay: Optional delay override
            **kwargs: Additional arguments to pass to requests.get()
            
        Returns:
            requests.Response: Raw response object
        """
        delay_time = delay if delay is not None else self.delay_seconds
        if delay_time > 0:
            time.sleep(delay_time)
            self.stats['total_delay_time'] += delay_time
        
        self.stats['requests_made'] += 1
        
        try:
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            self.stats['successful_requests'] += 1
            return response
            
        except requests.exceptions.RequestException as e:
            self.stats['failed_requests'] += 1
            raise WebFetchError(f"Failed to fetch {url}: {e}") from e
    
    def post_data(
        self, 
        url: str, 
        data: Dict[str, Any],
        delay: Optional[float] = None,
        **kwargs
    ) -> requests.Response:
        """
        POST data to URL with same retry/rate limiting logic.
        
        Args:
            url: URL to POST to
            data: Data to POST
            delay: Optional delay override
            **kwargs: Additional arguments to pass to requests.post()
            
        Returns:
            requests.Response: Response object
        """
        delay_time = delay if delay is not None else self.delay_seconds
        if delay_time > 0:
            time.sleep(delay_time)
            self.stats['total_delay_time'] += delay_time
        
        self.stats['requests_made'] += 1
        
        try:
            response = self.session.post(url, data=data, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            self.stats['successful_requests'] += 1
            return response
            
        except requests.exceptions.RequestException as e:
            self.stats['failed_requests'] += 1
            raise WebFetchError(f"Failed to POST to {url}: {e}") from e
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get fetching statistics.
        
        Returns:
            Dict[str, Any]: Statistics about requests made
        """
        return {
            **self.stats,
            'success_rate': (
                self.stats['successful_requests'] / max(self.stats['requests_made'], 1)
            ),
            'average_delay': (
                self.stats['total_delay_time'] / max(self.stats['requests_made'], 1)
            )
        }
    
    def reset_stats(self) -> None:
        """Reset request statistics."""
        self.stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_delay_time': 0.0
        }


class SeleniumWebFetcher:
    """
    Selenium-based web fetcher for JavaScript-heavy sites.
    
    This provides a standardized way to use Selenium for sites that require
    JavaScript execution, replacing ad-hoc Selenium usage across scrapers.
    """
    
    def __init__(
        self,
        headless: bool = True,
        delay_seconds: float = 2.0,
        page_timeout: int = 30,
        implicit_wait: int = 10,
        custom_options: Optional[List[str]] = None
    ):
        """
        Initialize Selenium web fetcher.
        
        Args:
            headless: Whether to run browser in headless mode
            delay_seconds: Default delay between requests
            page_timeout: Page load timeout in seconds
            implicit_wait: Implicit wait time for elements
            custom_options: Additional Chrome options
        """
        self.headless = headless
        self.delay_seconds = delay_seconds
        self.page_timeout = page_timeout
        self.implicit_wait = implicit_wait
        self.custom_options = custom_options or []
        self.logger = logging.getLogger(__name__)
        
        self.driver = None
        self._setup_driver()
        
    def _setup_driver(self) -> None:
        """Set up Chrome WebDriver with standardized options."""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        # Standard options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # Faster loading
        
        # Add custom options
        for option in self.custom_options:
            options.add_argument(option)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.page_timeout)
            self.driver.implicitly_wait(self.implicit_wait)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            raise WebFetchError(f"Selenium initialization failed: {e}") from e
    
    def get_soup(
        self, 
        url: str, 
        wait_for_element: Optional[str] = None,
        delay: Optional[float] = None
    ) -> BeautifulSoup:
        """
        Fetch URL using Selenium and return BeautifulSoup object.
        
        Args:
            url: URL to fetch
            wait_for_element: CSS selector to wait for before returning
            delay: Optional delay override
            
        Returns:
            BeautifulSoup: Parsed HTML content after JavaScript execution
        """
        if not self.driver:
            raise WebFetchError("Selenium driver not initialized")
        
        delay_time = delay if delay is not None else self.delay_seconds
        if delay_time > 0:
            time.sleep(delay_time)
        
        try:
            self.logger.debug(f"Fetching URL with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for specific element if specified
            if wait_for_element:
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element)))
            
            # Get page source and parse
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            self.logger.debug(f"Successfully fetched {url} with Selenium")
            return soup
            
        except (TimeoutException, WebDriverException) as e:
            error_msg = f"Selenium failed to fetch {url}: {e}"
            self.logger.error(error_msg)
            raise WebFetchError(error_msg) from e
    
    def click_and_wait(
        self, 
        selector: str, 
        wait_for_element: Optional[str] = None,
        timeout: int = 10
    ) -> None:
        """
        Click element and optionally wait for another element to appear.
        
        Args:
            selector: CSS selector for element to click
            wait_for_element: CSS selector to wait for after clicking
            timeout: Wait timeout in seconds
        """
        if not self.driver:
            raise WebFetchError("Selenium driver not initialized")
        
        try:
            # Find and click element
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            
            # Wait for result element if specified
            if wait_for_element:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                )
                
        except (TimeoutException, WebDriverException) as e:
            raise WebFetchError(f"Failed to click {selector}: {e}") from e
    
    def fill_form(self, form_data: Dict[str, str]) -> None:
        """
        Fill form fields with data.
        
        Args:
            form_data: Dictionary mapping CSS selectors to values
        """
        if not self.driver:
            raise WebFetchError("Selenium driver not initialized")
        
        try:
            for selector, value in form_data.items():
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                element.clear()
                element.send_keys(value)
                
        except (TimeoutException, WebDriverException) as e:
            raise WebFetchError(f"Failed to fill form: {e}") from e
    
    def execute_script(self, script: str) -> Any:
        """
        Execute JavaScript and return result.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Any: Result of JavaScript execution
        """
        if not self.driver:
            raise WebFetchError("Selenium driver not initialized")
        
        try:
            return self.driver.execute_script(script)
        except WebDriverException as e:
            raise WebFetchError(f"JavaScript execution failed: {e}") from e
    
    def cleanup(self) -> None:
        """Clean up Selenium driver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.warning(f"Error during driver cleanup: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class WebFetchError(Exception):
    """Custom exception for web fetching failures."""
    pass


class RateLimiter:
    """
    Utility class for advanced rate limiting strategies.
    
    Provides more sophisticated rate limiting than simple delays,
    useful for scrapers that need to be very respectful of servers.
    """
    
    def __init__(self, requests_per_minute: int = 30):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.request_times = []
        
    def wait_if_needed(self) -> None:
        """Wait if necessary to stay within rate limits."""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Check if we need to wait
        if len(self.request_times) >= self.requests_per_minute:
            oldest_request = min(self.request_times)
            wait_time = 60 - (now - oldest_request)
            if wait_time > 0:
                time.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)


class WebFetcherFactory:
    """
    Factory for creating configured WebFetcher instances for specific jurisdictions.
    
    This provides pre-configured fetchers optimized for known jurisdictions.
    """
    
    @staticmethod
    def create_arizona_fetcher() -> WebFetcher:
        """Create WebFetcher optimized for Arizona state websites."""
        return WebFetcher(
            delay_seconds=1.0,  # Arizona is generally responsive
            max_retries=3,
            timeout=30,
            custom_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
    
    @staticmethod
    def create_federal_fetcher() -> WebFetcher:
        """Create WebFetcher optimized for federal websites."""
        return WebFetcher(
            delay_seconds=2.0,  # Be more conservative with federal sites
            max_retries=5,
            timeout=45
        )
    
    @staticmethod
    def create_california_fetcher() -> WebFetcher:
        """Create WebFetcher optimized for California websites."""
        return WebFetcher(
            delay_seconds=1.5,
            max_retries=4,
            timeout=40
        )
    
    @staticmethod
    def create_selenium_fetcher(jurisdiction: str) -> SeleniumWebFetcher:
        """Create SeleniumWebFetcher optimized for specific jurisdiction."""
        config = {
            "arizona": {"delay_seconds": 2.0, "headless": True},
            "california": {"delay_seconds": 3.0, "headless": True},
            "federal": {"delay_seconds": 4.0, "headless": True},
        }
        
        settings = config.get(jurisdiction, {"delay_seconds": 2.0, "headless": True})
        return SeleniumWebFetcher(**settings)