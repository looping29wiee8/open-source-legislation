from src.utils.base import setup_project_path, BaseScraper, ConfigManager
from src.utils.processing import TextProcessor, WebFetcher
from src.utils.processing.database import ScrapingMode
setup_project_path()

# BeautifulSoup imports
from bs4 import BeautifulSoup
from bs4.element import Tag

# Selenium imports (if needed for future enhancements)
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver import ActionChains
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from typing import List, Tuple, Optional
import time
import json
import re

from src.utils.pydanticModels import NodeID, Node, Addendum, AddendumType, NodeText, Paragraph, ReferenceHub, Reference, DefinitionHub, Definition, IncorporatedTerms


class DelawareStatutesScraper(BaseScraper):
    def __init__(self, debug_mode: bool = False, mode: ScrapingMode = ScrapingMode.RESUME, skip_title: Optional[int] = None):
        # Delaware-specific configuration defined inline
        config = ConfigManager.create_custom_config(
            country="us",
            jurisdiction="de",
            corpus="statutes",
            base_url="https://delcode.delaware.gov",
            toc_url="https://delcode.delaware.gov",
            skip_title=0,  # Delaware starts from title 0 but skips Constitution at index 0
            reserved_keywords=["[Repealed", "[Expired", "[Reserved"],
            delay_seconds=1.5,
            debug_mode=debug_mode
        )
        super().__init__(config, mode=mode, skip_title=skip_title)
        
        # Initialize standardized web fetcher
        self.web_fetcher = WebFetcher(
            delay_seconds=1.5,
            max_retries=3,
            timeout=30
        )
        
        # Delaware-specific text processing configuration
        self.de_config = {
            "custom_replacements": {
                "Del. C.": "Delaware Code"
            },
            "citation_patterns": [r'\d+\s+Del\.\s*C\.\s*§\s*[\d-]+'],
            "addendum_patterns": [r'\[.*?\]']
        }

    def scrape_implementation(self) -> None:
        """
        Delaware-specific scraping logic.
        
        PRESERVED: All original parsing logic exactly as-is
        UPDATED: Infrastructure to use standardized framework
        """
        self.logger.info("Starting Delaware statutes scraping")
        
        # PRESERVED: Original main function logic
        self.scrape_all_titles()

    def scrape_all_titles(self):
        """PRESERVED: Original scrape_all_titles function with updated infrastructure calls"""
        soup = self.web_fetcher.get_soup(self.config.toc_url).find(id="content")
        
        all_title_containers = soup.find_all("a")
        
        for i, title_container in enumerate(all_title_containers):
            if i < self.config.skip_title:
                continue
            # Skip the delaware constitution
            if i == 0:
                continue
            href = title_container['href'].strip()
            if "/index.html" not in href:
                continue
            
            node_name = title_container.get_text().strip()
            number = node_name.split(" ")[1]
            top_level_title = number
            level_classifier = "title"
            link = f"{self.config.base_url}/{href}"
            
            # NEW: Use NodeFactory for consistent Node creation
            title_node = self.create_structure_node(
                parent_id=self.config.corpus_id,
                level_classifier=level_classifier,
                number=number,
                name=node_name,
                link=link,
                top_level_title=top_level_title
            )
            
            # NEW: Use standardized database insertion
            self.insert_node_safely(title_node)

            self.recursive_scrape(title_node)

    def recursive_scrape(self, node_parent: Node):
        """PRESERVED: Original recursive_scrape function with updated infrastructure calls"""
        soup = self.web_fetcher.get_soup(str(node_parent.link)).find(id="content")
        
        # Indicates page contains sections, send to section scrape function
        if soup.find(id="CodeBody"):
            self.scrape_sections(node_parent, soup)
        else:
            structure_node_containers = soup.find_all("div", class_="title-links")
            # Iterate over the container of the structure nodes
            for i, structure_container in enumerate(structure_node_containers):
                link_container = structure_container.find("a")
                href = link_container['href'].strip()
                
                link = href.replace("../","")
                link = f"{self.config.toc_url}/{link}"
                node_name = link_container.get_text().strip()
                level_classifier = node_name.split(" ")[0].lower()
                number = node_name.split(" ")[1]

                if number[-1] == ".":
                    number=number[:-1]

                parent = node_parent.node_id
                top_level_title = node_parent.top_level_title

                status = None
                for word in self.config.reserved_keywords:
                    if word in node_name:
                        status = word.lower()
                        break

                # NEW: Use NodeFactory for consistent Node creation
                structure_node = self.create_structure_node(
                    parent_id=parent,
                    level_classifier=level_classifier,
                    number=number,
                    name=node_name,
                    link=link,
                    top_level_title=top_level_title,
                    status=status
                )
                
                # NEW: Use standardized database insertion
                self.insert_node_safely(structure_node)
                self.recursive_scrape(structure_node)

    def scrape_sections(self, node_parent: Node, soup: BeautifulSoup):
        """PRESERVED: Original scrape_sections function with updated infrastructure calls"""
        # Scrape a section regularly
        
        section_containers = soup.find_all("div", class_="Section")

        for i, div in enumerate(section_containers):
            
            section_header = div.find("div", class_="SectionHead")
            node_name = section_header.get_text().strip()
            # Clean up super weird formatting
            node_name = node_name.replace("§", "")
            node_name = node_name.strip()
            node_name = f"§ {node_name}"
            
            # This is legacy code, I have no idea. Im not gonna touch it for now
            number = section_header['id']
            
            link = str(node_parent.link) + f"#{number}"

            number = number.replace(",", "-").rstrip(".")
            
            status = None
            for word in self.config.reserved_keywords:
                if word in node_name:
                    status = "reserved"
                    break
            
            node_text = None
            citation = f"{node_parent.top_level_title} Del. C. § {number}"

            # Finding addendum
            addendum = None
            core_metadata = None
            
            if not status:
                node_text = NodeText()
                addendum = Addendum()
                addendum.history = AddendumType(type="history", text="")
                addendum_references = ReferenceHub()
                for element in div.find_all(recursive=False):
                    # Skip the sectionHead
                    if 'class' in element.attrs and element['class'][0] == "SectionHead":
                        continue
                    
                    # I want to remove all &nbsp; and &ensp; from the elements text
                    temp = element.get_text().strip()
                    text = temp.replace('\xc2\xa0', '').replace('\u2002', '').replace('\n', '').replace('\r            ', '').strip()
                    text = re.sub(r'\s+', ' ', text)

                    if text == "":
                        continue
                    
                    if element.name == "p":
                        node_text.add_paragraph(text=text)
                        continue
                
                    # Assume any left over text without a <p> tag is the addendum
                    addendum.history.text += text
                    
                    if element.name == "a":
                        addendum_references.references[element['href']] = Reference(text=text)
                
                if addendum_references.references == {}:
                    addendum_references = None
                addendum.history.reference_hub = addendum_references
            if addendum and addendum.history.text == "":
                addendum = None
                
            # NEW: Use NodeFactory for consistent Node creation
            section_node = self.create_content_node(
                parent_id=node_parent.node_id,
                level_classifier="section",
                number=number,
                name=node_name,
                link=link,
                citation=citation,
                top_level_title=node_parent.top_level_title,
                status=status,
                node_text=node_text,
                addendum=addendum
            )
                
            # NEW: Use standardized database insertion
            self.insert_node_safely(section_node)


def main():
    """Main entry point for Delaware scraper with enhanced debugging support."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Delaware Statutes Scraper")
    parser.add_argument("--mode", choices=["resume", "clean", "skip"], default="resume", 
                       help="Scraping mode: resume (default), clean, or skip")
    parser.add_argument("--skip-title", type=int, help="Title number to skip to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--validation", action="store_true", help="Run in validation mode (2 min timeout, 3 titles max)")
    parser.add_argument("--timeout", type=int, help="Timeout in minutes")
    parser.add_argument("--max-titles", type=int, help="Maximum titles to process")
    parser.add_argument("--max-nodes", type=int, help="Maximum nodes to create")
    
    args = parser.parse_args()
    mode_map = {"resume": ScrapingMode.RESUME, "clean": ScrapingMode.CLEAN, "skip": ScrapingMode.SKIP}
    
    try:
        scraper = DelawareStatutesScraper(
            debug_mode=args.debug,
            mode=mode_map[args.mode],
            skip_title=args.skip_title
        )
        
        # Apply validation mode settings if requested
        if args.validation:
            scraper.timeout_minutes = 2
            scraper.max_titles = 3
            scraper.max_nodes = 100
            scraper.logger.info("🔍 VALIDATION MODE: 2 min timeout, 3 titles max, 100 nodes max")
        
        # Apply custom limits if specified
        if args.timeout:
            scraper.timeout_minutes = args.timeout
        if args.max_titles:
            scraper.max_titles = args.max_titles
        if args.max_nodes:
            scraper.max_nodes = args.max_nodes
            
        scraper.scrape()
        print(f"✅ Scraping completed successfully in {args.mode} mode!")
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()