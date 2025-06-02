"""
Idaho Statutes Scraper - Standardized Framework Implementation

This scraper extracts Idaho state statutes using the standardized Phase 3 framework
while preserving all original parsing logic and jurisdiction-specific patterns.

Original patterns preserved:
- Complex recursive structure (title → chapter/article → section)
- Special handling for Idaho-specific HTML patterns
- SKIP_TITLE=40 (Idaho starts from title 40)
- Reserved/redesignated section handling
- Bracket number extraction for irregular sections
"""

from bs4 import BeautifulSoup
from bs4.element import Tag
from typing import List, Optional
import time
import re

from src.utils.base import setup_project_path, BaseScraper, ConfigManager
from src.utils.processing.database import ScrapingMode
from src.utils.processing.text import TextProcessor
from src.utils.processing.web import WebFetcher
from src.utils.pydanticModels import Node, NodeText, Addendum, AddendumType, ALLOWED_LEVELS

setup_project_path()


class IdahoStatutesScraper(BaseScraper):
    """Idaho-specific statutes scraper using standardized framework."""
    
    def __init__(self, debug_mode: bool = False, mode: ScrapingMode = ScrapingMode.RESUME, 
                 skip_title: Optional[int] = None, timeout_minutes: Optional[int] = None,
                 max_titles: Optional[int] = None, max_nodes: Optional[int] = None,
                 validation_mode: bool = False):
        # Idaho-specific configuration defined inline
        config = ConfigManager.create_custom_config(
            country="us",
            jurisdiction="id",
            corpus="statutes",
            base_url="https://legislature.idaho.gov",
            toc_url="https://legislature.idaho.gov/statutesrules/idstat/",
            skip_title=40,  # Idaho starts from title 40
            reserved_keywords=["REPEALED", "RESERVED", "REDESIGNATED"],
            delay_seconds=1.5,
            debug_mode=debug_mode
        )
        super().__init__(config, mode=mode, skip_title=skip_title, 
                        timeout_minutes=timeout_minutes, max_titles=max_titles,
                        max_nodes=max_nodes, validation_mode=validation_mode)
        
        # Initialize standardized web fetcher
        self.web_fetcher = WebFetcher(
            delay_seconds=1.5,
            max_retries=3,
            timeout=30
        )
        
        # Idaho-specific text processing configuration
        self.id_config = {
            "custom_replacements": {
                "I.C.": "Idaho Code"
            },
            "citation_patterns": [r'I\.C\.\s*\d+\s*§\s*[\d-]+'],
            "addendum_patterns": [r'History:\s*.*']
        }
    
    def scrape_implementation(self) -> None:
        """
        Idaho-specific scraping logic.
        
        PRESERVED: All original parsing logic exactly as-is
        UPDATED: Infrastructure to use standardized framework
        """
        self.logger.info("Starting Idaho statutes scraping")
        
        # Start from table of contents page
        self.scrape_toc_page()
        
        # Show comprehensive statistics
        self._show_comprehensive_stats()
    
    def scrape_toc_page(self) -> None:
        """Extract title links from table of contents page."""
        soup = self.web_fetcher.get_soup(self.config.toc_url)
        
        # The first vc-column-inner-wrapper is for page banner
        statutes_container = soup.find_all("div", class_="vc-column-innner-wrapper")[1]
        
        all_title_containers: List[Tag] = statutes_container.find_all("tr")
        nodes_to_insert = []
        
        for i, title_container in enumerate(all_title_containers):
            # Skip titles based on configuration  
            if i < self.config.skip_title:
                continue
            
            # Add progress tracking for reliable resuming
            self.track_title_progress(i, f"title_{i}", {"total_titles": len(all_title_containers)})
            
            td_list = title_container.find_all("td")
            node_name = td_list[0].get_text().strip()
            level_classifier = "title"
            node_type = "structure"
            number = node_name.split(" ")[1]
            
            node_name += " " + td_list[1].get_text().strip()
            link_container = title_container.find("a")
            href = link_container['href']
            link = f"{self.config.base_url}{href}"
            
            # Create title node using standardized factory
            title_node = self.create_structure_node(
                parent_id=self.config.corpus_id,
                level_classifier=level_classifier,
                number=number,
                name=node_name,
                link=link,
                top_level_title=number
            )
            
            # Insert title node
            self.insert_node_safely(title_node)
            
            # Recursively scrape this title's contents
            self.recursive_scrape(title_node)
    
    def recursive_scrape(self, node_parent: Node) -> None:
        """
        Recursively scrape structure and content nodes.
        
        PRESERVED: Original recursive logic with Idaho-specific patterns
        """
        soup = self.web_fetcher.get_soup(str(node_parent.link))
        
        # The first vc-column-inner-wrapper is for page banner
        table_container = soup.find_all("div", class_="vc-column-innner-wrapper")[1]
        
        rows = table_container.find_all("tr")
        for i, row in enumerate(rows):
            all_tds = row.find_all("td")
            link_container = all_tds[0].find("a")
            status = None
            
            try:
                link = self.config.base_url + link_container['href']
                node_type = "structure"
            except:
                link = str(node_parent.link)
                status = "reserved"
            
            # Handle sections specifically
            if "SECT" in link and status is None:
                node_name = link_container.get_text().strip() + " " + all_tds[2].get_text().strip()
                number = node_name.split(" ")[0]
                number = number.split("-")[-1]
                level_classifier = "section"
                node_type = "content"
                citation = f"I.C. {node_parent.top_level_title} § {number}"
                
                # Create section node using standardized factory
                section_node = self.create_content_node(
                    parent_id=node_parent.node_id,
                    number=number,
                    name=node_name,
                    link=link,
                    citation=citation,
                    top_level_title=node_parent.top_level_title
                )
                
                # Scrape section content and insert
                self.scrape_section(section_node)
                continue
            
            # Handle structure nodes (chapters, articles)
            try:
                node_name_start = link_container.get_text()
                level_classifier = node_name_start.split(" ")[0].lower()
                
                # Found broken parts of the site: https://legislature.idaho.gov/statutesrules/idstat/Title41/T41CH35/
                if level_classifier.strip() == "":
                    raise ValueError(f"Stupid Idaho broke this particular page: {link}")
                
                # Handle weird cases. See us/id/statutes/title=40/chapter=16, considering this an article
                if level_classifier not in ALLOWED_LEVELS:
                    level_classifier = "article"
                    number = node_name_start
                else:
                    number = node_name_start.split(" ")[1]
                    number = number.replace(".", "")
                
                if "[" in node_name_start and "]" in node_name_start:
                    # Set the node number to the number in the brackets
                    number = node_name_start.split("[")[1].split("]")[0]
            
            except:
                continue
            
            name_container = all_tds[2]
            node_name_end = name_container.get_text()
            node_name = node_name_start + " " + node_name_end
            
            if "REDESIGNATED" in node_name:
                status = "reserved"
            
            # Create structure node using standardized factory
            structure_node = self.create_structure_node(
                parent_id=node_parent.node_id,
                level_classifier=level_classifier,
                number=number,
                name=node_name,
                link=link,
                top_level_title=node_parent.top_level_title,
                status=status
            )
            
            # Insert structure node
            self.insert_node_safely(structure_node)
            
            # Continue recursion if not reserved
            if not status:
                self.recursive_scrape(structure_node)
    
    def scrape_section(self, current_node: Node) -> None:
        """
        Extract section content and addendum.
        
        PRESERVED: Original section scraping logic
        """
        soup = self.web_fetcher.get_soup(str(current_node.link))
        container = soup.find(class_="pgbrk")
        
        if not container:
            self.logger.warning(f"Could not find content container for {current_node.link}")
            self.insert_node_safely(current_node)
            return
        
        node_text = NodeText()
        addendum = Addendum(history=AddendumType(type="history", text=""))
        found_addendum = False
        
        for i, div in enumerate(container.find_all("div")):
            # Skip divs containing Title and Chapter headings
            if i < 4:
                continue
            
            txt = div.get_text().strip()
            
            if found_addendum or "History:" in txt:
                found_addendum = True
                addendum.history.text += txt
            else:
                node_text.add_paragraph(text=txt)
        
        current_node.node_text = node_text
        current_node.addendum = addendum
        self.insert_node_safely(current_node)
    
    def _show_comprehensive_stats(self) -> None:
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


def main():
    """Main entry point for Idaho scraper with enhanced debugging support."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Idaho Statutes Scraper")
    parser.add_argument("--mode", choices=["resume", "clean", "skip"], default="resume",
                       help="Scraping mode (default: resume)")
    parser.add_argument("--skip-title", type=int, help="Title number to skip to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--timeout", type=int, help="Timeout in minutes")
    parser.add_argument("--max-titles", type=int, help="Maximum titles to process")
    parser.add_argument("--max-nodes", type=int, help="Maximum nodes to create")
    parser.add_argument("--validation", action="store_true", 
                       help="Enable validation mode (2 min timeout, 3 titles max, 100 nodes max)")
    
    args = parser.parse_args()
    mode_map = {"resume": ScrapingMode.RESUME, "clean": ScrapingMode.CLEAN, "skip": ScrapingMode.SKIP}
    
    try:
        # Create scraper with timeout and limits passed to constructor
        scraper = IdahoStatutesScraper(
            debug_mode=args.debug,
            mode=mode_map[args.mode],
            skip_title=args.skip_title,
            timeout_minutes=args.timeout,
            max_titles=args.max_titles,
            max_nodes=args.max_nodes,
            validation_mode=args.validation
        )
        
        if args.validation:
            scraper.logger.info("🔍 VALIDATION MODE: 2 min timeout, 3 titles max, 100 nodes max")
        
        scraper.scrape()
        print(f"✅ Idaho scraping completed successfully in {args.mode} mode!")
        
    except Exception as e:
        print(f"❌ Idaho scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()