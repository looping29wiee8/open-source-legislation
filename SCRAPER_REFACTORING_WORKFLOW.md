# Scraper Refactoring Workflow

This document provides step-by-step instructions for Claude Code instances to autonomously refactor and test individual jurisdiction scrapers. Each instance should use this workflow document alongside @CLAUDE.md for context and framework information.

## Mission Statement

**Objective**: Refactor a single jurisdiction's scraper to use the standardized Phase 3 framework while preserving all working parsing logic.

**Success Criteria**: 
- ✅ Scraper runs without runtime errors
- ✅ Creates expected database structure with correct node hierarchy
- ✅ Preserves all jurisdiction-specific parsing logic exactly
- ✅ Uses standardized framework components (BaseScraper, WebFetcher, TextProcessor, etc.)

## Pre-Conditions

Before starting, verify these conditions are met:

1. **Database Configuration**: Environment variables are set
   ```bash
   echo $OSL_DB_USER      # Should show database username
   echo $OSL_DB_PASSWORD  # Should show database password  
   echo $OSL_DB_HOST      # Should show "localhost"
   echo $OSL_DB_NAME      # Should show shared database name (e.g., "legislation")
   ```
   
   **Note**: Multiple Claude Code instances can safely share the same database since each jurisdiction writes to its own table (e.g., `us_az_statutes`, `us_ca_statutes`, etc.)

2. **Python Environment**: Dependencies are installed
   ```bash
   pip list | grep -E "(requests|beautifulsoup4|psycopg|pydantic)"
   ```

3. **Project Structure**: Verify you're in the correct directory
   ```bash
   pwd  # Should end with /open-source-legislation
   ls src/utils/base/  # Should show __init__.py, scraper.py, config.py, credentials.py
   ```

4. **Database Schema**: Each jurisdiction table follows the standard schema:
   ```sql
   CREATE TABLE us_{jurisdiction}_{corpus} (
       id text PRIMARY KEY,
       citation text NOT NULL,
       link text,
       status text,
       node_type text NOT NULL,
       top_level_title text,
       level_classifier text NOT NULL,
       number text,
       node_name text,
       alias text,
       node_text jsonb,
       definitions jsonb,
       core_metadata jsonb,
       processing jsonb,
       addendum jsonb,
       dates jsonb,
       summary text,
       hyde text[],
       agency text,
       parent text,
       direct_children text[],
       siblings text[],
       incoming_references jsonb,
       text_embedding vector(1536),
       summary_embedding vector(1536),
       hyde_embedding vector(1536),
       date_created timestamp DEFAULT CURRENT_TIMESTAMP,
       date_modified timestamp DEFAULT CURRENT_TIMESTAMP,
       name_embedding vector(1536)
   );
   ```
   
   The Pydantic `Node` model represents this schema. Tables are auto-created by the framework.

## Phase 1: Analysis & Backup

### Step 1: Locate Target Scraper & Initialize Progress Tracking
```bash
# Navigate to jurisdiction directory
cd src/scrapers/us/{jurisdiction}/statutes/

# List existing files
ls -la

# Expected files (may vary):
# - scrape{JURISDICTION}.py (main scraper file)
# - read{JURISDICTION}.py (optional)
# - process{JURISDICTION}.py (optional)
# - *.json or *.txt data files
```

**IMPORTANT**: Create a progress tracking file to document your work:

```bash
# Create progress tracking file
touch REFACTORING_PROGRESS.md
```

This file will serve as your working log and final report. It should be updated throughout the process to track:
- Analysis findings
- Refactoring steps completed
- Errors encountered and fixes applied
- Testing results
- Final validation status

### Step 2: Create Backup
```bash
# Create backup of original scraper
cp scrape{JURISDICTION}.py scrape{JURISDICTION}_original.py
echo "✅ Backup created: scrape{JURISDICTION}_original.py"
```

### Step 3: Analyze Current Implementation & Document Findings
Read the original scraper file and identify:

- **Path setup patterns** (usually 20+ lines at top)
- **Global variables** (`COUNTRY`, `JURISDICTION`, `CORPUS`, `TABLE_NAME`, etc.)
- **Database operations** (`insert_node()`, `pydantic_insert()`, raw SQL)
- **Web fetching** (`get_url_as_soup()`, `requests.get()`, Selenium usage)
- **Text processing** (`.get_text().strip()`, custom cleaning functions)
- **Main function structure**
- **Parsing logic patterns** (this must be preserved exactly)

**Document your analysis in REFACTORING_PROGRESS.md:**

```markdown
# {Jurisdiction} Scraper Refactoring Progress

**Date Started**: [Date]
**Jurisdiction**: {jurisdiction}
**Scraper File**: scrape{JURISDICTION}.py

## Phase 1: Analysis Complete ✅

### Current Implementation Analysis
- **Path Setup**: [describe pattern found]
- **Database Pattern**: [insert_node() / pydantic_insert() / raw SQL]
- **Web Fetching**: [get_url_as_soup() / requests / selenium]
- **Text Processing**: [simple .strip() / custom functions]
- **Main Function**: [file-based / URL iteration / etc.]

### Jurisdiction-Specific Logic to Preserve
- **HTML Parsing**: [list unique patterns]
- **Navigation Logic**: [list methods]
- **Data Extraction**: [list approaches]
- **Special Cases**: [list quirks/edge cases]

### URLs and Configuration
- **Base URL**: [extract from original]
- **TOC URL**: [extract from original]
- **Skip Titles**: [extract if present]

---
```

## Phase 2: Standardization Implementation

### Step 4: Replace Path Setup
Replace the path setup boilerplate (usually first 20+ lines):

```python
# REMOVE old pattern:
# import os
# import sys
# from pathlib import Path
# DIR = os.path.dirname(os.path.realpath(__file__))
# current_file = Path(__file__).resolve()
# src_directory = current_file.parent
# while src_directory.name != 'src' and src_directory.parent != src_directory:
#     src_directory = src_directory.parent
# project_root = src_directory.parent
# if str(project_root) not in sys.path:
#     sys.path.append(str(project_root))

# REPLACE with single line:
from src.utils.base import setup_project_path, BaseScraper, ConfigManager
setup_project_path()
```

### Step 5: Replace Global Variables
Convert global configuration to ScraperConfig:

```python
# REMOVE old pattern:
# COUNTRY = "us"
# JURISDICTION = "az"  # or other jurisdiction
# CORPUS = "statutes"
# TABLE_NAME = f"{COUNTRY}_{JURISDICTION}_{CORPUS}"
# BASE_URL = "https://www.azleg.gov"  # jurisdiction-specific
# TOC_URL = "https://www.azleg.gov/arstitle/"  # jurisdiction-specific
# USER = "will2"  # SECURITY ISSUE - hardcoded credentials

# REPLACE with ScraperConfig:
class {Jurisdiction}StatutesScraper(BaseScraper):
    def __init__(self, debug_mode: bool = False):
        config = ConfigManager.create_custom_config(
            country="us",
            jurisdiction="{jurisdiction_code}",  # e.g., "az", "ca", "tx"
            corpus="statutes",
            base_url="{jurisdiction_base_url}",  # Extract from original
            toc_url="{jurisdiction_toc_url}",    # Extract from original
            skip_title=0,  # Extract from original if present
            debug_mode=debug_mode
        )
        super().__init__(config)
```

### Step 6: Add Standardized Utilities
Initialize the Phase 3 standardized utilities:

```python
# Add to __init__ method:
        
        # Initialize standardized web fetcher
        self.web_fetcher = WebFetcher(
            delay_seconds=1.5,  # Adjust based on jurisdiction needs
            max_retries=3,
            timeout=30
        )
        
        # Jurisdiction-specific text processing configuration
        self.text_config = {
            "custom_replacements": {
                # Add jurisdiction-specific replacements
                # Example: "A.R.S.": "Arizona Revised Statutes"
            },
            "citation_patterns": [
                # Add jurisdiction-specific citation patterns
                # Example: r'A\.R\.S\.\s*§\s*[\d-]+'
            ],
            "addendum_patterns": [
                # Add jurisdiction-specific addendum patterns
                # Example: r'\[Added by Laws (\d+),.*?\]'
            ]
        }
```

### Step 7: Convert Main Function
Wrap the existing main logic in scrape_implementation():

```python
# REMOVE old main function:
# def main():
#     corpus_node = insert_jurisdiction_and_corpus_node(COUNTRY, JURISDICTION, CORPUS)
#     # ... existing logic ...

# REPLACE with:
    def scrape_implementation(self) -> None:
        """
        {Jurisdiction}-specific scraping logic.
        
        PRESERVED: All original parsing logic exactly as-is
        UPDATED: Infrastructure to use standardized framework
        """
        self.logger.info("Starting {jurisdiction} statutes scraping")
        
        # PRESERVE the original main function logic here
        # Just update the infrastructure calls (see next steps)
```

### Step 8: Update Infrastructure Calls
Systematically replace infrastructure calls while preserving logic:

**Web Fetching:**
```python
# OLD: soup = get_url_as_soup(url)
# NEW: soup = self.web_fetcher.get_soup(url)

# OLD: response = requests.get(url)
# NEW: response = self.web_fetcher.get_raw_response(url)
```

**Text Processing:**
```python
# OLD: text = element.get_text().strip()
# NEW: text = TextProcessor.clean_text(element)

# OLD: text = get_text_clean(element)
# NEW: text = TextProcessor.clean_text(element)
```

**Node Creation:**
```python
# OLD: Manual Node() creation
# node = Node(
#     id=node_id,
#     name=name,
#     link=link,
#     node_type="structure",
#     level_classifier="TITLE",
#     # ... other fields
# )

# NEW: Use NodeFactory helpers
node = self.create_structure_node(
    parent_id=parent_id,
    level_classifier="title",
    number=number,
    name=name,
    link=link,
    top_level_title=top_level_title
)
```

**Database Operations:**
```python
# OLD: insert_node(node, TABLE_NAME, True, True)
# NEW: self.insert_node_safely(node)

# OLD: util.pydantic_insert(TABLE_NAME, [node], user=USER)
# NEW: self.insert_node_safely(node)

# For batch operations:
# OLD: Multiple individual inserts
# NEW: self.batch_insert_nodes(nodes_list, ignore_duplicates=True)
```

### Step 9: Add Standardized Main Function
```python
# Add at the end of file:
def main():
    """Main entry point for {jurisdiction} scraper."""
    try:
        scraper = {Jurisdiction}StatutesScraper(debug_mode=True)
        scraper.scrape()
        
    except Exception as e:
        print(f"Scraping failed: {e}")
        raise

if __name__ == "__main__":
    main()
```

**Update REFACTORING_PROGRESS.md:**
```markdown
## Phase 2: Refactoring Complete ✅

### Changes Made
- ✅ Replaced path setup with `setup_project_path()`
- ✅ Converted global variables to `ScraperConfig`
- ✅ Migrated to `BaseScraper` framework
- ✅ Added standardized web fetcher
- ✅ Added jurisdiction-specific text configuration
- ✅ Updated infrastructure calls while preserving parsing logic
- ✅ Added standardized main function

### Configuration Extracted
- **Country**: us
- **Jurisdiction**: {jurisdiction}
- **Corpus**: statutes
- **Base URL**: {base_url}
- **TOC URL**: {toc_url}

---
```

## Phase 3: Testing & Debugging

### Step 10: First Test Run
```bash
cd src/scrapers/us/{jurisdiction}/statutes/
python scrape{JURISDICTION}.py
```

**Expected Outcome**: Errors (this is normal for first run)

### Step 11: Debug Common Errors

**Error Type 1: Import Errors**
```python
# Error: ModuleNotFoundError: No module named 'src.utils.base'
# Fix: Add path setup at the very top
import sys
from pathlib import Path
current_file = Path(__file__).resolve()
while current_file.name != 'src':
    current_file = current_file.parent
sys.path.insert(0, str(current_file.parent))

# Then import framework
from src.utils.base import setup_project_path, BaseScraper, ConfigManager
setup_project_path()
```

**Error Type 2: Environment Variable Errors**
```python
# Error: ValueError: OSL_DB_USER environment variable not set
# Fix: Check environment variables are properly set
import os
required_vars = ['OSL_DB_USER', 'OSL_DB_PASSWORD', 'OSL_DB_HOST', 'OSL_DB_NAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"❌ Missing environment variables: {missing_vars}")
    print("Please set them before running the scraper")
    print("Example: Copy .env.example to .env and fill in your values")
    return
```

**Error Type 3: Database Connection Errors**
```python
# Error: psycopg2.OperationalError: could not connect to server
# Fix: Test database connection
try:
    scraper = {Jurisdiction}StatutesScraper(debug_mode=True)
    # Test database connection
    test_result = scraper.db.test_connection()
    print(f"✅ Database connection successful: {test_result}")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    print("Please check your database configuration")
    return
```

**Error Type 4: Attribute Errors**
```python
# Error: AttributeError: 'NoneType' object has no attribute 'find'
# Fix: Add null checks to preserved parsing logic
container = soup.find(class_="target-class")
if not container:
    self.logger.warning(f"Could not find target container in {url}")
    return

# Continue with preserved logic...
```

### Step 12: Iterative Debugging Process

For each error encountered:

1. **Classify the error**:
   - Import/path issues → Fix imports
   - Environment/config issues → Fix configuration 
   - Database issues → Fix database connection
   - Parsing logic issues → Preserve logic, add safety checks

2. **Apply targeted fix**:
   - Make minimal changes to preserve working logic
   - Focus on infrastructure, not parsing patterns

3. **Test the fix**:
   ```bash
   python scrape{JURISDICTION}.py
   ```

4. **Repeat until no errors**

### Step 13: Validate Success & Document Testing

Once the scraper runs without errors, validate the output:

```python
# Add validation logic to scraper
def validate_output(self):
    """Validate that scraper produced expected results."""
    
    # Check database has nodes
    nodes = self.db.get_all_nodes()
    assert len(nodes) > 0, "No nodes were created"
    
    # Check node types are valid
    for node in nodes:
        assert node.id and node.id.raw_id, f"Node missing ID: {node}"
        assert node.node_type in ["structure", "content"], f"Invalid node type: {node.node_type}"
        assert node.level_classifier, f"Node missing level classifier: {node}"
        
    # Verify database schema compliance
    # Each table should follow the standard schema with required fields:
    # id (text PRIMARY KEY), citation, node_type, level_classifier, etc.
    
    # Check hierarchy makes sense
    title_nodes = [n for n in nodes if n.level_classifier == "TITLE"]
    chapter_nodes = [n for n in nodes if n.level_classifier == "CHAPTER"]
    section_nodes = [n for n in nodes if n.level_classifier == "SECTION"]
    
    print(f"✅ Validation successful!")
    print(f"Created {len(nodes)} total nodes")
    print(f"  - {len(title_nodes)} titles")
    print(f"  - {len(chapter_nodes)} chapters")
    print(f"  - {len(section_nodes)} sections")
    
    return True

# Add to end of scrape_implementation():
self.validate_output()
```

**Update REFACTORING_PROGRESS.md:**
```markdown
## Phase 3: Testing & Debugging Complete ✅

### Debugging History
- **Attempt 1**: [Error encountered] → [Fix applied]
- **Attempt 2**: [Error encountered] → [Fix applied]
- **Final Run**: ✅ Success - No errors

### Validation Results
- ✅ Scraper runs without runtime errors
- ✅ Database table `us_{jurisdiction}_{corpus}` created
- ✅ Nodes created with correct hierarchy
- ✅ All required fields populated
- ✅ Framework components properly integrated

### Database Statistics
- **Total Nodes**: [number]
- **Title Nodes**: [number]
- **Chapter Nodes**: [number]
- **Section Nodes**: [number]

---
```

## Phase 4: Final Validation & Reporting

### Step 14: Performance Check
```python
# Add timing and statistics
import time

def scrape_implementation(self):
    start_time = time.time()
    self.logger.info("Starting {jurisdiction} statutes scraping")
    
    # ... existing logic ...
    
    # Final statistics
    end_time = time.time()
    execution_time = end_time - start_time
    
    self.logger.info(f"✅ Scraping completed successfully")
    self.logger.info(f"Execution time: {execution_time:.1f} seconds")
    
    # Show comprehensive statistics  
    self._show_comprehensive_stats()

def _show_comprehensive_stats(self):
    """Display detailed statistics about the scraping process."""
    try:
        # Database statistics
        db_stats = self.db.get_stats()
        self.logger.info("=== DATABASE STATISTICS ===")
        self.logger.info(f"Total nodes: {db_stats.get('total_nodes', 0)}")
        
        if 'by_type' in db_stats:
            for node_type, count in db_stats['by_type'].items():
                self.logger.info(f"  {node_type}: {count}")
        
        # Web fetching statistics
        web_stats = self.web_fetcher.get_stats()
        self.logger.info("=== WEB FETCHING STATISTICS ===")
        self.logger.info(f"Requests made: {web_stats['requests_made']}")
        self.logger.info(f"Success rate: {web_stats['success_rate']:.2%}")
        self.logger.info(f"Average delay: {web_stats['average_delay']:.1f}s")
        
    except Exception as e:
        self.logger.warning(f"Could not retrieve statistics: {e}")
```

### Step 15: Generate Completion Report
```python
def generate_completion_report(self):
    """Generate final report of refactoring process."""
    
    report = {
        "jurisdiction": "{jurisdiction}",
        "status": "completed",
        "refactoring_date": datetime.now().isoformat(),
        "framework_version": "Phase 3 (Database + Text + Web utilities)",
        "changes_made": [
            "✅ Replaced path setup with setup_project_path()",
            "✅ Migrated to BaseScraper framework",
            "✅ Updated database operations to use DatabaseManager", 
            "✅ Replaced web fetching with standardized WebFetcher",
            "✅ Updated text processing to use TextProcessor",
            "✅ Added proper error handling and logging",
            "✅ Added environment-based credential management"
        ],
        "preserved_logic": [
            "✅ All jurisdiction-specific HTML parsing patterns",
            "✅ Complex navigation and link extraction logic",
            "✅ Title/chapter/section identification methodology", 
            "✅ Text extraction and cleaning patterns",
            "✅ Any jurisdiction-specific quirks and edge cases"
        ],
        "validation_results": {
            "runtime_success": True,
            "nodes_created": "TBD - filled by validate_output()",
            "database_structure": "Valid",
            "error_count": 0
        },
        "next_steps": [
            "Scraper ready for production use",
            "Consider running process{JURISDICTION}.py for embeddings",
            "Monitor for any jurisdiction-specific edge cases"
        ]
    }
    
    self.logger.info("=== REFACTORING COMPLETION REPORT ===")
    for key, value in report.items():
        if isinstance(value, list):
            self.logger.info(f"{key}:")
            for item in value:
                self.logger.info(f"  {item}")
        else:
            self.logger.info(f"{key}: {value}")
    
    return report

# Call at end of scrape_implementation()
completion_report = self.generate_completion_report()
```

**Final Update to REFACTORING_PROGRESS.md:**
```markdown
## Phase 4: Final Validation & Reporting Complete ✅

### Performance Metrics
- **Execution Time**: [time in seconds/minutes]
- **Web Requests Made**: [number]
- **Request Success Rate**: [percentage]
- **Average Delay**: [seconds]

### Final Status: ✅ SUCCESS

The {jurisdiction} scraper has been successfully refactored to use the Phase 3 standardized framework. All jurisdiction-specific parsing logic has been preserved while infrastructure has been standardized.

### Files Modified
- ✅ `scrape{JURISDICTION}.py` - Refactored to use standardized framework
- ✅ `scrape{JURISDICTION}_original.py` - Backup of original implementation
- ✅ `REFACTORING_PROGRESS.md` - This progress report

### Next Steps
- Scraper is ready for production use
- Consider running `process{JURISDICTION}.py` for embeddings generation
- Monitor for any jurisdiction-specific edge cases in production

---

**Refactoring completed on**: [Date]
**Framework version**: Phase 3 (Database + Text + Web utilities)
**Claude Code instance**: [Instance identifier if applicable]
```

## Emergency Procedures

### If Refactoring Fails
```bash
# Restore original scraper
cp scrape{JURISDICTION}_original.py scrape{JURISDICTION}.py
echo "⚠️  Restored original scraper due to refactoring failure"

# Test original still works
python scrape{JURISDICTION}.py
```

### If Stuck on Complex Error
```python
# Add detailed error logging
import traceback

try:
    # Problematic code section
    pass
except Exception as e:
    self.logger.error(f"DETAILED ERROR CONTEXT:")
    self.logger.error(f"Error: {e}")
    self.logger.error(f"Type: {type(e)}")
    self.logger.error(f"Traceback: {traceback.format_exc()}")
    self.logger.error(f"Current URL: {url if 'url' in locals() else 'None'}")
    self.logger.error(f"Current element: {element if 'element' in locals() else 'None'}")
    raise
```

## Success Checklist

Before declaring refactoring complete, verify:

- [ ] ✅ Scraper runs without runtime errors
- [ ] ✅ Environment variables are properly configured 
- [ ] ✅ Database connection works and creates expected schema
- [ ] ✅ Nodes are created with correct hierarchy (titles → chapters → sections)
- [ ] ✅ All original parsing logic is preserved exactly
- [ ] ✅ StandardizedFramework components are properly integrated
- [ ] ✅ Performance is acceptable (reasonable execution time)
- [ ] ✅ Comprehensive statistics are displayed
- [ ] ✅ Error handling is robust
- [ ] ✅ Code follows standardized patterns from Phase 3

## Final Notes

**Critical Reminders:**
1. **Preserve ALL jurisdiction-specific parsing logic** - these patterns were developed through extensive trial and error
2. **Only standardize infrastructure** - path setup, database operations, web fetching, text processing
3. **Test frequently** - run the scraper after each major change
4. **Use the framework helpers** - BaseScraper provides many utilities to simplify common operations
5. **Document any unusual patterns** - add comments explaining jurisdiction-specific quirks

The goal is a scraper that works identically to the original but uses the standardized framework for all infrastructure operations.