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
    
    def __init__(self, debug_mode: bool = False):
        """Initialize Arizona scraper with Phase 3 standardized infrastructure."""
        config = ConfigManager.create_arizona_config(debug_mode=debug_mode)
        super().__init__(config)
        
        self.scraper_dir = self.get_scraper_directory()
        
        # NEW: Initialize standardized web fetcher for Arizona
        self.web_fetcher = WebFetcherFactory.create_arizona_fetcher()
        
        # Track batch insertion for performance
        self.batch_nodes = []
        self.batch_size = 50
        
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
                    
                self.logger.info(f"Scraping title {i+1}/{len(all_titles)}: {title_url}")
                self._scrape_per_title(title_url)
                
            # Flush any remaining batch nodes
            self._flush_batch()
            
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
        PRESERVED: Arizona section finding logic
        """
        # PRESERVED: Arizona section finding logic
        section_elements = article.find_all(class_="section")
        
        for section_elem in section_elements:
            try:
                section_link = section_elem.find("a")
                if not section_link:
                    continue
                    
                # NEW: Enhanced text processing for section data
                section_text_raw = section_link.get_text()
                section_text = TextProcessor.clean_text(section_text_raw)
                section_href = section_link.get("href", "")
                
                # Extract section number (Arizona-specific logic preserved)
                if " " in section_text:
                    section_number = section_text.split(" ")[1]
                else:
                    continue
                
                # NEW: Extract and process section content if available
                section_content_container = section_elem.find_next("div", class_="section-content")
                node_text = None
                addendum = None
                
                if section_content_container:
                    # NEW: Use TextProcessor for content extraction
                    node_text = TextProcessor.extract_node_text(
                        section_content_container,
                        tag_filter=["p", "div", "li"],
                        custom_paragraph_patterns=[r"^\([a-z]\)", r"^\d+\."]
                    )
                    
                    # NEW: Extract addendum using standardized patterns
                    content_text = TextProcessor.clean_text(section_content_container)
                    addendum = TextProcessor.extract_addendum(
                        content_text,
                        patterns=self.az_text_config["addendum_patterns"],
                        addendum_type=AddendumType.HISTORICAL
                    )
                
                # NEW: Generate Arizona-style citation
                citation = f"A.R.S. § {top_level_title}-{section_number}"
                
                # NEW: Use NodeFactory for content node creation
                section_node = self.create_content_node(
                    parent_id=article_node.node_id,
                    number=section_number,
                    name=section_text,
                    link=f"{self.config.base_url}{section_href}" if section_href.startswith("/") else section_href,
                    citation=citation,
                    top_level_title=top_level_title,
                    node_text=node_text,
                    addendum=addendum
                )
                
                # NEW: Content analysis and classification
                if node_text:
                    content_full = " ".join([p.text for p in node_text.to_list_paragraph()])
                    
                    # Analyze content type
                    content_type = TextProcessor._classify_paragraph(content_full)
                    if content_type:
                        if not section_node.core_metadata:
                            section_node.core_metadata = {}
                        section_node.core_metadata["content_type"] = content_type
                    
                    # Extract citations within the content
                    citations = TextProcessor.extract_citation(
                        content_full,
                        {"arizona": self.az_text_config["citation_patterns"]}
                    )
                    if citations:
                        if not section_node.core_metadata:
                            section_node.core_metadata = {}
                        section_node.core_metadata["internal_citations"] = citations
                
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
            self.logger.info(f"Batch inserting {len(self.batch_nodes)} nodes")
            
            successful_nodes = self.batch_insert_nodes(
                self.batch_nodes, 
                ignore_duplicates=True
            )
            
            self.logger.info(f"Successfully inserted {len(successful_nodes)} nodes")
            
        except Exception as e:
            self.logger.error(f"Batch insertion failed: {e}")
            
            # Fallback to individual insertions
            self.logger.info("Falling back to individual insertions")
            for node in self.batch_nodes:
                try:
                    self.insert_node_safely(node)
                except Exception as individual_error:
                    self.logger.warning(f"Failed to insert {node.node_id}: {individual_error}")
        
        finally:
            self.batch_nodes.clear()
    
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
                    
        except Exception as e:
            self.logger.warning(f"Could not retrieve statistics: {e}")


# Standardized main function
def main():
    """Main entry point with Phase 3 enhancements."""
    try:
        # Create and run scraper
        scraper = ArizonaStatutesScraperPhase3(debug_mode=True)
        scraper.scrape()
        
    except Exception as e:
        print(f"Scraping failed: {e}")
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