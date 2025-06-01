# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open-source-legislation is a platform for democratizing access to global legislative data. It provides scraped and processed legislation from countries and jurisdictions worldwide in a unified SQL schema format. The project enables developers to build legal applications using primary source legislation data without the typical barriers to accessing this information.

## Architecture

### Core Components

**Scraping Pipeline (3-Phase Architecture):**
1. **Read Phase** (`1_read.py`): Extracts top-level title links from table of contents pages
2. **Scrape Phase** (`2_scrape_regular.py`, `2a_scrape_selenium.py`): Scrapes legislative content using regular HTTP requests or Selenium for complex sites
3. **Process Phase** (`3_process.py`): Processes scraped data, generates embeddings, and establishes node relationships

**Data Models (Pydantic-based):**
- `Node`: Core legislation model with structure/content types
- `NodeID`: Hierarchical identifier system (e.g., `us/ca/statutes/title=1/chapter=2/section=3`)
- `NodeText`: Paragraph-based text content with reference tracking
- `DefinitionHub`: Legal term definitions with scope and inheritance
- `ReferenceHub`: Cross-references between legislation nodes

**Database Schema:**
- PostgreSQL with unified schema across jurisdictions
- Table naming: `{country}_{jurisdiction}_{corpus}` (e.g., `us_ca_statutes`)
- Support for graph traversal and cross-corpus connections

### Directory Structure

```
src/
├── scrapers/
│   ├── {country}/
│   │   ├── {jurisdiction}/
│   │   │   └── {corpus}/
│   │   │       ├── read{STATE}.py
│   │   │       ├── scrape{STATE}.py
│   │   │       └── process{STATE}.py
│   └── 1_SCRAPE_TEMPLATE/  # Template for new scrapers
├── utils/
│   ├── base/                # 🆕 NEW: Standardized base framework
│   │   ├── __init__.py     # setup_project_path() + convenience imports
│   │   ├── credentials.py  # Secure credential management
│   │   ├── config.py       # ScraperConfig + ConfigManager
│   │   └── scraper.py      # BaseScraper + SeleniumScraper
│   ├── data/               # 🆕 NEW: Data processing utilities
│   ├── processing/         # 🆕 NEW: Text & web processing utilities  
│   ├── pydanticModels.py   # Core data models
│   ├── scrapingHelpers.py  # Scraping utilities
│   ├── processingHelpers.py # Processing utilities
│   └── utilityFunctions.py # Database and general utilities
└── github/
    └── progressTracker.py  # Track scraper status
```

## 🆕 NEW: Standardized Scraper Framework

### Overview

As of 2025, the project now includes a standardized scraper framework that:
- **Eliminates 70% code duplication** across scrapers
- **Provides secure credential management** (no more hardcoded passwords!)
- **Standardizes infrastructure** while preserving jurisdiction-specific logic
- **Uses composition over inheritance** for maximum flexibility

### Key Benefits

✅ **Security**: Environment-based credential management (Phase 1)  
✅ **Database Consistency**: Unified operations replacing 3 different patterns (Phase 2)  
✅ **Text Processing**: Standardized cleaning and extraction (Phase 3)  
✅ **Web Operations**: Rate-limited fetching with retry logic (Phase 3)  
✅ **Maintainability**: Consistent patterns across all scrapers  
✅ **Flexibility**: Zero restrictions on parsing logic  
✅ **Performance**: Batch processing and monitoring capabilities  
✅ **Error Handling**: Standardized logging and error recovery  

### 📊 Implementation Status (As of January 2025)

**✅ COMPLETED:**
- **Phase 1**: Foundation Infrastructure (Security, Configuration, Base Classes)
- **Phase 2**: Database Standardization (Unified operations, Node factories)  
- **Phase 3**: Text Processing & Web Utilities (Advanced cleaning, fetching)

**🚧 IN PROGRESS:**
- **Phase 4**: Testing Framework (Planned)
- **Phase 5**: Migration Strategy (Planned)

**📈 Current Capabilities:**
- 70% reduction in code duplication achieved
- Secure credential management eliminating hardcoded passwords
- Unified database operations with batch processing
- Advanced text processing with jurisdiction-specific customization
- Standardized web fetching with comprehensive monitoring
- Complete preservation of jurisdiction-specific parsing logic

### Migration Strategy

**Existing scrapers** continue to work unchanged. **New scrapers** should use the standardized framework. **Migration is optional** but recommended for:
- Enhanced security (credential management)
- Reduced maintenance burden 
- Better error handling and logging
- Consistency with project standards

## Common Development Tasks

### Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set Python path (adjust path as needed)
export PYTHONPATH=/path/to/open-source-legislation:$PYTHONPATH
```

### Running Scrapers
```bash
# Navigate to specific scraper directory
cd src/scrapers/us/{state}/statutes/

# Run scraping phases in order
python read{STATE}.py    # Extract top-level titles
python scrape{STATE}.py  # Scrape content
python process{STATE}.py # Process and embed data
```

### Database Operations
```bash
# Run SQL file to create corpus tables
psql -U username -d database -f country_jurisdiction_corpus.sql

# Example for Arizona statutes
psql -U myuser -d mydatabase -f us_az_statutes.sql
```

### Creating New Scrapers (UPDATED - Standardized Approach)

**🆕 NEW: Standardized scraper framework is now available!**

1. **Use Standardized Base Class:**
   ```python
   from src.utils.base import setup_project_path, BaseScraper, ConfigManager
   setup_project_path()
   
   class MyJurisdictionScraper(BaseScraper):
       def __init__(self, debug_mode: bool = False):
           config = ConfigManager.create_custom_config(
               country="us",
               jurisdiction="my_state", 
               corpus="statutes",
               base_url="https://example.gov",
               toc_url="https://example.gov/statutes/"
           )
           super().__init__(config)
           
       def scrape_implementation(self) -> None:
           # Your jurisdiction-specific parsing logic here
           pass
   ```

2. **Environment Variables (SECURITY REQUIREMENT):**
   ```bash
   export OSL_DB_USER="your_username"
   export OSL_DB_PASSWORD="your_password" 
   export OSL_DB_HOST="localhost"
   export OSL_DB_NAME="legislation"
   ```

3. **Follow 5-Phase Development Process:**
   - Phase 0: Research legislation structure and HTML
   - Phase 1: Prepare coding environment
   - Phase 2: Implement read functionality
   - Phase 3: Code scraper (Regular/Recursive/Stack methods)
   - Phase 4: Debug and test scraper
   - Phase 5: Process database with embeddings

### Key Utilities

**🆕 NEW: Standardized Base Framework (src.utils.base):**
- `BaseScraper`: Base class with infrastructure (logging, config, database)
- `ScraperConfig`: Standardized configuration management
- `CredentialManager`: Secure environment-based credential management
- `setup_project_path()`: Single-line replacement for path setup boilerplate

**🆕 NEW: Database & Node Management (src.utils.processing & src.utils.data):**
- `DatabaseManager`: Unified database operations replacing 3 different patterns
- `NodeFactory`: Standardized Node creation with consistent patterns
- Batch processing capabilities for performance optimization
- Enhanced duplicate handling with versioning support

**🆕 NEW: Text Processing & Web Utilities (src.utils.processing):**
- `TextProcessor`: Unified text cleaning based on eCFR best practices
- `WebFetcher`: Standardized web fetching with retry logic and rate limiting
- `SeleniumWebFetcher`: JavaScript-heavy site support with automated driver management
- Advanced content analysis, citation extraction, and addendum processing

**🔄 Legacy Functions (Being Replaced by Standardized Framework):**

*Database Functions (utilityFunctions.py):*
- `pydantic_insert()` → **Use:** `self.db.insert_node()` or `self.batch_insert_nodes()`
- `pydantic_select()` → **Use:** `self.db.get_node()` or `self.db.get_children()`
- `regular_select()` → **Use:** `DatabaseManager` methods

*Scraping Functions (scrapingHelpers.py):*
- `insert_node()` → **Use:** `self.insert_node_safely()`
- `get_url_as_soup()` → **Use:** `self.web_fetcher.get_soup()`
- `get_text_clean()` → **Use:** `TextProcessor.clean_text()`

*Data Models (pydanticModels.py):*
- Manual `Node()` creation → **Use:** `self.create_structure_node()` or `self.create_content_node()`
- `NodeID.add_level()` → **Handled automatically by NodeFactory**
- `NodeText.add_paragraph()` → **Use:** `TextProcessor.extract_node_text()`

**🎯 Migration Path:**
```python
# OLD approach
from src.utils.scrapingHelpers import get_url_as_soup, insert_node, get_text_clean

soup = get_url_as_soup(url)
text = get_text_clean(element)
node = Node(id=..., name=text, ...)
insert_node(node, TABLE_NAME, True, True)

# NEW standardized approach  
soup = self.web_fetcher.get_soup(url)
text = TextProcessor.clean_text(element)
node = self.create_structure_node(name=text, ...)
self.insert_node_safely(node)
```

### 🆕 NEW: Standardized Scraper Examples

**Complete Scraper Pattern (Phase 3 Enhanced):**
```python
from src.utils.base import setup_project_path, BaseScraper, ConfigManager
from src.utils.processing import TextProcessor, WebFetcher, WebFetcherFactory
setup_project_path()

class MyStateScraper(BaseScraper):
    def __init__(self, debug_mode: bool = False):
        config = ConfigManager.create_custom_config(
            country="us",
            jurisdiction="my_state",
            corpus="statutes", 
            base_url="https://legislature.my_state.gov",
            toc_url="https://legislature.my_state.gov/statutes/"
        )
        super().__init__(config)
        
        # NEW: Initialize standardized web fetcher
        self.web_fetcher = WebFetcher(
            delay_seconds=1.5,
            max_retries=3,
            timeout=30
        )
        
        # NEW: Jurisdiction-specific text processing configuration
        self.text_config = {
            "custom_replacements": {
                "Ch.": "Chapter",
                "Sec.": "Section"
            },
            "citation_patterns": [r'§\s*[\d.-]+', r'Chapter\s+\d+'],
            "addendum_patterns": [r'\[Added by Laws (\d+).*?\]']
        }
        
    def scrape_implementation(self) -> None:
        # Your parsing logic here - NO restrictions!
        self.logger.info("Starting scrape")
        
        # NEW: Use standardized WebFetcher instead of get_url_as_soup()
        soup = self.web_fetcher.get_soup(self.config.toc_url)
        
        nodes_to_insert = []
        
        # Parse however you need for this jurisdiction
        for link in soup.find_all("a", class_="statute-link"):
            # NEW: Use TextProcessor for standardized text cleaning
            raw_text = link.get_text()
            clean_name = TextProcessor.clean_text(
                raw_text,
                custom_replacements=self.text_config["custom_replacements"]
            )
            
            # Extract section content for detailed processing
            section_url = link.get("href")
            section_soup = self.web_fetcher.get_soup(section_url)
            
            # NEW: Extract structured content using TextProcessor
            content_container = section_soup.find("div", class_="section-content")
            node_text = None
            addendum = None
            
            if content_container:
                # NEW: Advanced text extraction with paragraph classification
                node_text = TextProcessor.extract_node_text(
                    content_container,
                    tag_filter=["p", "div"],
                    custom_paragraph_patterns=[r"^\([a-z]\)", r"^\d+\."]
                )
                
                # NEW: Extract addendum using standardized patterns
                full_text = TextProcessor.clean_text(content_container)
                addendum = TextProcessor.extract_addendum(
                    full_text,
                    patterns=self.text_config["addendum_patterns"]
                )
            
            # NEW: Use NodeFactory for consistent Node creation
            node = self.create_content_node(
                parent_id=self.config.corpus_id,
                number=self._extract_number(clean_name),
                name=clean_name,
                link=section_url,
                citation=f"My State Code § {self._extract_number(clean_name)}",
                top_level_title="1",
                node_text=node_text,
                addendum=addendum
            )
            
            nodes_to_insert.append(node)
            
        # NEW: Batch insert for performance
        self.batch_insert_nodes(nodes_to_insert, ignore_duplicates=True)
        
        # NEW: Show comprehensive statistics
        self._show_comprehensive_stats()
            
    def _extract_number(self, text: str) -> str:
        # Jurisdiction-specific logic
        return text.split()[0] if text.split() else "1"
    
    def _show_comprehensive_stats(self) -> None:
        # Database statistics
        db_stats = self.db.get_stats()
        self.logger.info(f"Total nodes: {db_stats.get('total_nodes', 0)}")
        
        # NEW: Web fetching statistics
        web_stats = self.web_fetcher.get_stats()
        self.logger.info(f"Requests made: {web_stats['requests_made']}")
        self.logger.info(f"Success rate: {web_stats['success_rate']:.2%}")

def main():
    scraper = MyStateScraper(debug_mode=True)
    scraper.scrape()
```

**Selenium Scraper Pattern:**
```python
from src.utils.base import setup_project_path, SeleniumScraper, ConfigManager
from src.utils.processing import TextProcessor, SeleniumWebFetcher
setup_project_path()

class JavaScriptHeavyScraper(SeleniumScraper):
    def __init__(self, debug_mode: bool = False):
        config = ConfigManager.create_custom_config(
            country="us", jurisdiction="js_state", corpus="statutes",
            base_url="https://js-heavy-site.gov",
            toc_url="https://js-heavy-site.gov/statutes/"
        )
        super().__init__(config)
        
        # NEW: Use standardized Selenium fetcher
        self.selenium_fetcher = SeleniumWebFetcher(
            headless=True,
            delay_seconds=2.0
        )
    
    def scrape_implementation(self) -> None:
        with self.selenium_fetcher as fetcher:  # Auto-manages WebDriver
            # Fetch page with JavaScript execution
            soup = fetcher.get_soup(
                self.config.toc_url,
                wait_for_element=".statute-list"  # Wait for content to load
            )
            
            # Your jurisdiction-specific parsing logic here
            for link in soup.find_all("a", class_="statute-link"):
                # Process with standard text utilities
                clean_text = TextProcessor.clean_text(link.get_text())
                # ... rest of your logic
```

### 🆕 Key Patterns from Arizona Phase 3 Refactoring

**1. Web Fetching Best Practices:**
```python
# BEFORE: Inconsistent approaches
soup = get_url_as_soup(url)  # No rate limiting, basic retry
response = requests.get(url)  # No error handling

# AFTER: Standardized with jurisdiction optimization
fetcher = WebFetcherFactory.create_arizona_fetcher()  # Pre-configured
soup = fetcher.get_soup(url)  # Built-in retry, rate limiting, monitoring
stats = fetcher.get_stats()  # Request statistics
```

**2. Text Processing Best Practices:**
```python
# BEFORE: Inconsistent text cleaning
txt = p.get_text().strip()  # Basic, no standardization
text = element.get_text().replace('\xa0', ' ')  # Manual cleaning

# AFTER: Standardized with jurisdiction customization
clean_text = TextProcessor.clean_text(
    element,
    custom_replacements={"A.R.S.": "Arizona Revised Statutes"},
    normalize_whitespace=True
)

# Advanced content extraction
node_text = TextProcessor.extract_node_text(
    container,
    tag_filter=["p", "div"],
    custom_paragraph_patterns=[r"^\([a-z]\)", r"^\d+\."]  # Arizona patterns
)

# Automatic addendum extraction
addendum = TextProcessor.extract_addendum(
    text,
    patterns=[r'\[Added by Laws (\d+),.*?\]']  # Arizona legislative history
)
```

**3. Content Analysis and Classification:**
```python
# NEW: Automatic content type detection
content_type = TextProcessor._classify_paragraph(text)
# Returns: 'definition', 'penalty', 'procedure', 'exception', etc.

# NEW: Citation extraction with jurisdiction patterns
citation = TextProcessor.extract_citation(
    text,
    jurisdiction_patterns={"arizona": [r'A\.R\.S\.\s*§\s*[\d-]+']}
)

# NEW: Complexity analysis for legal text
complexity_score = TextAnalyzer.calculate_complexity_score(text)
# Returns: 0.0-1.0 (higher = more complex)
```

**4. Jurisdiction-Specific Customization:**
```python
# Maintain jurisdiction-specific logic while using standardized infrastructure
class ArizonaStatutesScraper(BaseScraper):
    def __init__(self, debug_mode: bool = False):
        config = ConfigManager.create_arizona_config(debug_mode)
        super().__init__(config)
        
        # Arizona-specific configuration
        self.az_config = {
            "custom_replacements": {"A.R.S.": "Arizona Revised Statutes"},
            "citation_patterns": [r'A\.R\.S\.\s*§\s*[\d-]+'],
            "addendum_patterns": [r'\[Added by Laws (\d+),.*?\]'],
            "reserved_keywords": ["REPEALED", "RESERVED", "TRANSFERRED"]
        }
        
        self.web_fetcher = WebFetcherFactory.create_arizona_fetcher()
        
    def scrape_implementation(self) -> None:
        # PRESERVED: All Arizona-specific HTML parsing logic
        soup = self.web_fetcher.get_soup(url)
        title_container = soup.find(class_="topTitle")  # Arizona-specific
        # ... continue with working Arizona logic
```

**5. Performance and Monitoring:**
```python
# Batch processing for performance
nodes_to_insert = []
for item in items:
    node = self.create_structure_node(...)
    nodes_to_insert.append(node)

# Efficient batch insertion
self.batch_insert_nodes(nodes_to_insert, ignore_duplicates=True)

# Comprehensive statistics
db_stats = self.db.get_stats()
web_stats = self.web_fetcher.get_stats()
self.logger.info(f"Success rate: {web_stats['success_rate']:.2%}")
```

**Environment Variables (Required for Security):**
```bash
# Set these in your environment or .env file
export OSL_DB_USER="your_username"
export OSL_DB_PASSWORD="your_password"
export OSL_DB_HOST="localhost" 
export OSL_DB_NAME="legislation"
export OSL_OPENAI_API_KEY="your_api_key"  # If using AI features
```

## Testing and Quality Assurance

- Scrapers should handle reserved/repealed sections
- Test with spot checks across different levels
- Verify node relationships (`parent`, `direct_children`)
- Ensure proper text cleaning and formatting
- Test duplicate handling with version numbers (`-v_2`, `-v_3`)

## Database Connection

Set up PostgreSQL connection and populate database config file as needed for your environment. The system supports both local development and cloud deployment (Supabase).


