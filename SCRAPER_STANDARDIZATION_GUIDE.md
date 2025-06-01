# Scraper Standardization Guide

This comprehensive guide consolidates all research and planning for standardizing the open-source-legislation scrapers. It serves as the definitive blueprint for implementing consistent patterns while preserving jurisdiction-specific parsing logic.

## Executive Summary

### Current State Analysis
After extensive analysis of 50+ scrapers across federal and state jurisdictions, we've identified critical issues requiring immediate attention:

**🚨 Critical Security Issues:**
- Hardcoded database credentials found in multiple files (`user = "will2"`)
- No secure credential management system

**📊 Code Quality Issues:**
- **70% code duplication** - Same 20+ line path setup repeated across all scrapers
- **3 different database insertion patterns** causing maintenance nightmare
- **Inconsistent error handling** - Bare `except:` statements throughout
- **Mixed text processing approaches** - From simple `.strip()` to complex cleaning

**🏗️ Architecture Problems:**
- No inheritance hierarchy or base classes
- Inconsistent Node creation patterns
- No standardized logging or configuration management
- Mixed approaches to web fetching and rate limiting

### Strategic Approach

**Key Insight:** These scrapers contain thousands of jurisdiction-specific quirks developed through extensive trial and error. Our standardization must preserve this hard-won parsing logic while establishing consistent infrastructure.

**Solution:** Use **composition over inheritance** - standardize infrastructure (database, logging, configuration, security) while maintaining complete flexibility for parsing logic.

## Research Findings

### 1. Current Utility Function Analysis

#### Existing Utils in `src/utils/`

**pydanticModels.py** - Core data models:
- `NodeID`: Hierarchical identifier system
- `Node`: Primary legislation model (structure/content types)  
- `NodeText`: Paragraph-based text content with reference tracking
- `DefinitionHub`: Legal term definitions with scope inheritance
- `ReferenceHub`: Cross-references between legislation nodes
- `Addendum`: Metadata and source information

**scrapingHelpers.py** - Web scraping utilities:
- `insert_jurisdiction_and_corpus_node()`: Creates base hierarchy
- `insert_node()`: Handles Node insertion with versioning  
- `get_url_as_soup()`: Web fetching with retry logic
- `selenium_elements_present()`: Selenium waiting conditions
- `get_text_clean()`: Text cleaning (duplicated across files)

**utilityFunctions.py** - Database operations:
- `pydantic_insert()`: Insert Pydantic models to database
- `pydantic_select()`: Query database returning Pydantic models
- `regular_select()`: Standard SQL queries
- `create_chat_completion()`: LLM API calls
- `create_embedding()`: Text embedding generation

**processingHelpers.py** - Batch processing:
- `generate_embedding_for_row()`: Creates embeddings for text
- `generate_embeddings_in_batch()`: Batch embedding processing
- `read_rows_sequentially()`: Database row reading
- `update_rows_in_batch()`: Batch database updates

### 2. Scraper Pattern Analysis

#### Path Setup Duplication
**Found in every scraper file (20+ lines):**
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

#### Global Variables Pattern
**Found in every scraper:**
```python
COUNTRY = "us"
JURISDICTION = "az"  # varies
CORPUS = "statutes"
TABLE_NAME = f"{COUNTRY}_{JURISDICTION}_{CORPUS}"
BASE_URL = "https://www.azleg.gov"  # varies
TOC_URL = "https://www.azleg.gov/arstitle/"  # varies
SKIP_TITLE = 38  # varies
RESERVED_KEYWORDS = ["REPEALED", "RESERVED"]  # varies
```

#### Main Function Inconsistencies
**Arizona Pattern:**
```python
def main():
    corpus_node = insert_jurisdiction_and_corpus_node(COUNTRY, JURISDICTION, CORPUS)
    with open(f"{DIR}/data/top_level_titles.txt","r") as read_file:
        for i, line in enumerate(read_file):
            if i < SKIP_TITLE:
                continue
            url = line.strip()
            scrape_per_title(url)
```

**California Pattern:**
```python
def main():
    corpus_node = insert_jurisdiction_and_corpus_node(COUNTRY, JURISDICTION, CORPUS)
    scrape_all_titles()
```

**eCFR Pattern:**
```python
def main():
    insert_jurisdiction_and_corpus_node()
    scrape_all_titles()
```

### 3. Database Operation Inconsistencies

**Three Different Patterns Found:**

1. **scrapingHelpers.insert_node()** (Arizona, Alabama):
   ```python
   insert_node(title_node, TABLE_NAME, True, True)  # Boolean flags unclear
   ```

2. **Direct util.pydantic_insert()** (eCFR):
   ```python
   util.pydantic_insert(TABLE_NAME, [node_instance], include=None, user=user)
   ```

3. **Manual SQL with cursors** (Florida):
   ```python
   connection = util.psql_connect(USER)
   cursor = connection.cursor()
   query = f"INSERT INTO {TABLE_NAME} (...) VALUES (...)"
   cursor.execute(query, values)
   ```

### 4. Text Processing Variations

**Arizona (Simple):**
```python
txt = p.get_text().strip()
```

**eCFR (Complex but sophisticated):**
```python
def get_text_clean(element, direct_children_only=False):
    text = element.get_text().replace('\xa0', ' ').replace('\r', ' ').replace('\n', '').strip()
    clean_text = re.sub('<.*?>', '', text)
    clean_text = clean_text.replace("—", "-").replace("–", "-")
    return clean_text
```

**California (Inconsistent):**
```python
text_to_add = p_tag.get_text().strip()
if(text_to_add == ""):
    continue
```

### 5. Node Creation Inconsistencies

**Arizona (Good pattern):**
```python
title_node = Node(
    id=title_node_id,
    link=url,
    top_level_title=top_level_title,
    node_type=node_type, 
    level_classifier=level_classifier,
    node_name=title_name,
    parent=parent,
    number=number
)
```

**California (Problematic ID handling):**
```python
node_id = f"{node_parent.node_id}"  # Should use NodeID class
new_partial_node.id = new_partial_node.id.add_level(
    new_partial_node.level_classifier, 
    new_partial_node.number
)
```

## Implementation Plan

### Phase 1: Foundation Infrastructure (Week 1)

#### 1.1 Security Framework - CRITICAL PRIORITY
**Problem:** Hardcoded credentials throughout codebase
**Solution:** Implement secure credential management

```python
# src/utils/base/credentials.py
import os
from typing import Optional

class CredentialManager:
    """Secure credential management."""
    
    @staticmethod
    def get_database_user() -> str:
        """Get database user from environment variables."""
        user = os.getenv('OSL_DB_USER')
        if not user:
            raise ValueError(
                "OSL_DB_USER environment variable not set. "
                "Please set it to your database username."
            )
        return user
        
    @staticmethod
    def get_database_config() -> dict:
        """Get complete database configuration."""
        required_vars = ['OSL_DB_USER', 'OSL_DB_PASSWORD', 'OSL_DB_HOST', 'OSL_DB_NAME']
        config = {}
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                raise ValueError(f"Required environment variable {var} not set")
            config[var.lower().replace('osl_db_', '')] = value
            
        return config
```

#### 1.2 Configuration Management
**Problem:** Hardcoded globals in every scraper
**Solution:** Standardized configuration class

```python
# src/utils/base/config.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ScraperConfig:
    """Standardized configuration for all scrapers."""
    country: str
    jurisdiction: str
    corpus: str
    base_url: str
    toc_url: str
    skip_title: int = 0
    reserved_keywords: List[str] = field(default_factory=lambda: ["REPEALED", "RESERVED"])
    delay_seconds: float = 1.0
    debug_mode: bool = False
    
    @property
    def table_name(self) -> str:
        return f"{self.country}_{self.jurisdiction}_{self.corpus}"
    
    @property  
    def corpus_id(self) -> str:
        return f"{self.country}/{self.jurisdiction}/{self.corpus}"
```

#### 1.3 Base Scraper Framework
**Problem:** No inheritance hierarchy, inconsistent main functions
**Solution:** Flexible base class using composition

```python
# src/utils/base/scraper.py
from abc import ABC, abstractmethod
import logging
from typing import Optional

class BaseScraper(ABC):
    """Base class providing standardized infrastructure only."""
    
    def __init__(self, config: ScraperConfig, user: str):
        self.config = config
        self.user = user
        self.db = DatabaseManager(config.table_name, user)
        self.logger = self._setup_logger()
        # NO assumptions about web fetching - scrapers choose their tools
        
    def _setup_logger(self) -> logging.Logger:
        """Standardized logging setup."""
        logger = logging.getLogger(f"{self.config.country}_{self.config.jurisdiction}")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG if self.config.debug_mode else logging.INFO)
        return logger
        
    def scrape(self) -> None:
        """Template method for scraping process."""
        try:
            self.logger.info(f"Starting scrape for {self.config.table_name}")
            corpus_node = self.setup_corpus()
            self.scrape_implementation()  # Jurisdiction implements ANY logic here
            self.logger.info("Scraping completed successfully")
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}", exc_info=True)
            raise
            
    def setup_corpus(self) -> Node:
        """Set up jurisdiction and corpus nodes."""
        return insert_jurisdiction_and_corpus_node(
            self.config.country,
            self.config.jurisdiction, 
            self.config.corpus
        )
        
    @abstractmethod
    def scrape_implementation(self) -> None:
        """Implement jurisdiction-specific logic - NO restrictions."""
        pass
        
    # Helper methods - optional to use
    def create_structure_node(self, **kwargs) -> Node:
        """Helper for standardized Node creation."""
        return NodeFactory.create_structure_node(**kwargs)
        
    def insert_node_safely(self, node: Node) -> Node:
        """Helper for standardized database operations."""
        return self.db.insert_node(node, ignore_duplicate=True, debug=self.config.debug_mode)
```

#### 1.4 Path Setup Utility
**Problem:** 20+ lines repeated in every file
**Solution:** Single utility function

```python
# src/utils/base/__init__.py
import os
import sys
from pathlib import Path

def setup_project_path():
    """Handle project path setup for all scrapers."""
    current_file = Path(__file__).resolve()
    src_directory = current_file.parent
    while src_directory.name != 'src' and src_directory.parent != src_directory:
        src_directory = src_directory.parent
    project_root = src_directory.parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
```

### Phase 2: Database Standardization (Week 2)

#### 2.1 Unified Database Manager
**Problem:** 3 different database interaction patterns
**Solution:** Single database manager with consistent interface

```python
# src/utils/processing/database.py
class DatabaseManager:
    """Unified database operations for all scrapers."""
    
    def __init__(self, table_name: str, user: str):
        self.table_name = table_name
        self.user = user
        
    def insert_node(self, node: Node, ignore_duplicate: bool = False, 
                   debug: bool = False) -> Node:
        """Standardized node insertion with consistent duplicate handling."""
        try:
            if debug:
                print(f"-Inserting: {node.node_id}")
            util.pydantic_insert(self.table_name, [node], user=self.user)
            return node
        except psycopg.errors.UniqueViolation:
            if ignore_duplicate:
                if debug:
                    print(f"   **Ignoring duplicate: {node.node_id}")
                return node
            else:
                return self._handle_duplicate_with_version(node, debug)
                
    def _handle_duplicate_with_version(self, node: Node, debug: bool) -> Node:
        """Handle duplicates by adding version numbers."""
        base_id = node.node_id
        for i in range(2, 10):
            try:
                v_index = base_id.find("-v_")
                if v_index != -1:
                    base_id = base_id[:v_index]
                    
                new_id = f"{base_id}-v_{i}"
                node.id = NodeID(raw_id=new_id)
                
                if debug:
                    print(f"Adding version: {new_id}")
                    
                util.pydantic_insert(self.table_name, [node], user=self.user)
                return node
            except psycopg.errors.UniqueViolation:
                continue
        raise Exception(f"Could not insert node after 10 attempts: {base_id}")
        
    def batch_insert(self, nodes: List[Node], batch_size: int = 100) -> None:
        """Efficient batch insertion for large datasets."""
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            util.pydantic_insert(self.table_name, batch, user=self.user)
```

#### 2.2 Node Factory Pattern
**Problem:** Inconsistent Node creation across scrapers
**Solution:** Factory for consistent Node generation

```python
# src/utils/data/factories.py
class NodeFactory:
    """Factory for creating standardized Node instances."""
    
    @staticmethod
    def create_structure_node(
        parent_id: str,
        level_classifier: str,
        number: str,
        name: str,
        link: str,
        top_level_title: str,
        status: Optional[str] = None,
        citation: Optional[str] = None
    ) -> Node:
        """Create a structure node with consistent ID generation."""
        parent_node_id = NodeID(raw_id=parent_id)
        node_id = parent_node_id.add_level(level_classifier.lower(), number)
        
        # Check for reserved status using standardized logic
        final_status = NodeFactory._determine_status(name, status)
        
        return Node(
            id=node_id,
            citation=citation,
            link=link,
            status=final_status,
            node_type="structure",
            top_level_title=top_level_title,
            level_classifier=level_classifier.upper(),
            number=number,
            node_name=name,
            parent=parent_id
        )
        
    @staticmethod  
    def create_content_node(
        parent_id: str,
        number: str,
        name: str,
        link: str,
        citation: str,
        top_level_title: str,
        node_text: Optional[NodeText] = None,
        addendum: Optional[Addendum] = None,
        status: Optional[str] = None
    ) -> Node:
        """Create a content node with standardized structure."""
        parent_node_id = NodeID(raw_id=parent_id)
        node_id = parent_node_id.add_level("section", number)
        
        final_status = NodeFactory._determine_status(name, status)
        
        return Node(
            id=node_id,
            citation=citation,
            link=link,
            status=final_status,
            node_type="content",
            top_level_title=top_level_title,
            level_classifier="SECTION",
            number=number,
            node_name=name,
            parent=parent_id,
            node_text=node_text,
            addendum=addendum
        )
        
    @staticmethod
    def _determine_status(name: str, explicit_status: Optional[str]) -> Optional[str]:
        """Determine node status based on name and explicit status."""
        if explicit_status:
            return explicit_status
            
        name_upper = name.upper()
        reserved_keywords = ["REPEALED", "RESERVED", "TRANSFERRED", "OMITTED"]
        
        for keyword in reserved_keywords:
            if keyword in name_upper:
                return "reserved"
                
        return None
```

### Phase 3: Text Processing & Web Utilities (Week 3)

#### 3.1 Unified Text Processor
**Problem:** `get_text_clean()` duplicated, inconsistent approaches
**Solution:** Standardized text processing based on eCFR best practices

```python
# src/utils/processing/text.py
import re
from bs4 import BeautifulSoup, Tag
from typing import Optional, List

class TextProcessor:
    """Unified text processing utilities."""
    
    @staticmethod
    def clean_text(element, direct_children_only: bool = False, 
                  normalize_whitespace: bool = True) -> str:
        """
        Standardized text cleaning based on eCFR best practices.
        
        Args:
            element: BeautifulSoup element or string
            direct_children_only: If True, only get text from direct children
            normalize_whitespace: If True, normalize all whitespace to single spaces
        """
        if element is None:
            return ""
            
        if isinstance(element, str):
            text = element
        elif isinstance(element, Tag):
            if direct_children_only:
                text = element.get_text(separator=' ', strip=True)
            else:
                text = element.get_text()
        else:
            text = str(element)
            
        # Standard cleaning pipeline
        text = text.replace('\xa0', ' ')  # Non-breaking space
        text = text.replace('\r', ' ')    # Carriage return
        text = text.replace('\n', ' ')    # Newline
        text = text.replace('\t', ' ')    # Tab
        
        # Normalize em dashes and en dashes
        text = text.replace('—', '-').replace('–', '-')
        
        # Remove HTML tags if any remain
        text = re.sub('<.*?>', '', text)
        
        # Normalize whitespace
        if normalize_whitespace:
            text = re.sub(r'\s+', ' ', text)
            
        return text.strip()
        
    @staticmethod
    def extract_node_text(container: Tag, tag_filter: str = "p", 
                         skip_empty: bool = True) -> NodeText:
        """Extract NodeText from container with standardized logic."""
        node_text = NodeText()
        
        for element in container.find_all(tag_filter):
            text = TextProcessor.clean_text(element)
            
            if skip_empty and not text:
                continue
                
            node_text.add_paragraph(text=text)
            
        return node_text
        
    @staticmethod
    def extract_addendum(text: str, patterns: List[str] = None) -> Optional[str]:
        """Extract addendum information using standardized patterns."""
        if patterns is None:
            patterns = [
                r'\[([^\]]+)\]$',  # Text in square brackets at end
                r'\(([^)]+)\)$',   # Text in parentheses at end  
                r'SOURCE:\s*(.+)$', # Source information
                r'HISTORY:\s*(.+)$' # History information
            ]
            
        for pattern in patterns:
            match = re.search(pattern, text.strip())
            if match:
                return match.group(1).strip()
                
        return None
```

#### 3.2 Flexible Web Fetcher
**Problem:** Different approaches to web fetching, inconsistent rate limiting
**Solution:** Standardized web fetcher with customizable options

```python
# src/utils/processing/web.py
import time
from typing import Optional
import requests
from bs4 import BeautifulSoup

class WebFetcher:
    """Standardized web fetching with retry logic and rate limiting."""
    
    def __init__(self, delay_seconds: float = 1.0, max_retries: int = 3):
        self.delay_seconds = delay_seconds
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_soup(self, url: str, delay: Optional[float] = None) -> BeautifulSoup:
        """
        Fetch URL and return BeautifulSoup object with standardized error handling.
        
        Args:
            url: URL to fetch
            delay: Optional delay override for this request
        """
        if delay is not None:
            time.sleep(delay)
        elif self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
            
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                return BeautifulSoup(response.text, 'html.parser')
                
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"Failed to fetch {url} after {self.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
                
        raise Exception(f"Unexpected error fetching {url}")
```

### Phase 4: Testing Framework (Week 4)

#### 4.1 Multi-Level Testing Strategy

**Level 1: Infrastructure Compliance (Standardized)**
```python
# tests/test_infrastructure.py
class TestScraperInfrastructure:
    def test_all_scrapers_inherit_base(self):
        """Ensure all scrapers use standardized base."""
        for scraper_class in get_all_scraper_classes():
            assert issubclass(scraper_class, BaseScraper)
            
    def test_no_hardcoded_credentials(self):
        """Critical security test."""
        for scraper_file in get_all_scraper_files():
            content = read_file(scraper_file)
            assert 'user = "' not in content
            assert 'USER = "' not in content
```

**Level 2: Data Validation (Standardized)**
```python
# tests/test_data_output.py
class TestDataOutput:
    def test_node_structure_compliance(self):
        """Test that all scrapers produce valid Nodes."""
        for jurisdiction in TEST_JURISDICTIONS:
            nodes = run_scraper_sample(jurisdiction, limit=10)
            for node in nodes:
                errors = DataValidator.validate_node(node)
                assert len(errors) == 0, f"{jurisdiction}: {errors}"
                
    def test_hierarchy_integrity(self):
        """Test parent-child relationships."""
        for jurisdiction in TEST_JURISDICTIONS:
            nodes = run_scraper_sample(jurisdiction, limit=50)
            hierarchy_errors = DataValidator.validate_hierarchy(nodes)
            assert len(hierarchy_errors) == 0
```

**Level 3: Jurisdiction-Specific (Custom per scraper)**
```python
# tests/test_arizona_specific.py
class TestArizonaSpecific:
    def test_title_extraction(self):
        """Arizona-specific: Ensure titles are parsed correctly."""
        scraper = ArizonaStatutesScraper(config, user)
        title_node = scraper._scrape_title_sample("https://www.azleg.gov/ars/title1/")
        
        assert title_node.level_classifier == "TITLE"
        assert title_node.number == "1"
        assert "General Provisions" in title_node.node_name
        
    def test_chapter_navigation(self):
        """Arizona-specific: Test complex chapter link parsing."""
        scraper = ArizonaStatutesScraper(config, user)
        soup = scraper.fetcher.get_soup("https://www.azleg.gov/ars/title1/")
        
        chapter_links = scraper._extract_chapter_links(soup)
        assert len(chapter_links) > 0
        assert any("chapter1" in link for link in chapter_links)
```

#### 4.2 Golden Dataset Testing
```python
# tests/test_golden_datasets.py
class GoldenDatasetTest:
    """Test against known-good data snapshots."""
    
    def setUp(self):
        self.golden_data = {
            "arizona": load_golden_dataset("arizona_sample_nodes.json"),
            "california": load_golden_dataset("california_sample_nodes.json"),
        }
        
    def test_output_matches_golden_dataset(self):
        """Ensure refactored scrapers produce identical output."""
        for jurisdiction, expected_nodes in self.golden_data.items():
            scraper = get_scraper_for_jurisdiction(jurisdiction)
            actual_nodes = scraper.scrape_sample_urls(expected_nodes.keys())
            
            for url, expected_node in expected_nodes.items():
                actual_node = actual_nodes[url]
                
                # Compare critical fields
                assert actual_node.node_id == expected_node.node_id
                assert actual_node.node_type == expected_node.node_type
                assert actual_node.level_classifier == expected_node.level_classifier
                
                # Text content should be substantially similar
                if expected_node.node_text and actual_node.node_text:
                    similarity = text_similarity(
                        expected_node.node_text.to_string(),
                        actual_node.node_text.to_string()
                    )
                    assert similarity > 0.95
```

#### 4.3 Validation Framework
```python
# src/utils/data/validation.py
class DataValidator:
    """Validation tools for scraper compliance."""
    
    @staticmethod
    def validate_node(node: Node) -> List[str]:
        """Validate that a Node follows schema requirements."""
        errors = []
        
        if not node.id or not node.id.raw_id:
            errors.append("Node must have a valid ID")
            
        if not node.node_type in ["structure", "content"]:
            errors.append("Node type must be 'structure' or 'content'")
            
        if node.node_type == "content" and not node.node_text:
            errors.append("Content nodes must have node_text")
            
        if not node.level_classifier:
            errors.append("Node must have a level_classifier")
            
        return errors
        
    @staticmethod
    def validate_scraper_compliance(scraper_class) -> List[str]:
        """Validate that a scraper follows base patterns."""
        errors = []
        
        if not issubclass(scraper_class, BaseScraper):
            errors.append("Scraper must inherit from BaseScraper")
            
        if not hasattr(scraper_class, 'scrape_implementation'):
            errors.append("Scraper must implement scrape_implementation method")
            
        return errors
```

### Phase 5: Migration Strategy

#### 5.1 Preserving Jurisdiction-Specific Logic

**Key Principle:** Minimal changes to parsing logic, maximum standardization of infrastructure.

**Before (Arizona scraper):**
```python
# Keep the working Arizona logic exactly as-is
def scrape_per_title(url):
    soup: BeautifulSoup = get_url_as_soup(url)
    
    # This Arizona-specific logic was developed through trial and error - KEEP IT
    title_container = soup.find("div", {"class": "ars-title-container"})
    title_header = title_container.find("h1")
    title_name = get_text_clean(title_header)
    
    # Complex Arizona navigation logic that works
    chapter_links = soup.find_all("a", href=re.compile(r"/ars/title\d+/chapter\d+/"))
```

**After (Standardized wrapper):**
```python
class ArizonaStatutesScraper(BaseScraper):
    def scrape_implementation(self) -> None:
        # Arizona keeps using their working method
        for title_url in self._get_title_urls():
            self._scrape_per_title(title_url)  # Same function!
            
    def _scrape_per_title(self, url: str) -> None:
        # Use standardized web fetching
        soup = self.fetcher.get_soup(url)
        
        # KEEP the working Arizona logic exactly
        title_container = soup.find("div", {"class": "ars-title-container"})
        title_header = title_container.find("h1")
        title_name = TextProcessor.clean_text(title_header)  # Standardized cleaning
        
        # Create node using helper, but Arizona provides the data
        title_node = self.create_structure_node(
            parent_id=self.config.corpus_id,
            level_classifier="title",
            number=self._extract_title_number(title_name),  # Arizona logic
            name=title_name,
            link=url,
            top_level_title=self._extract_title_number(title_name)
        )
        
        # Standardized database operation
        self.insert_node_safely(title_node)
        
        # Keep the complex Arizona navigation logic unchanged
        chapter_links = soup.find_all("a", href=re.compile(r"/ars/title\d+/chapter\d+/"))
        for link in chapter_links:
            # Arizona-specific logic continues...
```

#### 5.2 Documentation Strategy

For each scraper, document the "why" behind quirky logic:
```python
class CaliforniaCodeScraper(BaseScraper):
    def _navigate_complex_hierarchy(self, soup: BeautifulSoup) -> List[str]:
        """
        California has a deeply nested hierarchy that changes structure
        mid-tree. This logic was developed through extensive trial and error.
        
        Known quirks:
        - Some codes have Division > Part > Chapter > Article > Section
        - Others jump directly from Part > Section
        - The "Select Code" dropdown changes navigation structure
        - Must handle both old HTML tables and new div layout
        """
        # Keep the battle-tested California logic exactly as-is
        if soup.find("table", {"class": "law-table"}):  # Old HTML
            return self._parse_legacy_table_structure(soup)
        else:  # New div structure
            return self._parse_modern_div_structure(soup)
```

#### 5.3 Migration Process

**Step 1: Infrastructure Only**
- Replace hardcoded credentials with `CredentialManager`
- Replace global variables with `ScraperConfig`
- Wrap in `BaseScraper` class
- Use `DatabaseManager` for all database operations
- **DO NOT touch parsing logic**

**Step 2: Test Extensively**
- Run before/after comparison tests
- Verify identical database output
- Test with golden datasets

**Step 3: Optional Cleanup**
- Document quirks and "why" comments
- Standardize common patterns where safe
- Only optimize when absolutely necessary

### File Organization

```
src/utils/
├── __init__.py
├── base/
│   ├── __init__.py          # setup_project_path()
│   ├── scraper.py           # BaseScraper, SeleniumScraper
│   ├── config.py            # ScraperConfig, ConfigManager  
│   └── credentials.py       # CredentialManager
├── data/
│   ├── __init__.py
│   ├── models.py            # Enhanced Pydantic models
│   ├── factories.py         # NodeFactory, ScraperFactory
│   └── validation.py        # DataValidator
├── processing/
│   ├── __init__.py
│   ├── text.py              # TextProcessor
│   ├── web.py               # WebFetcher
│   └── database.py          # DatabaseManager
├── infrastructure/
│   ├── __init__.py
│   ├── logging.py           # ScraperLogger
│   ├── errors.py            # ErrorRecovery
│   └── monitoring.py        # Performance monitoring
└── legacy/                  # Keep during migration
    ├── utilityFunctions.py
    ├── scrapingHelpers.py
    └── processingHelpers.py
```

## Success Criteria

✅ **Security:** No hardcoded credentials in any file  
✅ **Code Reduction:** 70% reduction in duplicate code  
✅ **Consistency:** All scrapers use standardized patterns  
✅ **Error Handling:** Specific exception handling throughout  
✅ **Maintainability:** New scrapers follow template patterns  
✅ **Testing:** Automated validation for all scrapers  
✅ **Preserved Logic:** All jurisdiction-specific parsing logic maintained

## Next Steps

1. **Immediate Priority:** Implement Phase 1 - Foundation Infrastructure
2. **Security First:** Remove all hardcoded credentials  
3. **Pilot Testing:** Migrate Arizona scraper as proof of concept
4. **Gradual Rollout:** Migrate complex scrapers one by one
5. **Documentation:** Update CLAUDE.md with new patterns

This standardization will establish a robust, secure, and maintainable foundation while preserving the hard-won jurisdiction-specific parsing logic that makes these scrapers work.