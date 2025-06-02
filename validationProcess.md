# Scraper Validation Process

**The Challenge**: Validating legislative scrapers is inherently difficult because we're extracting complex legal hierarchies into a knowledge graph structure. Unlike traditional software testing, there's no single "correct answer" to validate against.

## Core Validation Philosophy

**Legislative data is a hierarchical knowledge graph stored in PostgreSQL.** We're not just scraping text - we're modeling the complex structural relationships between titles, chapters, articles, and sections. Validation must account for both **structural integrity** and **content accuracy**.

## Two Types of Errors

### 1. "Compiler Errors" - Infrastructure Failures
- Scraper fails to run due to configuration issues
- Database connection problems  
- Import/dependency errors
- Environment variable issues

**Detection**: Immediate - scraper crashes or throws exceptions
**Fix**: Debug the infrastructure, check logs, verify setup

### 2. "Runtime Errors" - Logic/Content Failures  
- Wrong hierarchical structure extracted
- Missing or incorrectly parsed content
- Sections created under wrong parents
- node_text extraction failures

**Detection**: Requires manual validation and spot checking
**Fix**: Analyze HTML structure, debug parsing logic

## Primary Validation Method: Progressive Timeout-Based Testing

**⚠️ CRITICAL FOR CLAUDE CODE INSTANCES: ALWAYS use timeout-based validation for scraper debugging. Running scrapers without timeouts will prevent you from getting feedback for hours.**

### **Mandatory Timeout Usage for Debugging**

**🚨 NEVER run a scraper without timeout conditions during debugging/validation**

```bash
# ✅ CORRECT - Use validation mode for quick feedback
python scrapeJURISDICTION_standardized.py --mode clean --validation --debug

# ✅ CORRECT - Use explicit timeouts  
python scrapeJURISDICTION_standardized.py --mode clean --timeout 2 --debug

# ❌ WRONG - Will run for hours without feedback
python scrapeJURISDICTION_standardized.py --mode clean
```

**The gold standard for validation is progressive timeout-based testing followed by manual spot checking with database visualization tools like Postico 2.**

### **Progressive Validation Workflow (MANDATORY for Claude Code)**

**⚡ Step 1: Quick Timeout Test (30 seconds - 2 minutes)**
```bash
# Ultra-fast first test - get immediate feedback
python scrapeJURISDICTION_standardized.py --mode clean --validation --debug
# OR
python scrapeJURISDICTION_standardized.py --mode clean --timeout 1 --max-titles 1 --debug
```

**📊 Step 2: Immediate Health Check**
```python
# Run immediately after timeout test to validate sample data
from src.utils.utilityFunctions import db_connect
conn = db_connect()
with conn.cursor() as cur:
    cur.execute('SELECT level_classifier, COUNT(*) FROM us_JURISDICTION_statutes GROUP BY level_classifier')
    breakdown = cur.fetchall()
    print(f'Node breakdown: {breakdown}')
    
    cur.execute('SELECT COUNT(node_text) FROM us_JURISDICTION_statutes WHERE level_classifier = %s', ('SECTION',))
    content_count = cur.fetchone()[0] 
    print(f'Sections with content: {content_count}')
```

**🔄 Step 3: Iterative Testing (if issues found)**
```bash
# If step 1-2 reveal issues, debug with longer timeouts
python scrapeJURISDICTION_standardized.py --mode clean --timeout 5 --max-titles 3 --debug

# Target specific problem areas
python scrapeJURISDICTION_standardized.py --mode skip --skip-title 5 --timeout 2 --debug
```

**✅ Step 4: Full Validation (only if timeout tests pass)**
```bash
# Only run full scraper after timeout validation succeeds
python scrapeJURISDICTION_standardized.py --mode clean
```

### Traditional Spot Check Process (After Timeout Validation)

1. **Pick a Representative Sample**: Choose 1-2 titles that represent typical complexity
2. **Follow the Hierarchy**: Start from title → chapter → article → section
3. **Verify Each Level**: Check that parent-child relationships are correct
4. **Content Deep Dive**: Examine node_text, citations, and metadata
5. **Cross-Reference**: Compare database content to original website

### What to Look For

#### **Structural Validation**
- [ ] **Complete Hierarchy**: All expected levels present (title → chapter → article → section)
- [ ] **Correct Parent IDs**: Each node's parent field points to the right parent
- [ ] **Logical Ordering**: Siblings appear in expected numerical/alphabetical order
- [ ] **No Orphans**: All nodes (except corpus) have valid parents
- [ ] **Consistent Naming**: Node names follow jurisdiction's formatting patterns

#### **Content Validation** 
- [ ] **node_text Population**: Section nodes have meaningful content in node_text field
- [ ] **Citation Accuracy**: Citations match jurisdiction's formatting (e.g., "A.R.S. § 1-101")
- [ ] **Link Validity**: Node links point to correct web pages
- [ ] **Metadata Capture**: Addenda, historical notes, references properly extracted
- [ ] **Text Cleanliness**: No HTML artifacts, proper formatting, consistent whitespace

#### **Count Sanity Checks**
- [ ] **Expected Ratios**: Titles (10s) → Chapters (100s) → Sections (1000s)
- [ ] **Zero Content Nodes**: If 0 content nodes exist, section processing is broken
- [ ] **Reasonable Totals**: Compare to known legislative corpus size

## Validation Tools & Techniques

### Database Queries for Health Checks

```sql
-- Overall node distribution
SELECT level_classifier, COUNT(*) 
FROM us_{jurisdiction}_statutes 
GROUP BY level_classifier 
ORDER BY COUNT(*) DESC;

-- Check for orphaned nodes  
SELECT COUNT(*) as orphan_count
FROM us_{jurisdiction}_statutes 
WHERE parent IS NULL AND level_classifier != 'corpus';

-- Sample hierarchy for spot checking
SELECT id, name, level_classifier, parent
FROM us_{jurisdiction}_statutes 
WHERE id LIKE '%title=1%' 
ORDER BY id;

-- Content population check
SELECT 
  COUNT(*) as total_sections,
  COUNT(node_text) as sections_with_text,
  COUNT(citation) as sections_with_citations
FROM us_{jurisdiction}_statutes 
WHERE level_classifier = 'section';
```

### HTML Structure Investigation

When validation reveals issues, investigate the source:

1. **Fetch Sample Pages**: Get representative HTML from the jurisdiction's website
2. **Inspect Element Structure**: Use browser dev tools or BeautifulSoup to understand hierarchy
3. **Document Patterns**: Note the CSS selectors and HTML patterns used
4. **Compare to Code**: Check if scraper logic matches actual HTML structure

Example from Arizona debugging:
```python
# Expected: class="section" elements (WRONG)
section_elements = article.find_all(class_="section")  # Returns []

# Actual: ul > li structure (CORRECT)  
section_lists = article.find_all("ul")
for section_list in section_lists:
    left_items = section_list.find_all("li", class_="colleft")  # Statute numbers
    right_items = section_list.find_all("li", class_="colright")  # Statute titles
```

## Common Failure Patterns

Based on experience with Arizona and other jurisdictions:

### **Structural Issues**
- **Missing Content Nodes**: Structure nodes created but no sections (Arizona's original issue)
- **Wrong Parent Assignment**: Sections attached to titles instead of articles  
- **Duplicate Hierarchies**: Same content scraped multiple times with version numbers
- **Broken Chains**: Missing intermediate levels (title → section, skipping chapter/article)

### **Content Issues**
- **Empty node_text**: Sections created but content extraction fails
- **HTML Artifacts**: Raw HTML tags in cleaned text
- **Truncated Content**: Only partial section content captured
- **Wrong Text Association**: Content from one section assigned to another

### **Parsing Logic Issues**
- **CSS Selector Mismatches**: Code looks for elements that don't exist on website
- **HTML Structure Changes**: Website updates break existing scrapers
- **Edge Case Handling**: Special sections (repealed, reserved) not handled properly

## **Enhanced Validation Workflow (2025)**

**🚨 CRITICAL: All validation must use the enhanced timeout system. Never run scrapers without timeout conditions during debugging.**

### **The Progressive Timeout-Based Approach**

**🆕 REVOLUTIONARY IMPROVEMENT**: Built-in cross-platform timeout system eliminates the need for external subprocess management.

```bash
# ✅ ALWAYS use these patterns for validation
python scrapeJURISDICTION_standardized.py --mode clean --validation --debug
python scrapeJURISDICTION_standardized.py --mode clean --timeout 2 --max-titles 3 --debug
python scrapeJURISDICTION_standardized.py --mode skip --skip-title 5 --timeout 1 --debug

# ❌ NEVER do this during debugging (will run for hours)
python scrapeJURISDICTION_standardized.py --mode clean
```

**Key Improvements:**
- ✅ **Cross-platform** - Works on Windows/Mac/Linux (no signal.SIGALRM dependency)
- ✅ **Multiple stopping conditions** - Time, title count, node count, validation mode
- ✅ **Partial results preserved** - Database contains sample data for immediate validation
- ✅ **Graceful shutdown** - Proper cleanup and comprehensive statistics
- ✅ **Built-in** - No external subprocess management needed

### For New Scrapers (Enhanced Process)
1. **Quick Timeout Run**: Use `--validation` mode for immediate feedback (30 seconds - 2 minutes)
2. **Immediate Health Check**: Run database queries on sample data
3. **Iterative Debugging**: Use longer timeouts and specific title ranges for targeted fixes
4. **HTML Investigation**: If issues found, inspect actual website structure
5. **Progressive Validation**: Gradually increase limits until full validation passes
6. **Full Run**: Only after timeout validation succeeds

### For Refactored Scrapers
1. **Regression Check**: Compare node counts before/after refactoring
2. **Spot Check**: Validate same sample paths work correctly
3. **New Features**: If new extraction features added, verify they work
4. **Performance Check**: Ensure refactoring didn't break batch processing

### For Production Monitoring
1. **Periodic Health Checks**: Run automated SQL queries monthly
2. **Spot Validation**: Manually check 1-2 jurisdictions quarterly  
3. **Error Monitoring**: Watch for new failure patterns in logs
4. **Website Change Detection**: Monitor for HTML structure changes

## Tools & Resources

### **Essential Tools**
- **Postico 2**: PostgreSQL GUI for database visualization and querying
- **Browser Dev Tools**: For inspecting HTML structure and testing CSS selectors
- **BeautifulSoup**: For programmatic HTML analysis during debugging
- **Pydantic**: Strict schema validation prevents many data integrity issues

### **Validation Helpers** 
```python
# Quick database health check
def check_scraper_health(table_name: str) -> Dict[str, Any]:
    """Run standard validation queries and return summary"""
    
# HTML structure investigator  
def investigate_html_structure(url: str, target_elements: List[str]) -> Dict[str, Any]:
    """Fetch page and analyze structure for given CSS selectors"""
    
# Spot check helper
def validate_hierarchy_path(table_name: str, node_path: str) -> Dict[str, Any]:
    """Deep validate a specific title/chapter/article/section path"""
```

## Documentation Requirements

For each jurisdiction, maintain:

### **HTML Patterns Documentation**
```yaml
# Example: arizona_html_patterns.yaml
jurisdiction: arizona
base_url: "https://www.azleg.gov"
toc_url: "https://www.azleg.gov/arstitle/"

structure_patterns:
  title:
    selector: ".topTitle"
    example: "TITLE 1 GENERAL PROVISIONS"
  
  chapter: 
    selector: ".accordion h5 a"
    example: "Chapter 1 Construction of Statutes"
    
  article:
    container: ".article"
    number_element: "first child text"
    name_element: "second child text"
    
  section:
    container: "ul"  # NOT class="section"!
    number_element: "li.colleft a"
    title_element: "li.colright"
    expected_per_article: 3-20
```

### **Known Issues & Quirks**
```markdown
# arizona_quirks.md

## Parsing Challenges
- Articles use sibling elements, not nested containers
- Sections are ul/li pairs, not individual elements with class="section"
- Some chapters have no articles (direct title → chapter → section)

## Content Issues  
- Legislative history in [Added by Laws...] format
- Some sections marked as "REPEALED" or "RESERVED"
- Cross-references use "A.R.S. § X-Y" format
```

## Success Criteria

A scraper is considered "correctly validated" when:

- [ ] **Runs Without Errors**: No infrastructure failures
- [ ] **Reasonable Node Counts**: Expected ratios of structure vs content nodes
- [ ] **Complete Hierarchies**: Sample paths show proper parent-child relationships  
- [ ] **Content Population**: Sections have meaningful node_text and metadata
- [ ] **Spot Check Passes**: Manual validation of 1-2 titles shows accurate extraction
- [ ] **HTML Understanding**: Parsing logic matches actual website structure
- [ ] **Documentation Current**: Patterns and quirks documented for future reference

## Real-World Validation Example: Arizona Content Extraction Issue

**Case Study from Arizona Refactoring (January 2025)**

### **Problem Discovered**
- ✅ Scraper runs without errors
- ✅ Perfect hierarchical structure created (3,766 sections)  
- ✅ All sections have citations (100%)
- ❌ **0% of sections have node_text content**

### **Validation Process Applied**

**Step 1: Database Health Check**
```sql
SELECT level_classifier, COUNT(*) FROM us_az_statutes GROUP BY level_classifier;
-- Result: 86.5% sections, good distribution

SELECT COUNT(node_text) FROM us_az_statutes WHERE level_classifier = 'SECTION';  
-- Result: 0 (CRITICAL ISSUE DETECTED)
```

**Step 2: Hierarchy Spot Check**  
- ✅ Verified `us/az/statutes/title=1/chapter=1/article=1/section=1-101` exists
- ✅ All expected sections present (1-101 through 1-106)
- ✅ Perfect parent-child relationships

**Step 3: HTML Structure Investigation**
- ✅ Main listing page structure correct: `<ul>` with `<li class="colleft">` and `<li class="colright">`
- ✅ Section links found: `/viewdocument/?docName=https://www.azleg.gov/ars/1/00101.htm`

**Step 4: CRITICAL - Visit Individual Section URLs**
```bash
# URL: https://www.azleg.gov/viewdocument/?docName=https://www.azleg.gov/ars/1/00101.htm
# HTML Analysis: .content-sidebar-wrap .first contains <p> elements with statute content!
# Content Found: "1-101. Designation and citation" + full statute text (398 chars)
```

### **Root Cause Identified**
**🎯 MAJOR DISCOVERY**: Content IS available on individual section pages! The issue was **not** website changes.

**Step 5: Code Analysis Reveals the Real Problem**

**Original Scraper (`scrapeAZ.py` lines 183-192):**
```python
# ✅ WORKING - Fetches individual section content
section_soup = get_url_as_soup(node_link)
text_container = section_soup.find(class_="content-sidebar-wrap").find(class_="first")
for p in text_container.find_all("p"):
    txt = p.get_text().strip()
    if txt != "":
        node_text.add_paragraph(text=txt)
```

**Phase 3 Standardized Scraper (`scrapeAZ_standardized.py` lines 316-322):**
```python
# ❌ BROKEN - Explicitly disabled content fetching!
# NOTE: Arizona statute links point to separate documents, not inline content
# So we don't expect to find section content on this page
node_text = None
addendum = None

# Future enhancement: Could fetch individual statute content from section_href
```

### **Actual Root Cause: Refactoring Bug**
During Phase 3 refactoring, **working content extraction logic was accidentally removed** and marked as a "future enhancement". This is a **"runtime error" caused by refactoring**, not a website change.

### **Validation Success & Critical Lesson**
Our systematic validation process **correctly identified the issue type**:
1. **Health check** - 0% content population flagged immediately
2. **Spot check** - Perfect hierarchy confirmed infrastructure working  
3. **HTML investigation** - **CRITICAL STEP** revealed content is available
4. **Code analysis** - **FINAL STEP** found the refactoring broke working logic

**Key Insight**: Always **visit actual URLs** during validation - don't assume website issues without verification!

### **Resolution Steps**
1. **Restore individual section content fetching** from original scraper
2. **Re-run validation** to confirm content extraction works
3. **Update refactoring documentation** to prevent similar issues

### **Lessons for Framework**
- **Multiple validation layers essential** - structure can be perfect while content fails
- **Always verify content population** - not just node creation
- **Always visit actual URLs** - don't assume website problems without checking
- **Code comparison critical** - compare refactored vs original working logic
- **Systematic investigation beats random debugging** 
- **Document real examples** for future validation reference

### **Framework Enhancement: URL Investigation Protocol**
Added to validation workflow:
```python
# Always visit sample URLs during validation
sample_urls = [first_section_link, random_middle_section, last_section]
for url in sample_urls:
    response = requests.get(url)
    # Analyze actual HTML structure vs expected code patterns
    # Document findings for targeted debugging
```

## Brainstorming: Automatic Validation Patterns

**🚧 UNDER DEVELOPMENT** - Collaborative brainstorming for automated scraper validation

### **Tree Structure Validation**
Legislative data forms hierarchical trees. Common parsing bugs create detectable tree anomalies:

**1. Hierarchy Level Violations**
```python
# Detect impossible parent-child relationships
# Example: section → title (skipping chapter/article)
def detect_level_violations(table_name: str) -> List[ValidationIssue]:
    # TITLE → CHAPTER → ARTICLE → SECTION (expected)
    # Flag: SECTION → TITLE, ARTICLE → TITLE, etc.
```

**2. Insertion Order Anomalies** 
```python
# Tree traversal should follow depth-first insertion pattern
# Flag: Parent inserted AFTER child (impossible in correct parsing)
def detect_insertion_order_issues(table_name: str) -> List[ValidationIssue]:
    # Check: All children inserted after their parents
    # Check: Siblings inserted in reasonable order
```

**3. Orphaned Subtrees**
```python
# Detect nodes without valid parent chains to corpus
def detect_orphaned_nodes(table_name: str) -> List[ValidationIssue]:
    # Flag: parent field points to non-existent nodes
    # Flag: nodes with level_classifier != 'corpus' but no parent
```

**4. Content Population Patterns**
```python
# Structure vs content ratios indicate parsing health
def detect_content_anomalies(table_name: str) -> List[ValidationIssue]:
    # Flag: 0% sections with node_text (like Arizona case)
    # Flag: Impossible ratios (more titles than sections)
    # Flag: All content same length (copy-paste bugs)
```

**5. Duplicate Detection**
```python
# Version numbering suggests parsing ran multiple times
def detect_duplicate_processing(table_name: str) -> List[ValidationIssue]:
    # Flag: Multiple nodes with same base ID + version suffixes
    # Flag: Identical node_text across different nodes
```

### **Jurisdiction-Specific Validation**
```python
# Each jurisdiction has expected patterns
def validate_jurisdiction_patterns(table_name: str, jurisdiction: str) -> List[ValidationIssue]:
    # Arizona: Should have titles 1-47, certain chapters per title
    # Federal: CFR should have titles 1-50, parts per title
    # Flag: Missing expected major divisions
    # Flag: Unexpected extra levels (5-deep hierarchy when jurisdiction uses 3)
```

### **Performance & Resource Validation**
```python
# Detect scraper efficiency issues
def detect_performance_issues(scraper_logs: str) -> List[ValidationIssue]:
    # Flag: Taking >X seconds per section (network issues)
    # Flag: Memory usage growing (memory leaks)
    # Flag: Error rate >Y% (parsing logic broken)
```

### **Cross-Reference Validation**
```python
# Legal documents have predictable citation patterns
def validate_citation_patterns(table_name: str, jurisdiction: str) -> List[ValidationIssue]:
    # Arizona: Citations should match "A.R.S. § X-Y" pattern
    # Flag: Malformed citations
    # Flag: Citation numbers don't match node hierarchy
```

### **Implementation Strategy**
1. **SQL Functions**: Common tree queries, pattern detection
2. **Python Validators**: Complex logic, cross-table analysis  
3. **Pydantic Validators**: Field-level validation, data integrity
4. **Scraper Integration**: Real-time validation during scraping
5. **Post-Processing**: Batch validation after scraper completion

### **Questions for Implementation**
- Which validations should be **real-time** (during scraping) vs **post-processing**?
- Should validation **halt scraping** on critical errors or just warn?
- How to handle **jurisdiction-specific** validation rules?
- What **performance impact** is acceptable for validation?
- Should we create a **validation dashboard** for multiple scrapers?

---

## Meta-Notes

**This is a living document** that should be updated as we discover new validation techniques, failure patterns, and debugging approaches. The Arizona refactoring process serves as our test case for developing and refining these validation methodologies.

**Key Insight**: Scraper validation is fundamentally about **human judgment applied systematically**. While we can automate health checks and provide tools, the core validation requires understanding legal document structure and manually verifying that our knowledge graph accurately represents the legislative hierarchy.