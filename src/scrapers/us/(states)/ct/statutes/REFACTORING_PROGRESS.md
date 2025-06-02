# Connecticut Scraper Refactoring Progress

**Date Started**: January 6, 2025
**Jurisdiction**: Connecticut (CT)
**Scraper File**: scrapeCT.py
**Framework Version**: Phase 3 Enhanced (Database + Text + Web utilities with debugging workflow)

## Phase 1: Analysis Complete 

### Current Implementation Analysis

**Path Setup**: Traditional 15-line path setup pattern using `os`, `sys`, and `Path` to find and add project root to sys.path

**Database Pattern**: Uses legacy `insert_node()` from scrapingHelpers.py with `TABLE_NAME` and `ignore_duplicate=True`

**Web Fetching**: Uses `get_url_as_soup()` from scrapingHelpers.py for HTTP requests

**Text Processing**: Basic `.get_text().strip()` operations with manual text cleaning

**Main Function**: Direct function-based approach with `insert_jurisdiction_and_corpus_node()`

### Jurisdiction-Specific Logic to Preserve

**HTML Parsing Patterns**:
- Uses `soup.find(id="titles.htm")` to locate content container
- Extracts titles from `class_="left_38pct"` elements 
- Handles both active and reserved titles with try/except pattern
- Uses `next_sibling.next_sibling` navigation pattern
- Processes chapters from `class_="left_40pct"` elements
- Sections extracted from `class_="toc_catchln"` elements with anchor links

**Navigation Logic**:
- Three-level hierarchy: Title ’ Chapter ’ Section
- Reserved sections detected via `<b>` tag presence
- Complex section content extraction using `iterator.next_sibling.next_sibling` pattern
- Handles different paragraph classes: `source-first`, `history-first`

**Data Extraction**:
- Citation format: `"Conn. Gen. Stat. § {title}-{section}"`
- Section numbering from href fragments (`href.replace("#","")`)
- Links are relative URLs requiring BASE_URL concatenation
- Addendum extraction for source and history information
- Reference extraction from anchor tags within paragraphs

**Special Cases**:
- Reserved title handling with status="reserved"
- Complex content parsing that walks through siblings until navigation table
- ReferenceHub creation for cross-references
- AddendumType creation for source/history metadata
- Annotations collection in core_metadata

### URLs and Configuration
- **Base URL**: "https://www.cga.ct.gov"
- **TOC URL**: "https://www.cga.ct.gov/current/pub/titles.htm"
- **Skip Titles**: 0 (starts from beginning)
- **Reserved Keywords**: [] (empty, but uses <b> tag detection)

### Key Infrastructure Elements to Standardize
- Path setup boilerplate (lines 20-34)
- Global variables (lines 41-52)
- `get_url_as_soup()` calls in scrape_titles(), scrape_chapters(), scrape_sections()
- `insert_node()` calls with TABLE_NAME parameter
- Manual Node() construction throughout
- `insert_jurisdiction_and_corpus_node()` in main()

---