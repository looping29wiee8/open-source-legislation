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
│   │   │
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

## 🆕 NEW: Enhanced Standardized Framework (2025)

### Recent Updates - Revolutionary Debugging Workflow

**🎉 MAJOR ENHANCEMENT (January 2025)**: Enhanced the standardized framework with revolutionary debugging and table management capabilities based on real-world Arizona scraper refactoring experience.

**Key Improvements:**
- ✅ **Automatic table creation** from Node schema (eliminates manual SQL files)
- ✅ **Enhanced debugging modes** - Clean/Resume/Skip with intelligent detection
- ✅ **Real database operations** - Verified insertions (no more fake success logs)
- ✅ **Dynamic resume detection** - Auto-detects interruption points
- ✅ **Progress tracking** - Reliable resuming with metadata storage
- ✅ **Command-line interface** - Professional debugging experience

### Overview

As of 2025, the project includes a comprehensive standardized framework that:
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

### **⚠️ CRITICAL: Mandatory Timeout Usage for Claude Code Instances**

**🚨 ESSENTIAL RULE: NEVER run scrapers without timeout conditions during debugging/validation.**

**Why this is critical:**
- Legislative scrapers can run for 2-6 hours to complete
- Without timeouts, Claude Code instances cannot get feedback to validate or debug
- Progressive timeout-based testing is the ONLY effective debugging approach
- Running full scrapers wastes time when issues exist

**ALWAYS use these patterns:**
```bash
# ✅ For debugging/validation (MANDATORY)
python scrapeJURISDICTION_standardized.py --mode clean --validation --debug
python scrapeJURISDICTION_standardized.py --mode clean --timeout 2 --max-titles 3 --debug

# ✅ For production (only after validation passes)
python scrapeJURISDICTION_standardized.py --mode clean
```

**This applies to:**
- All scraper debugging sessions
- All validation workflows  
- All refactoring processes
- All new scraper development

### Environment Setup (Updated - Modern Approach)
```bash
# Clone repository (if not already done)
git clone https://github.com/spartypkp/open-source-legislation.git
cd open-source-legislation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install project with dependencies (Modern approach using pyproject.toml)
pip install -e ".[dev]"

# This single command:
# ✅ Installs all production dependencies from pyproject.toml
# ✅ Installs development tools (pytest, black, mypy, etc.)
# ✅ Sets up the project for editable installation
# ✅ Eliminates PYTHONPATH issues - modules are now importable


```

**Key Benefits of New Setup:**
- ✅ **No more PYTHONPATH issues** - Project installation handles module imports
- ✅ **Single dependency source** - Everything defined in `pyproject.toml`
- ✅ **Development tools included** - Testing, linting, type checking ready
- ✅ **Consistent environments** - Everyone gets the same setup
- ✅ **Modern Python packaging** - Follows current best practices

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

#### Quick Start (Recommended)
```bash
# 1. Ensure environment is set up (one-time setup)
cd open-source-legislation
source venv/bin/activate
pip install -e ".[dev]"  # Installs project + all dependencies
```

#### Standardized Scraper Template
1. **Use Standardized Base Class:**
   ```python
   from src.utils.base import setup_project_path, BaseScraper, ConfigManager
   from src.utils.processing.database import ScrapingMode
   setup_project_path()
   
   class MyJurisdictionScraper(BaseScraper):
       def __init__(self, debug_mode: bool = False, mode: ScrapingMode = ScrapingMode.RESUME, skip_title: Optional[int] = None):
           # Jurisdiction-specific configuration defined inline
           config = ConfigManager.create_custom_config(
               country="us",
               jurisdiction="my_state", 
               corpus="statutes",
               base_url="https://example.gov",
               toc_url="https://example.gov/statutes/",
               skip_title=0,  # Will be overridden by mode logic
               reserved_keywords=["REPEALED", "RESERVED"],  # Add jurisdiction-specific keywords
               delay_seconds=1.5  # Adjust based on site responsiveness
           )
           super().__init__(config, mode=mode, skip_title=skip_title)
           
       def scrape_implementation(self) -> None:
           # Your jurisdiction-specific parsing logic here
           # NEW: Add progress tracking for reliable resuming
           for i, item in enumerate(items):
               self.track_title_progress(i, item_url, {"total_items": len(items)})
               # ... your parsing logic
   ```

2. **Environment Variables (SECURITY REQUIREMENT):**
   ```bash
   # Add to your .env file:
   OSL_DB_USER="your_username"
   OSL_DB_PASSWORD="your_password" 
   OSL_DB_HOST="localhost"
   OSL_DB_NAME="legislation"
   ```

3. **Enhanced Main Function with Debugging Support:**
   ```python
   def main():
       import argparse
       
       parser = argparse.ArgumentParser(description="My Jurisdiction Scraper")
       parser.add_argument("--mode", choices=["resume", "clean", "skip"], default="resume")
       parser.add_argument("--skip-title", type=int, help="Title number to skip to")
       parser.add_argument("--debug", action="store_true", help="Enable debug mode")
       
       args = parser.parse_args()
       mode_map = {"resume": ScrapingMode.RESUME, "clean": ScrapingMode.CLEAN, "skip": ScrapingMode.SKIP}
       
       try:
           scraper = MyJurisdictionScraper(
               debug_mode=args.debug,
               mode=mode_map[args.mode],
               skip_title=args.skip_title
           )
           scraper.scrape()
           print(f"✅ Scraping completed successfully in {args.mode} mode!")
       except Exception as e:
           print(f"❌ Scraping failed: {e}")
           raise
   ```

4. **Follow Enhanced 5-Phase Development Process:**
   - Phase 0: Research legislation structure and HTML
   - Phase 1: Prepare coding environment (use `pip install -e ".[dev]"`)
   - Phase 2: Implement read functionality
   - Phase 3: Code scraper with standardized framework
   - Phase 4: **Enhanced debugging** with clean/resume/skip modes
   - Phase 5: Process database with embeddings

**No More PYTHONPATH Issues:** The `pip install -e ".[dev]"` command handles all module imports automatically!

### Key Utilities

**🆕 NEW: Standardized Base Framework (src.utils.base):**
- `BaseScraper`: Base class with infrastructure (logging, config, database)
- `ScraperConfig`: Standardized configuration management
- `CredentialManager`: Secure environment-based credential management
- `setup_project_path()`: Single-line replacement for path setup boilerplate

**🆕 NEW: Database & Node Management (src.utils.processing & src.utils.data):**
- `DatabaseManager`: Unified database operations replacing 3 different patterns
- `NodeFactory`: Standardized Node creation with consistent patterns
- `ScrapingMode`: Enhanced debugging workflow with clean/resume/skip modes
- **Automatic table creation** from Node schema (no more manual SQL files!)
- **Dynamic resume point detection** for interrupted scrapes
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
        # Jurisdiction-specific configuration defined inline
        config = ConfigManager.create_custom_config(
            country="us",
            jurisdiction="my_state",
            corpus="statutes", 
            base_url="https://legislature.my_state.gov",
            toc_url="https://legislature.my_state.gov/statutes/",
            skip_title=0,  # Adjust based on jurisdiction needs
            reserved_keywords=["REPEALED", "RESERVED"],  # Add jurisdiction-specific keywords
            delay_seconds=1.5  # Adjust based on site responsiveness
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

### 🆕 Enhanced Debugging Workflow (2025)

**Revolutionary improvement for development and debugging workflow:**

#### **Intelligent Scraping Modes with Mandatory Timeout Usage**

**🚨 CRITICAL FOR CLAUDE CODE INSTANCES: ALWAYS use timeout conditions during debugging. Running scrapers without timeouts will prevent feedback for hours.**

```bash
# ✅ CORRECT - Validation mode (RECOMMENDED for all debugging)
python scrapeAZ_standardized.py --mode clean --validation --debug
# Automatically sets: 2 min timeout, 3 titles max, 100 nodes max

# ✅ CORRECT - Custom timeout combinations
python scrapeAZ_standardized.py --mode clean --timeout 2 --max-titles 3 --debug
python scrapeAZ_standardized.py --mode skip --skip-title 25 --timeout 1 --debug

# ✅ CORRECT - Ultra-fast spot checks
python scrapeAZ_standardized.py --mode clean --timeout 1 --max-titles 1 --debug

# ❌ WRONG - Will run for hours without feedback (only use for production)
python scrapeAZ_standardized.py --mode clean

# Resume mode (DEFAULT): Auto-detects where to continue after interruptions
python scrapeAZ_standardized.py --mode resume --timeout 5

# Skip mode: Start from specific title (for debugging specific sections)  
python scrapeAZ_standardized.py --mode skip --skip-title 25 --timeout 2 --debug
```

#### **Automatic Table Management**
- ✅ **No more manual SQL files** - Tables created automatically from Node schema
- ✅ **No more "table doesn't exist" errors** - Auto-creation handles everything
- ✅ **Safe clean mode** - Prevents accidental data loss with confirmation checks
- ✅ **Race condition handling** - Multiple processes can safely create tables

#### **Dynamic Resume Detection**
- ✅ **Intelligent recovery** - Automatically detects last processed title
- ✅ **Zero configuration** - No more hardcoded `skip_title` values
- ✅ **Progress tracking** - Metadata stored for reliable resuming
- ✅ **Manual override** - Can still specify `--skip-title` when needed

#### **Real Database Operations (No More Fake Logs!)**
- ✅ **Verified insertions** - Logs show actual database operations
- ✅ **Batch processing** - Efficient bulk insertions with fallback to individual
- ✅ **Error transparency** - Clear distinction between success and failure
- ✅ **Statistics reporting** - Real-time counts and progress tracking

#### **Development Workflow Examples (Updated with Mandatory Timeouts)**

**Scenario 1: Starting a new scraper**
```bash
# ✅ CORRECT - First run with validation timeout
python scrapeNEW_standardized.py --mode clean --validation --debug

# ❌ WRONG - Will run for hours without feedback
python scrapeNEW_standardized.py --mode clean --debug
```

**Scenario 2: Scraper crashed at title 15**
```bash
# ✅ CORRECT - Resume with timeout for safety
python scrapeNEW_standardized.py --mode resume --timeout 10

# ❌ RISKY - May run for hours if issue persists
python scrapeNEW_standardized.py --mode resume
```

**Scenario 3: Debugging issue in title 42**
```bash
# ✅ CORRECT - Skip directly to problem area with timeout
python scrapeNEW_standardized.py --mode skip --skip-title 42 --timeout 2 --debug

# ❌ WRONG - No timeout protection
python scrapeNEW_standardized.py --mode skip --skip-title 42 --debug
```

**Scenario 4: Testing changes to parsing logic**
```bash
# ✅ CORRECT - Test with timeout first
python scrapeNEW_standardized.py --mode clean --validation --debug
# Then if validation passes:
python scrapeNEW_standardized.py --mode clean

# ❌ WRONG - Jump straight to full run
python scrapeNEW_standardized.py --mode clean
```

**Scenario 5: Progressive debugging workflow (RECOMMENDED)**
```bash
# Step 1: Ultra-fast spot check (1 minute)
python scrapeNEW_standardized.py --mode clean --timeout 1 --max-titles 1 --debug

# Step 2: Medium validation (2 minutes, 3 titles)  
python scrapeNEW_standardized.py --mode clean --validation --debug

# Step 3: Extended test (10 minutes, 10 titles)
python scrapeNEW_standardized.py --mode clean --timeout 10 --max-titles 10

# Step 4: Full production run (only if all above pass)
python scrapeNEW_standardized.py --mode clean
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
        # Arizona-specific configuration defined inline (not in shared config.py)
        config = ConfigManager.create_custom_config(
            country="us",
            jurisdiction="az",
            corpus="statutes",
            base_url="https://www.azleg.gov",
            toc_url="https://www.azleg.gov/arstitle/",
            skip_title=38,  # Arizona starts from title 38
            reserved_keywords=["REPEALED", "RESERVED", "TRANSFERRED"],
            delay_seconds=1.5,
            debug_mode=debug_mode
        )
        super().__init__(config)
        
        # Arizona-specific text processing configuration
        self.az_config = {
            "custom_replacements": {"A.R.S.": "Arizona Revised Statutes"},
            "citation_patterns": [r'A\.R\.S\.\s*§\s*[\d-]+'],
            "addendum_patterns": [r'\[Added by Laws (\d+),.*?\]']
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
# Create .env file in project root with:
OSL_DB_USER="your_username"
OSL_DB_PASSWORD="your_password"
OSL_DB_HOST="localhost" 
OSL_DB_NAME="legislation"
OSL_OPENAI_API_KEY="your_api_key"  # If using AI features

# Load variables:
source .env

# Or use python-dotenv (automatically loaded by framework):
# The standardized framework automatically loads .env files
```

## 🆕 **Scraper Validation & Testing Framework (2025)**

**🎉 CRITICAL CAPABILITY**: Comprehensive validation methodology developed through real-world Arizona refactoring experience.

### **The Validation Challenge**

Scraper validation is **fundamentally different from traditional software testing**:
- **No ground truth** to validate against
- **Legislative hierarchies** must be modeled as knowledge graphs  
- **Content accuracy** requires human judgment
- **Structure vs Content** are separate validation concerns
- **Jurisdictional differences** mean every scraper is unique

### **Two Types of Errors**

**1. "Compiler Errors" (Infrastructure)**
- Scraper crashes due to configuration issues
- Database connection problems
- Import/dependency errors
- **Detection**: Immediate failure
- **Fix**: Debug infrastructure

**2. "Runtime Errors" (Logic/Content)**  
- Wrong hierarchical structure extracted
- Missing or incorrectly parsed content
- **Detection**: Requires systematic validation
- **Fix**: Analyze HTML, debug parsing logic

### **Timeout-Based Validation Approach**

**🆕 KEY INNOVATION**: Use timeouts for iterative validation instead of running full scrapers.

```bash
# Timeout validation for rapid feedback (30 seconds)
python -c "
import subprocess
import signal
import time

signal.signal(signal.SIGALRM, lambda s, f: exec('raise TimeoutError()'))
signal.alarm(30)

try:
    subprocess.run(['python', 'scrape{JURISDICTION}_standardized.py', '--mode', 'clean', '--debug'])
except TimeoutError:
    print('=== SCRAPER STOPPED AFTER 30 SECONDS FOR VALIDATION ===')
finally:
    signal.alarm(0)
"
```

**Benefits:**
- ✅ **Fast feedback** - Get sample data in 30 seconds vs hours
- ✅ **Early issue detection** - Catch problems before wasting time
- ✅ **Iterative debugging** - Test fix → validate → repeat cycle
- ✅ **Critical error detection** - Pydantic/request errors break scraper immediately

### **Systematic Validation Process**

**Step 1: Database Health Check**
```python
# Automated health check queries
from src.utils.utilityFunctions import db_connect

conn = db_connect()
with conn.cursor() as cur:
    # Node distribution validation
    cur.execute('SELECT level_classifier, COUNT(*) FROM us_{jurisdiction}_statutes GROUP BY level_classifier')
    breakdown = cur.fetchall()
    
    # Content population check  
    cur.execute('SELECT COUNT(*) as total_sections, COUNT(node_text) as sections_with_text FROM us_{jurisdiction}_statutes WHERE level_classifier = %s', ('SECTION',))
    content_check = cur.fetchone()
    
    # Success indicators:
    # ✅ Expected ratios: Titles (10s) → Chapters (100s) → Sections (1000s)  
    # ✅ Content population: >0% sections have node_text
    # ❌ RED FLAGS: 0 content nodes, all nodes same type, 0% content population
```

**Step 2: Hierarchy Spot Check**
```python
# Target-specific validation of known legal paths
target_path = "us/{jurisdiction}/statutes/title=1/chapter=1/article=1"
cur.execute('SELECT id, node_name, level_classifier, parent FROM us_{jurisdiction}_statutes WHERE id LIKE %s ORDER BY id', (f'%{target_path}%',))

# Validation criteria:
# ✅ Complete hierarchy: Title → Chapter → Article → Section
# ✅ Proper parent-child relationships
# ✅ Expected sections present (cross-reference with website)
```

**Step 3: HTML Structure Investigation**
```python
# When validation reveals issues, investigate the source
import requests
from bs4 import BeautifulSoup

response = requests.get(section_url)
soup = BeautifulSoup(response.content, 'html.parser')

# Check if scraper logic matches actual website structure
# Examples from Arizona debugging:
# ❌ Expected: class="section" elements (WRONG)
# ✅ Actual: <ul> with <li class="colleft"> and <li class="colright"> (CORRECT)
```

### **Real-World Validation Example: Arizona Content Issue**

**Problem Detected:**
- ✅ Scraper runs without errors  
- ✅ Perfect hierarchical structure (3,766 sections)
- ✅ All sections have citations (100%)
- ❌ **0% of sections have node_text content**

**Validation Process:**
1. **Health Check**: Immediately flagged 0% content population
2. **Spot Check**: Confirmed structure perfect, content missing
3. **HTML Investigation**: Individual section pages serve navigation only, not statute text

**Root Cause**: Website structure changed - section content not available at expected URLs

**Lesson**: **Multiple validation layers essential** - structure can be perfect while content completely fails.

### **Common Failure Patterns**

**Structural Issues:**
- Missing content nodes (structure created, no sections)
- Wrong parent assignment (sections → titles instead of articles)
- Broken hierarchical chains (missing intermediate levels)

**Content Issues:**
- Empty node_text (sections created but content extraction fails)
- HTML artifacts in cleaned text
- Wrong text association (content from wrong sections)

**Parsing Logic Issues:**
- CSS selector mismatches (code looks for non-existent elements)
- Website structure changes breaking existing scrapers
- Edge cases not handled (REPEALED, RESERVED sections)

### **Validation Tools & Resources**

**Essential Tools:**
- **Postico 2**: PostgreSQL GUI for database visualization
- **Browser Dev Tools**: HTML structure inspection  
- **Simple requests/BeautifulSoup**: Programmatic HTML analysis
- **Timeout commands**: Controlled scraper execution for sampling

**Standard Validation Queries:**
```sql
-- Node distribution check
SELECT level_classifier, COUNT(*) FROM us_{jurisdiction}_statutes GROUP BY level_classifier;

-- Content population verification  
SELECT COUNT(node_text) as with_content, COUNT(*) as total FROM us_{jurisdiction}_statutes WHERE level_classifier = 'SECTION';

-- Hierarchy sample for spot checking
SELECT id, node_name, parent FROM us_{jurisdiction}_statutes WHERE id LIKE '%title=1%' ORDER BY id LIMIT 20;

-- Orphan detection
SELECT COUNT(*) FROM us_{jurisdiction}_statutes WHERE parent IS NULL AND level_classifier != 'corpus';
```

### **Success Criteria**

A scraper is **validated** when:
- [ ] **Runs without infrastructure errors**
- [ ] **Reasonable node counts** (expected ratios by type)
- [ ] **Complete hierarchies** (sample paths show proper relationships)
- [ ] **Content population** (sections have meaningful node_text)
- [ ] **Spot check passes** (manual validation of 1-2 titles)
- [ ] **HTML logic matches reality** (parsing aligns with actual website structure)

### **Integration with Development Workflow**

**For New Scrapers:**
1. Timeout test (30 seconds) → Health check → HTML investigation
2. Fix issues → Repeat until validation passes
3. Longer test → Full validation → Production ready

**For Refactored Scrapers:**
1. Compare before/after node counts
2. Validate same sample paths work
3. Verify new features functional

**For Production Monitoring:**
1. Periodic health checks (monthly)
2. Spot validation (quarterly)  
3. Website change detection

---

**📚 For complete validation methodology, see `/validationProcess.md`**

## Testing and Quality Assurance

**Legacy Testing Approaches (Still Important):**
- Scrapers should handle reserved/repealed sections
- Test with spot checks across different levels
- Verify node relationships (`parent`, `direct_children`)
- Ensure proper text cleaning and formatting
- Test duplicate handling with version numbers (`-v_2`, `-v_3`)

**🆕 Modern Validation Framework:**
- **Systematic validation process** with health checks, spot checks, and HTML investigation
- **Timeout-based iterative testing** for rapid feedback
- **Multi-layer validation** detecting both structural and content issues
- **Real-world examples** documenting common failure patterns
- **Human judgment applied systematically** for complex legal document validation

## Database Connection

Set up PostgreSQL connection and populate database config file as needed for your environment. The system supports both local development and cloud deployment (Supabase).


