**WARNING: THIS FILE IS OUTDATED. NEEDS TO BE UPDATED AFTER SCRAPER STANDARDIZATION IS COMPLETED**

# Claude Code Instructions for Scraper Refactoring

This document provides standardized instructions for Claude Code instances working on refactoring scrapers in the open-source-legislation project.

## Project Context

You are working on the open-source-legislation project, which democratizes access to global legislative data by providing scraped and processed legislation in a unified SQL schema format. Your task is to refactor existing scrapers to use standardized patterns, improve security, and eliminate code duplication.

## Critical Security Requirements

### 🚨 NEVER hardcode credentials
```python
# ❌ NEVER DO THIS - Security vulnerability
user = "will2"
USER = "madeline or will or will2"

# ✅ ALWAYS DO THIS - Use environment variables
user = CredentialManager.get_database_user()
```

### 🚨 Check for existing hardcoded credentials
Before starting any work, search the files for hardcoded usernames and replace them with secure credential management.

## Architecture Overview

### Core Components You'll Work With

1. **Pydantic Models** (`src/utils/pydanticModels.py`)
   - `Node`: Core legislation model (structure/content types)
   - `NodeID`: Hierarchical identifier system  
   - `NodeText`: Paragraph-based text content
   - `DefinitionHub`: Legal term definitions
   - `ReferenceHub`: Cross-references between nodes

2. **Scraping Utilities** (`src/utils/scrapingHelpers.py`)
   - `insert_jurisdiction_and_corpus_node()`: Creates base hierarchy
   - `insert_node()`: Handles Node insertion with versioning
   - `get_url_as_soup()`: Web fetching with retry logic

3. **Database Functions** (`src/utils/utilityFunctions.py`)
   - `pydantic_insert()`: Insert Pydantic models to database
   - `pydantic_select()`: Query database returning Pydantic models

## Refactoring Standards

### File Structure Pattern
Every scraper should follow this pattern:
```
src/scrapers/{country}/{jurisdiction}/{corpus}/
├── read{JURISDICTION}.py     # Extract top-level title links
├── scrape{JURISDICTION}.py   # Main scraping logic  
├── process{JURISDICTION}.py  # Generate embeddings, relationships
└── refactoring.md           # Document jurisdiction-specific patterns
```

### Standard Imports Pattern
Replace the verbose path setup with:
```python
from src.utils.base import setup_project_path
setup_project_path()

from src.utils.scrapers import BaseScraper, ScraperConfig
from src.utils.credentials import CredentialManager
from src.utils.factories import NodeFactory
from src.utils.database import DatabaseManager
from src.utils.text import TextProcessor
from src.utils.web import WebFetcher
```

### Configuration Pattern
Replace hardcoded globals with:
```python
config = ScraperConfig(
    country="us",
    jurisdiction="az",  # Replace with your jurisdiction
    corpus="statutes",
    base_url="https://www.azleg.gov",  # Replace with your base URL
    toc_url="https://www.azleg.gov/arstitle/",  # Replace with your TOC URL
    skip_title=0,  # Adjust as needed
    reserved_keywords=["REPEALED", "RESERVED"],  # Adjust as needed
    debug_mode=False
)
```

## Step-by-Step Refactoring Process

### Step 1: Security Audit
1. Search for hardcoded usernames/credentials
2. Replace with `CredentialManager.get_database_user()`
3. Update any database calls to use the user parameter properly

### Step 2: Extract Configuration
1. Identify all global variables (COUNTRY, JURISDICTION, BASE_URL, etc.)
2. Convert to `ScraperConfig` instance
3. Remove global variable declarations

### Step 3: Refactor Main Structure
Transform the main function from:
```python
def main():
    corpus_node = insert_jurisdiction_and_corpus_node(COUNTRY, JURISDICTION, CORPUS)
    # jurisdiction-specific logic...
```

To:
```python
class {Jurisdiction}Scraper(BaseScraper):
    def scrape_implementation(self) -> None:
        # Move jurisdiction-specific logic here
        pass

def main():
    config = ScraperConfig(...)  # Your config
    user = CredentialManager.get_database_user()
    scraper = {Jurisdiction}Scraper(config, user)
    scraper.scrape()
```

### Step 4: Standardize Node Creation
Replace manual Node construction with factory methods:
```python
# ❌ Before
node = Node(
    id=node_id,
    node_type="structure",
    level_classifier="TITLE",
    # ... many manual fields
)

# ✅ After  
node = NodeFactory.create_structure_node(
    parent_id=parent_id,
    level_classifier="title",
    number=title_number,
    name=title_name,
    link=url,
    top_level_title=top_level_title
)
```

### Step 5: Standardize Database Operations
Replace direct database calls with DatabaseManager:
```python
# ❌ Before
insert_node(node, TABLE_NAME, True, True)  # Unclear boolean flags

# ✅ After
self.db.insert_node(node, ignore_duplicate=True, debug=self.config.debug_mode)
```

### Step 6: Standardize Text Processing
Replace custom text cleaning with TextProcessor:
```python
# ❌ Before
text = element.get_text().strip()
if text == "":
    continue

# ✅ After
text = TextProcessor.clean_text(element)
if not text:
    continue
```

### Step 7: Standardize Web Fetching
Replace manual URL fetching with WebFetcher:
```python
# ❌ Before
response = urllib.request.urlopen(url)
data = response.read()
text = data.decode('utf-8')
soup = BeautifulSoup(text, features="html.parser")

# ✅ After
soup = self.fetcher.get_soup(url)
```

### Step 8: Improve Error Handling
Replace bare except statements:
```python
# ❌ Before
try:
    # some operation
except:
    print("Error occurred")

# ✅ After
try:
    # some operation
except SpecificException as e:
    self.logger.error(f"Specific error description: {e}")
    # Appropriate recovery action
```

## Common Patterns by Jurisdiction Type

### Simple State Scrapers (Alabama, Arizona style)
- Flat hierarchy: Title → Chapter → Section
- Single webpage per section
- Simple text extraction

**Template:**
```python
class {State}Scraper(BaseScraper):
    def scrape_implementation(self) -> None:
        self.fetcher = WebFetcher(delay_seconds=self.config.delay_seconds)
        
        for title_url in self._get_title_urls():
            self._scrape_title(title_url)
            
    def _scrape_title(self, url: str) -> None:
        soup = self.fetcher.get_soup(url)
        # Extract title info and create title node
        # Find chapters and scrape each
        
    def _scrape_chapter(self, url: str, parent_id: str) -> None:
        soup = self.fetcher.get_soup(url)
        # Extract chapter info and create chapter node
        # Find sections and scrape each
```

### Complex State Scrapers (California style)
- Deep hierarchy: Title → Division → Part → Chapter → Article → Section
- Multiple navigation patterns
- Complex text structures

**Template:**
```python
class {State}Scraper(BaseScraper):
    def scrape_implementation(self) -> None:
        self.fetcher = WebFetcher(delay_seconds=self.config.delay_seconds)
        
        for code_url in self._get_code_urls():
            self._scrape_code_recursively(code_url, self.config.corpus_id)
            
    def _scrape_code_recursively(self, url: str, parent_id: str) -> None:
        soup = self.fetcher.get_soup(url)
        level_type = self._determine_level_type(soup)
        
        if level_type == "content":
            self._scrape_section(soup, url, parent_id)
        else:
            node = self._create_structure_node(soup, url, parent_id, level_type)
            for child_url in self._get_child_urls(soup):
                self._scrape_code_recursively(child_url, node.node_id)
```

### Federal Scrapers (eCFR, USC style)
- Complex regulations with frequent cross-references
- Large datasets requiring batch processing
- Multiple document formats

**Template:**
```python
class {Federal}Scraper(BaseScraper):
    def scrape_implementation(self) -> None:
        self.fetcher = WebFetcher(delay_seconds=self.config.delay_seconds)
        
        for title_num in self._get_title_numbers():
            self._scrape_title_batch(title_num)
            
    def _scrape_title_batch(self, title_num: str) -> None:
        nodes_to_insert = []
        
        for part_url in self._get_part_urls(title_num):
            part_nodes = self._scrape_part(part_url)
            nodes_to_insert.extend(part_nodes)
            
        self.db.batch_insert(nodes_to_insert)
```

## Files You Should NOT Modify

### Core Utilities (Will be updated separately)
- `src/utils/pydanticModels.py`
- `src/utils/utilityFunctions.py` 
- `src/utils/scrapingHelpers.py`
- `src/utils/processingHelpers.py`

### Configuration Files
- `CLAUDE.md`
- `requirements.txt`
- Database schema files

### Documentation
- `README.md`
- `contributing.md`

## Quality Checklist

Before completing any scraper refactoring, verify:

### ✅ Security
- [ ] No hardcoded credentials anywhere in the code
- [ ] All database calls use proper user parameter
- [ ] Environment variables used for sensitive data

### ✅ Code Structure  
- [ ] Inherits from `BaseScraper`
- [ ] Uses `ScraperConfig` for configuration
- [ ] Implements `scrape_implementation()` method
- [ ] Uses `NodeFactory` for Node creation

### ✅ Database Operations
- [ ] Uses `DatabaseManager` for all database operations
- [ ] Consistent duplicate handling strategy
- [ ] Proper error handling for database operations

### ✅ Error Handling
- [ ] No bare `except:` statements
- [ ] Specific exception types caught
- [ ] Meaningful error messages
- [ ] Appropriate recovery actions

### ✅ Text Processing
- [ ] Uses `TextProcessor.clean_text()` consistently
- [ ] Proper handling of empty text
- [ ] Consistent NodeText creation patterns

### ✅ Web Operations
- [ ] Uses `WebFetcher` for all HTTP requests
- [ ] Appropriate rate limiting
- [ ] Retry logic for failed requests

### ✅ Logging
- [ ] Uses standardized logger from `BaseScraper`
- [ ] Informative log messages at appropriate levels
- [ ] No excessive print statements

## Common Errors to Avoid

### 1. Mixing Old and New Patterns
```python
# ❌ Don't mix patterns
config = ScraperConfig(...)  # New pattern
TABLE_NAME = f"{COUNTRY}_{JURISDICTION}_{CORPUS}"  # Old pattern
```

### 2. Inconsistent Node ID Generation
```python
# ❌ Don't manually construct IDs
node_id = f"{parent_id}/section={number}"

# ✅ Use NodeID class
parent_node_id = NodeID(raw_id=parent_id)
node_id = parent_node_id.add_level("section", number)
```

### 3. Ignoring Reserved Sections
```python
# ✅ Always check for reserved status
status = NodeFactory._determine_status(node_name, explicit_status)
if status != "reserved":
    # Only scrape content for non-reserved sections
    node_text = self._extract_content(soup)
```

### 4. Inconsistent Citation Formats
Follow the jurisdiction's standard citation format:
- State statutes: `"{STATE_CODE} § {section_number}"`
- Federal CFR: `"{title} CFR {section}"`
- US Code: `"{title} U.S.C. § {section}"`

## Testing Your Refactored Scraper

### 1. Validation Test
```python
from src.utils.validation import DataValidator

# Test that your scraper follows patterns
errors = DataValidator.validate_scraper_compliance(YourScraperClass)
assert len(errors) == 0, f"Scraper validation errors: {errors}"
```

### 2. Sample Run Test
Run your refactored scraper on a small subset:
```python
config.skip_title = 45  # Start from a later title for testing
config.debug_mode = True
scraper = YourScraper(config, user)
scraper.scrape()
```

### 3. Database Validation
```python
# Verify nodes were inserted correctly
nodes = db.get_nodes_by_parent(corpus_id)
assert len(nodes) > 0, "No nodes found in database"

# Verify proper hierarchy
for node in nodes:
    validation_errors = DataValidator.validate_node(node)
    assert len(validation_errors) == 0, f"Node validation errors: {validation_errors}"
```

## Getting Help

If you encounter jurisdiction-specific patterns that don't fit the standard templates:

1. **Document the pattern** in the jurisdiction's `refactoring.md` file
2. **Check similar jurisdictions** for comparable patterns  
3. **Extend the base classes** if needed for special cases
4. **Add utility functions** for commonly needed operations

## Success Criteria

Your refactoring is complete when:

1. **Security**: No hardcoded credentials remain
2. **Consistency**: Uses all standard patterns and utilities  
3. **Maintainability**: Code is clear and follows established conventions
4. **Functionality**: Produces identical database output to original scraper
5. **Error Handling**: Robust error handling with meaningful messages
6. **Documentation**: Clear documentation of any jurisdiction-specific patterns

Remember: The goal is not just to make the code work, but to make it maintainable, secure, and consistent with the established patterns for the entire project.