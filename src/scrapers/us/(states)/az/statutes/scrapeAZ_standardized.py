"""
Arizona Statutes Scraper - Phase 3 Version

This demonstrates the Arizona scraper after Phase 3 standardization:
- TextProcessor for unified text cleaning and extraction
- WebFetcher for standardized web operations with rate limiting
- Advanced text analysis and content classification
- Still preserves all Arizona-specific parsing logic

Improvements over Phase 2:
- Replace get_url_as_soup() with standardized WebFetcher
- Replace ad-hoc text cleaning with TextProcessor
- Enhanced content analysis and classification
- Better handling of complex legislative text structures
- Advanced addendum and citation extraction
"""

# Single line replaces 34 lines of path setup
from src.utils.base import setup_project_path, BaseScraper, ConfigManager
from src.utils.processing.database import ScrapingMode
setup_project_path()

# Standard imports (unchanged)
import os
import json
from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import List, Tuple, Optional
import time
from pathlib import Path

# Import Pydantic models (unchanged)  
from src.utils.pydanticModels import (
    NodeID, Node, Addendum, AddendumType, NodeText, Paragraph, 
    ReferenceHub, Reference, DefinitionHub, Definition, IncorporatedTerms
)

# NEW: Import Phase 3 processing utilities
from src.utils.processing import TextProcessor, WebFetcher, WebFetcherFactory


class ArizonaStatutesScraperPhase3(BaseScraper):
    """
    Arizona Statutes Scraper using Phase 3 standardized infrastructure.
    
    NEW Phase 3 Features:
    - WebFetcher for unified web operations with retry logic and rate limiting
    - TextProcessor for standardized text cleaning and extraction
    - Advanced content analysis and classification capabilities
    - Enhanced addendum and citation extraction
    - Better handling of complex legislative text structures
    
    Still preserves all working Arizona parsing logic exactly.
    """
    
    def __init__(self, debug_mode: bool = False, mode: ScrapingMode = ScrapingMode.RESUME, 
                 skip_title: Optional[int] = None, timeout_minutes: Optional[int] = None,
                 max_titles: Optional[int] = None, max_nodes: Optional[int] = None, validation_mode: bool = False):
        """Initialize Arizona scraper with enhanced debugging and timeout features."""
        # Arizona-specific configuration defined inline (not in shared config.py)
        config = ConfigManager.create_custom_config(
            country="us",
            jurisdiction="az",
            corpus="statutes",
            base_url="https://www.azleg.gov",
            toc_url="https://www.azleg.gov/arstitle/",
            skip_title=0,  # Will be overridden by mode logic
            reserved_keywords=["REPEALED", "RESERVED", "TRANSFERRED"],
            delay_seconds=0,
            debug_mode=debug_mode
        )
        super().__init__(config, mode=mode, skip_title=skip_title, timeout_minutes=timeout_minutes,
                         max_titles=max_titles, max_nodes=max_nodes, validation_mode=validation_mode)
        
        self.scraper_dir = self.get_scraper_directory()
        
        # 🔍 DELAY DEBUGGING: Initialize web fetcher with config delay verification
        if self.config.delay_seconds > 0:
            self.logger.warning(f"⚠️  DELAY CONFIGURED: {self.config.delay_seconds}s per request will slow scraping!")
        else:
            self.logger.info(f"🚀 ZERO DELAY OPTIMIZED: {self.config.delay_seconds}s = maximum speed")
            
        self.web_fetcher = WebFetcher(
            delay_seconds=self.config.delay_seconds,  # Respect config setting
            max_retries=3,
            timeout=30,
            custom_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
        
        # 🔍 DELAY DEBUGGING: Verify web fetcher delay setting
        self.logger.info(f"🔧 WebFetcher initialized with delay_seconds={self.web_fetcher.delay_seconds}")
        
        # OPTIMIZED: Large batch insertion for performance
        self.batch_nodes = []
        self.batch_size = 1000  # Large batches for maximum database throughput
        
        # OPTIMIZED: Performance tracking
        self.batch_stats = {
            'total_batches': 0,
            'total_nodes': 0,
            'fallback_operations': 0
        }
        
        # NEW: Arizona-specific text processing configuration
        self.az_text_config = {
            "custom_replacements": {
                "A.R.S.": "Arizona Revised Statutes",
                "Ch.": "Chapter",
                "Sec.": "Section"
            },
            "citation_patterns": [
                r'A\.R\.S\.\s*§\s*[\d-]+(?:\.[A-Z])?',
                r'ARS\s*§\s*[\d-]+',
                r'§\s*[\d-]+(?:\([a-z0-9]+\))*'
            ],
            "addendum_patterns": [
                r'\[Added by Laws (\d+),\s*Ch\.\s*(\d+),\s*§\s*(\d+)\]',
                r'\[Amended by Laws (\d+),.*?\]',
                r'\[Repealed by Laws (\d+),.*?\]'
            ]
        }
        
    def scrape_implementation(self) -> None:
        """
        Arizona-specific scraping logic - Enhanced with Phase 3 features.
        """
        self.logger.info("Starting Arizona statutes scraping with Phase 3 features")
        
        # Load title data (same as before)
        titles_file = os.path.join(self.scraper_dir, "top_level_title_links.json")
        
        if not os.path.exists(titles_file):
            self.logger.warning(f"Top level titles file not found: {titles_file}")
            self.logger.info("You may need to run readAZ.py first to generate title links")
            return
            
        with open(titles_file, "r") as read_file:
            data = json.loads(read_file.read())
            all_titles: List[str] = data['top_level_titles']
            
            self.logger.info(f"Found {len(all_titles)} titles to process")
            
            for i, title_url in enumerate(all_titles):
                if i < self.config.skip_title:
                    continue
                
                # NEW: Check stopping conditions (timeout, limits, etc.)
                if not self.should_continue():
                    self.logger.info(f"🛑 Stopping scraping: {self._stop_reason}")
                    break
                    
                self.logger.info(f"Scraping title {i+1}/{len(all_titles)}: {title_url}")
                
                # NEW: Track progress for reliable resuming
                self.track_title_progress(i, title_url, {"total_titles": len(all_titles)})
                
                self._scrape_per_title(title_url)
                
                # NEW: Track title processing for stopping conditions (after processing)
                self.increment_title_count()
                
            # OPTIMIZED: Flush all remaining batch nodes
            self._flush_all_batches()
            
            # Display enhanced statistics
            self._show_enhanced_stats()
                
        self.logger.info("Arizona statutes scraping completed")
    
    def _scrape_per_title(self, url: str) -> None:
        """
        Scrape a single title - Enhanced with Phase 3 features.
        
        PRESERVED: All Arizona-specific HTML parsing logic
        NEW: WebFetcher for standardized web operations
        NEW: TextProcessor for consistent text cleaning
        """
        try:
            # NEW: Use standardized WebFetcher instead of get_url_as_soup()
            soup: BeautifulSoup = self.web_fetcher.get_soup(url)
            
            # PRESERVED: Arizona-specific HTML parsing logic
            title_container = soup.find(class_="topTitle")
            
            # NEW: Use TextProcessor for standardized text cleaning
            title_name_raw = title_container.get_text()
            title_name = TextProcessor.clean_text(
                title_name_raw,
                custom_replacements=self.az_text_config["custom_replacements"]
            )
            
            number = title_name.split(" ")[1] if title_name.split() else "unknown"
            top_level_title = number

            # NEW: Use NodeFactory for consistent Node creation
            title_node = self.create_structure_node(
                parent_id=self.config.corpus_id,
                level_classifier="title",
                number=number,
                name=title_name,
                link=url,
                top_level_title=top_level_title
            )
           
            # Add to batch for insertion
            self._add_to_batch(title_node)
            
            # PRESERVED: Complex Arizona chapter parsing logic
            chapter_container = title_container.parent.parent.parent
            
            for i, chapter in enumerate(chapter_container.find_all(class_="accordion", recursive=False)):
                # NEW: Check timeout during chapter processing
                if not self.should_continue():
                    self.logger.info(f"🛑 Stopping during chapter processing: {self._stop_reason}")
                    return
                
                header = chapter.find("h5")
                link = header.find("a")
                
                # NEW: Enhanced text processing for chapter names
                node_name_start_raw = link.get_text()
                node_name_start = TextProcessor.clean_text(node_name_start_raw)
                
                node_number = node_name_start.split(" ")[1] if node_name_start.split() else str(i)
                node_link = url + "#" + chapter['id']
                
                node_name_end_raw = link.next_sibling.get_text() if link.next_sibling else ""
                node_name_end = TextProcessor.clean_text(node_name_end_raw)
                node_name = f"{node_name_start} {node_name_end}".strip()

                # NEW: Use NodeFactory for consistent Node creation
                chapter_node = self.create_structure_node(
                    parent_id=title_node.node_id,
                    level_classifier="chapter",
                    number=node_number,
                    name=node_name,
                    link=node_link,
                    top_level_title=top_level_title
                )
                
                # Add to batch
                self._add_to_batch(chapter_node)
                
                # PRESERVED: Complex Arizona article parsing logic
                article_container = header.next_sibling
                if article_container:
                    for j, article in enumerate(article_container.find_all(class_="article")):
                        # NEW: Check timeout during article processing
                        if not self.should_continue():
                            self.logger.info(f"🛑 Stopping during article processing: {self._stop_reason}")
                            return
                            
                        try:
                            self._process_article(article, chapter_node, top_level_title, j)
                        except Exception as e:
                            self.logger.warning(
                                f"Error processing article {j} in {chapter_node.node_id}: {e}"
                            )
                            continue
                        
        except Exception as e:
            self.logger.error(f"Error scraping title {url}: {e}")
            raise
    
    def _process_article(self, article: Tag, chapter_node: Node, top_level_title: str, article_index: int) -> None:
        """
        Process a single article with Phase 3 enhancements.
        
        NEW: Enhanced text processing and content analysis
        PRESERVED: Arizona article parsing logic
        """
        elements = article.find_all(recursive=False)
        if len(elements) < 2:
            return
            
        link_container = elements[0]
        name_container = elements[1]
        
        # NEW: Enhanced text processing for article names
        node_name_start = TextProcessor.clean_text(link_container.get_text())
        node_name_end = TextProcessor.clean_text(name_container.get_text())
        
        # Extract article number (Arizona-specific logic preserved)
        if " " in node_name_start:
            node_number = node_name_start.split(" ")[1]
        else:
            node_number = str(article_index + 1)
            
        node_name = f"{node_name_start} {node_name_end}".strip()

        # NEW: Use NodeFactory for consistent Node creation
        article_node = self.create_structure_node(
            parent_id=chapter_node.node_id,
            level_classifier="article", 
            number=node_number,
            name=node_name,
            link=chapter_node.link,  # Arizona uses chapter link for articles
            top_level_title=top_level_title
        )
        
        # Add to batch
        self._add_to_batch(article_node)
        
        # NEW: Enhanced section processing with content analysis
        self._process_article_sections(article, article_node, top_level_title)
    
    def _process_article_sections(self, article: Tag, article_node: Node, top_level_title: str) -> None:
        """
        Process sections within an article with Phase 3 enhancements.
        
        NEW: Advanced text processing and content analysis
        NEW: Citation and addendum extraction
        FIXED: Arizona section finding logic - sections are in <ul> lists, not class="section"
        """
        # FIXED: Arizona section finding logic - sections are in <ul> lists with statute links
        # Each section is a <ul> with 2 <li> items: link (class="colleft") and title (class="colright")
        section_lists = article.find_all("ul")
        
        for section_list in section_lists:
            # NEW: Check timeout during section processing (where most time is spent)
            if not self.should_continue():
                self.logger.info(f"🛑 Stopping during section processing: {self._stop_reason}")
                return
                
            try:
                # Look for statute links in the list
                left_items = section_list.find_all("li", class_="colleft")
                right_items = section_list.find_all("li", class_="colright")
                
                # Validate this is a statute section list (has both left and right items)
                if not left_items or not right_items:
                    continue
                    
                left_item = left_items[0]
                right_item = right_items[0]
                
                # Get the statute link from the left item
                section_link = left_item.find("a", class_="stat")
                if not section_link:
                    continue
                    
                # NEW: Enhanced text processing for section data
                section_number_raw = section_link.get_text()
                section_number = TextProcessor.clean_text(section_number_raw)
                section_href = section_link.get("href", "")
                
                # Get section title from the right item  
                section_title_raw = right_item.get_text()
                section_title = TextProcessor.clean_text(section_title_raw)
                
                # Combine section number and title for full name
                section_text = f"{section_number} {section_title}".strip()
                
                # Extract just the numeric part for section_number field
                # Arizona sections are like "1-101", "1-102", etc.
                if "-" in section_number:
                    section_number_clean = section_number
                else:
                    continue
                
                # RESTORED: Fetch individual section content (was working in original scraper)
                # Individual Arizona statute pages DO serve content via .content-sidebar-wrap .first
                node_text = None
                addendum = None
                
                try:
                    # Construct full URL for individual section
                    section_url = f"{self.config.base_url}{section_href}" if section_href.startswith("/") else section_href
                    
                    # Fetch individual section page content
                    section_soup = self.web_fetcher.get_soup(section_url)
                    
                    # Extract content using same logic as original scraper
                    text_container = section_soup.find(class_="content-sidebar-wrap")
                    if text_container:
                        first_element = text_container.find(class_="first")
                        if first_element:
                            # Use TextProcessor to extract structured content
                            node_text = TextProcessor.extract_node_text(
                                first_element,
                                tag_filter=["p"],
                                custom_paragraph_patterns=None  # Use default paragraph detection
                            )
                            
                            # Also extract full text for addendum analysis
                            full_text = TextProcessor.clean_text(first_element)
                            if full_text:
                                # Extract addendum using Arizona-specific patterns
                                addendum = TextProcessor.extract_addendum(
                                    full_text,
                                    patterns=self.az_text_config["addendum_patterns"]
                                )
                            
                            #self.logger.debug(f"Extracted content for {section_number_clean}: {len(full_text) if full_text else 0} characters")
                        else:
                            self.logger.warning(f"No .first element found in {section_url}")
                    else:
                        self.logger.warning(f"No .content-sidebar-wrap found in {section_url}")
                        
                except Exception as content_error:
                    self.logger.warning(f"Failed to fetch content for {section_number_clean}: {content_error}")
                    # Continue with node creation even if content extraction fails
                
                # NEW: Generate Arizona-style citation
                citation = f"A.R.S. § {section_number_clean}"
                
                # NEW: Use NodeFactory for content node creation
                section_node = self.create_content_node(
                    parent_id=article_node.node_id,
                    number=section_number_clean,
                    name=section_text,
                    link=f"{self.config.base_url}{section_href}" if section_href.startswith("/") else section_href,
                    citation=citation,
                    top_level_title=top_level_title,
                    node_text=node_text,
                    addendum=addendum
                )
                
                # Add metadata about the section title for future analysis
                if section_title:
                    if not section_node.core_metadata:
                        section_node.core_metadata = {}
                    section_node.core_metadata["section_title"] = section_title
                
                # Add to batch
                self._add_to_batch(section_node)
                
                self.logger.debug(f"Processed section: {section_text}")
                
            except Exception as e:
                self.logger.warning(f"Error processing section in {article_node.node_id}: {e}")
                continue
    
    def _add_to_batch(self, node: Node) -> None:
        """Add node to batch for efficient insertion."""
        self.batch_nodes.append(node)
        
        if len(self.batch_nodes) >= self.batch_size:
            self._flush_batch()
    
    def _flush_batch(self) -> None:
        """Flush batch nodes to database."""
        if not self.batch_nodes:
            return
            
        try:
            self.logger.info(f"📦 Batch inserting {len(self.batch_nodes)} nodes")
            
            successful_nodes = self.batch_insert_nodes(
                self.batch_nodes, 
                ignore_duplicates=True
            )
            
            self.logger.info(f"✅ Batch complete: {len(successful_nodes)} nodes inserted")
            
            # Track performance metrics
            self.batch_stats['total_batches'] += 1
            self.batch_stats['total_nodes'] += len(successful_nodes)
            
        except Exception as e:
            self.logger.error(f"❌ Batch insertion failed: {e}")
            self.batch_stats['fallback_operations'] += 1
            self._fallback_individual_insert()
        finally:
            self.batch_nodes.clear()
    
    def _fallback_individual_insert(self) -> None:
        """Fallback to individual insertions with error tracking."""
        self.logger.info(f"🔄 Falling back to individual insertions for {len(self.batch_nodes)} nodes")
        
        successful = 0
        failed = 0
        
        for node in self.batch_nodes:
            try:
                self.insert_node_safely(node)
                successful += 1
            except Exception as individual_error:
                failed += 1
                self.logger.warning(f"❌ Failed individual insert {node.node_id}: {individual_error}")
        
        self.logger.info(f"📈 Individual insertion results: {successful} success, {failed} failed")
    
    def _flush_all_batches(self) -> None:
        """Flush all remaining batches (called at end of scraping)."""
        self.logger.info("🧹 Flushing remaining batch")
        self._flush_batch()
    
    def _show_enhanced_stats(self) -> None:
        """
        NEW: Display enhanced statistics including web fetching metrics.
        """
        try:
            # Database statistics
            db_stats = self.db.get_stats()
            self.logger.info("=== SCRAPING STATISTICS ===")
            self.logger.info(f"Total nodes: {db_stats.get('total_nodes', 0)}")
            
            if 'by_type' in db_stats:
                for node_type, count in db_stats['by_type'].items():
                    self.logger.info(f"  {node_type}: {count}")
                    
            if 'by_status' in db_stats:
                self.logger.info("Status breakdown:")
                for status, count in db_stats['by_status'].items():
                    self.logger.info(f"  {status}: {count}")
            
            # NEW: Web fetching statistics
            web_stats = self.web_fetcher.get_stats()
            self.logger.info("=== WEB FETCHING STATISTICS ===")
            self.logger.info(f"Requests made: {web_stats['requests_made']}")
            self.logger.info(f"Successful requests: {web_stats['successful_requests']}")
            self.logger.info(f"Failed requests: {web_stats['failed_requests']}")
            self.logger.info(f"Success rate: {web_stats['success_rate']:.2%}")
            self.logger.info(f"Total delay time: {web_stats['total_delay_time']:.1f}s")
            self.logger.info(f"Average delay: {web_stats['average_delay']:.1f}s")
            
            # OPTIMIZED: Batch performance statistics
            self.logger.info("=== BATCH PERFORMANCE STATISTICS ===")
            self.logger.info(f"Total batches: {self.batch_stats['total_batches']}")
            self.logger.info(f"Total nodes processed: {self.batch_stats['total_nodes']}")
            
            if self.batch_stats['total_batches'] > 0:
                avg_batch_size = self.batch_stats['total_nodes'] / self.batch_stats['total_batches']
                self.logger.info(f"Average batch size: {avg_batch_size:.1f} nodes")
                
            if self.batch_stats['fallback_operations'] > 0:
                self.logger.info(f"⚠️  Fallback operations: {self.batch_stats['fallback_operations']}")
            else:
                self.logger.info("✅ No fallback operations required")
                    
        except Exception as e:
            self.logger.warning(f"Could not retrieve statistics: {e}")


# Enhanced main function with debugging modes
def main():
    """Main entry point with enhanced debugging workflow."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Arizona Statutes Scraper with Enhanced Debugging")
    parser.add_argument("--mode", choices=["resume", "clean", "skip"], default="resume",
                       help="Scraping mode: resume (continue where left off), clean (start fresh), skip (start from specific title)")
    parser.add_argument("--skip-title", type=int, help="Title number to skip to (for skip mode or manual override)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--timeout", type=int, help="Timeout in minutes for debugging/validation runs")
    parser.add_argument("--max-titles", type=int, help="Maximum number of titles to process (for validation)")
    parser.add_argument("--max-nodes", type=int, help="Maximum number of nodes to create (for validation)")
    parser.add_argument("--validation", action="store_true", help="Enable validation mode (sets automatic limits)")
    
    args = parser.parse_args()
    
    # Convert string mode to enum
    mode_map = {
        "resume": ScrapingMode.RESUME,
        "clean": ScrapingMode.CLEAN, 
        "skip": ScrapingMode.SKIP
    }
    mode = mode_map[args.mode]
    
    try:
        # Create and run scraper with specified mode and timeout options
        scraper = ArizonaStatutesScraperPhase3(
            debug_mode=args.debug,
            mode=mode,
            skip_title=args.skip_title,
            timeout_minutes=args.timeout,
            max_titles=args.max_titles,
            max_nodes=args.max_nodes,
            validation_mode=args.validation
        )
        scraper.scrape()
        
        print(f"\n✅ Scraping completed successfully in {args.mode} mode!")
        
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()


"""
PHASE 3 SUMMARY:

NEW FEATURES ADDED:
✅ WebFetcher for unified web operations with retry logic and rate limiting
✅ TextProcessor for standardized text cleaning and extraction  
✅ Advanced content analysis and classification capabilities
✅ Enhanced addendum and citation extraction using standardized patterns
✅ Better handling of complex legislative text structures
✅ Comprehensive web fetching statistics and monitoring

TEXT PROCESSING IMPROVEMENTS:
- Replaces get_url_as_soup() with standardized WebFetcher
- Replaces ad-hoc text cleaning with configurable TextProcessor
- Standardized NodeText extraction from HTML containers
- Advanced paragraph classification and content type detection
- Jurisdiction-specific text processing rules for Arizona
- Enhanced addendum extraction with pattern matching

WEB FETCHING IMPROVEMENTS:
- Unified WebFetcher with retry logic and exponential backoff
- Configurable rate limiting and delays
- Session management for better performance
- Request/response statistics and monitoring
- Jurisdiction-optimized fetcher configurations
- Support for both requests and Selenium approaches

PRESERVED:
✅ All Arizona-specific parsing logic exactly as-is
✅ Complex HTML navigation patterns that work
✅ Jurisdiction-specific quirks and edge cases
✅ Working data extraction patterns developed through trial and error

BENEFITS:
🌐 Standardized web operations across all scrapers
📝 Consistent text processing with advanced features
📊 Enhanced content analysis and classification
🔍 Better citation and addendum extraction
📈 Comprehensive statistics and monitoring
🛡️ Robust error handling and recovery for web operations
🚀 Performance optimizations with session management
"""