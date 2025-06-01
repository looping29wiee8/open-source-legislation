"""
Unified text processing utilities for open-source-legislation.

This module provides standardized text processing based on eCFR best practices,
replacing the inconsistent text cleaning approaches found across scrapers.

Key features:
- Standardized text cleaning pipeline
- BeautifulSoup element processing
- NodeText extraction utilities  
- Addendum and metadata extraction
- Customizable cleaning patterns for jurisdiction-specific needs
"""

import re
from bs4 import BeautifulSoup, Tag, NavigableString
from typing import Optional, List, Dict, Any, Union
from src.utils.pydanticModels import NodeText, Addendum, AddendumType


class TextProcessor:
    """
    Unified text processing utilities.
    
    This class standardizes the text processing approaches found across scrapers:
    
    Arizona (Simple):
    ```python
    txt = p.get_text().strip()
    ```
    
    eCFR (Complex but sophisticated):
    ```python  
    def get_text_clean(element, direct_children_only=False):
        text = element.get_text().replace('\\xa0', ' ').replace('\\r', ' ').replace('\\n', '').strip()
        clean_text = re.sub('<.*?>', '', text)
        clean_text = clean_text.replace("—", "-").replace("–", "-")
        return clean_text
    ```
    
    California (Inconsistent):
    ```python
    text_to_add = p_tag.get_text().strip()
    if(text_to_add == ""):
        continue
    ```
    """
    
    # Standard character replacements based on eCFR best practices
    DEFAULT_REPLACEMENTS = {
        '\xa0': ' ',    # Non-breaking space
        '\r': ' ',      # Carriage return
        '\n': ' ',      # Newline  
        '\t': ' ',      # Tab
        '—': '-',       # Em dash
        '–': '-',       # En dash
        '"': '"',       # Left double quotation mark
        '"': '"',       # Right double quotation mark
        ''': "'",       # Left single quotation mark
        ''': "'",       # Right single quotation mark
    }
    
    @staticmethod
    def clean_text(
        element: Union[Tag, NavigableString, str], 
        direct_children_only: bool = False,
        normalize_whitespace: bool = True,
        remove_html: bool = True,
        custom_replacements: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Standardized text cleaning based on eCFR best practices.
        
        This replaces the inconsistent text cleaning approaches found across scrapers
        with a single, configurable method that handles common edge cases.
        
        Args:
            element: BeautifulSoup element, NavigableString, or string to clean
            direct_children_only: If True, only get text from direct children
            normalize_whitespace: If True, normalize all whitespace to single spaces
            remove_html: If True, remove any remaining HTML tags
            custom_replacements: Additional character replacements for jurisdiction-specific needs
            
        Returns:
            str: Cleaned text
            
        Example:
            ```python
            # Basic usage (replaces simple .strip())
            clean_text = TextProcessor.clean_text(element)
            
            # Advanced usage with custom replacements
            az_replacements = {"A.R.S.": "Arizona Revised Statutes"}
            clean_text = TextProcessor.clean_text(element, custom_replacements=az_replacements)
            ```
        """
        if element is None:
            return ""
            
        # Extract text based on element type
        if isinstance(element, str):
            text = element
        elif isinstance(element, NavigableString):
            text = str(element)
        elif isinstance(element, Tag):
            if direct_children_only:
                # Only get text from direct children, preserving structure
                text = element.get_text(separator=' ', strip=True)
            else:
                text = element.get_text()
        else:
            text = str(element)
        
        # Apply standard character replacements
        replacements = TextProcessor.DEFAULT_REPLACEMENTS.copy()
        if custom_replacements:
            replacements.update(custom_replacements)
            
        for old_char, new_char in replacements.items():
            text = text.replace(old_char, new_char)
        
        # Remove HTML tags if any remain
        if remove_html:
            text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        if normalize_whitespace:
            text = re.sub(r'\s+', ' ', text)
            
        return text.strip()
    
    @staticmethod
    def extract_node_text(
        container: Tag, 
        tag_filter: Union[str, List[str]] = "p",
        skip_empty: bool = True,
        preserve_structure: bool = False,
        custom_paragraph_patterns: Optional[List[str]] = None
    ) -> NodeText:
        """
        Extract NodeText from container with standardized logic.
        
        This provides a consistent way to extract structured text content
        from HTML containers, replacing ad-hoc text extraction patterns.
        
        Args:
            container: BeautifulSoup container element
            tag_filter: HTML tag(s) to extract (e.g., "p", ["p", "div", "li"])
            skip_empty: Whether to skip empty paragraphs
            preserve_structure: Whether to maintain paragraph hierarchy
            custom_paragraph_patterns: Custom patterns for identifying paragraphs
            
        Returns:
            NodeText: Structured text content
            
        Example:
            ```python
            # Basic paragraph extraction
            node_text = TextProcessor.extract_node_text(section_container)
            
            # Extract from multiple tag types
            node_text = TextProcessor.extract_node_text(
                container, 
                tag_filter=["p", "div", "li"]
            )
            
            # Custom patterns for Arizona's unique structure
            az_patterns = [r"^\([a-z]\)", r"^\d+\."]  # (a), 1., etc.
            node_text = TextProcessor.extract_node_text(
                container,
                custom_paragraph_patterns=az_patterns
            )
            ```
        """
        node_text = NodeText()
        
        # Handle both single tag and multiple tags
        if isinstance(tag_filter, str):
            tag_filter = [tag_filter]
        
        # Find all relevant elements
        elements = []
        for tag in tag_filter:
            elements.extend(container.find_all(tag))
        
        # Sort by document order if preserving structure
        if preserve_structure:
            elements.sort(key=lambda x: list(container.descendants).index(x))
        
        for i, element in enumerate(elements):
            text = TextProcessor.clean_text(element)
            
            if skip_empty and not text:
                continue
            
            # Generate paragraph ID
            paragraph_id = f"#p-{len(node_text.paragraphs)}"
            
            # Determine classification using custom patterns
            classification = TextProcessor._classify_paragraph(text, custom_paragraph_patterns)
            
            # Add paragraph to NodeText
            node_text.add_paragraph(
                text=text,
                paragraph_id=paragraph_id,
                classification=classification
            )
            
        return node_text
    
    @staticmethod
    def _classify_paragraph(text: str, custom_patterns: Optional[List[str]] = None) -> Optional[str]:
        """
        Classify paragraph based on content patterns.
        
        Args:
            text: Paragraph text to classify
            custom_patterns: Custom classification patterns
            
        Returns:
            Optional[str]: Classification or None
        """
        if not text:
            return None
            
        # Standard classification patterns
        patterns = {
            'definition': [r'^As used in this', r'^For purposes of this', r'^In this [a-z]+,'],
            'subsection': [r'^\([a-z]\)', r'^\([0-9]+\)'],
            'numbered': [r'^\d+\.', r'^\d+\s'],
            'lettered': [r'^[A-Z]\.', r'^[a-z]\.'],
        }
        
        # Add custom patterns if provided
        if custom_patterns:
            patterns['custom'] = custom_patterns
        
        for classification, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.match(pattern, text.strip()):
                    return classification
                    
        return None
    
    @staticmethod
    def extract_addendum(
        text: str, 
        patterns: Optional[List[str]] = None,
        addendum_type: AddendumType = AddendumType.HISTORICAL
    ) -> Optional[Addendum]:
        """
        Extract addendum information using standardized patterns.
        
        This standardizes the extraction of metadata, historical notes,
        source information, and other addenda from legislative text.
        
        Args:
            text: Text to extract addendum from
            patterns: Custom regex patterns for extraction
            addendum_type: Type of addendum to create
            
        Returns:
            Optional[Addendum]: Extracted addendum or None
            
        Example:
            ```python
            # Extract standard addendum patterns
            addendum = TextProcessor.extract_addendum(
                "Some text [Added by Laws 2023, Ch. 100, § 1.]"
            )
            
            # Custom patterns for Arizona
            az_patterns = [r'\\[Added by Laws (\\d+),.*?\\]']
            addendum = TextProcessor.extract_addendum(text, az_patterns)
            ```
        """
        if not text:
            return None
            
        if patterns is None:
            patterns = [
                r'\[([^\]]+)\]$',        # Text in square brackets at end
                r'\(([^)]+)\)$',         # Text in parentheses at end  
                r'SOURCE:\s*(.+)$',      # Source information
                r'HISTORY:\s*(.+)$',     # History information
                r'EFFECTIVE DATE:\s*(.+)$',  # Effective date
                r'Added by Laws (\d+),\s*(.+)$',  # Arizona-style additions
                r'Amended by Laws (\d+),\s*(.+)$',  # Arizona-style amendments
            ]
            
        for pattern in patterns:
            match = re.search(pattern, text.strip(), re.IGNORECASE)
            if match:
                addendum_text = match.group(1).strip()
                
                return Addendum(
                    addendum_type=addendum_type,
                    addendum_text=addendum_text,
                    source_text=text
                )
                
        return None
    
    @staticmethod
    def extract_citation(
        text: str,
        jurisdiction_patterns: Optional[Dict[str, List[str]]] = None
    ) -> Optional[str]:
        """
        Extract legal citations from text using jurisdiction-specific patterns.
        
        Args:
            text: Text to extract citation from
            jurisdiction_patterns: Custom citation patterns by jurisdiction
            
        Returns:
            Optional[str]: Extracted citation or None
            
        Example:
            ```python
            # Standard citation extraction
            citation = TextProcessor.extract_citation("See A.R.S. § 1-101")
            # Returns: "A.R.S. § 1-101"
            
            # Custom patterns for specific jurisdictions
            az_patterns = [r'A\.R\.S\.\s*§\s*[\d-]+']
            citation = TextProcessor.extract_citation(
                text, 
                {"arizona": az_patterns}
            )
            ```
        """
        if not text:
            return None
            
        # Standard citation patterns
        patterns = [
            r'(?:A\.R\.S\.|ARS)\s*§\s*[\d-]+(?:\.[A-Z])?',  # Arizona
            r'(?:Cal\.|California)\s*(?:Code|Gov\.)\s*§\s*[\d-]+',  # California
            r'\d+\s+U\.S\.C\.\s*§\s*[\d-]+',  # Federal USC
            r'C\.F\.R\.\s*§\s*[\d.-]+',  # CFR
            r'§\s*[\d.-]+(?:\([a-z0-9]+\))*',  # Generic section
        ]
        
        # Add jurisdiction-specific patterns
        if jurisdiction_patterns:
            for jurisdiction, custom_patterns in jurisdiction_patterns.items():
                patterns.extend(custom_patterns)
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
                
        return None
    
    @staticmethod
    def split_into_sections(
        text: str,
        section_patterns: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Split long text into logical sections based on patterns.
        
        Args:
            text: Text to split
            section_patterns: Regex patterns that indicate section breaks
            
        Returns:
            List[Dict[str, str]]: List of sections with metadata
            
        Example:
            ```python
            sections = TextProcessor.split_into_sections(
                long_text,
                section_patterns=[r'^SECTION \d+', r'^\([a-z]\)']
            )
            ```
        """
        if not text or not section_patterns:
            return [{"text": text, "type": "full"}]
            
        sections = []
        current_section = ""
        current_type = "content"
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line matches any section pattern
            matched_pattern = None
            for pattern in section_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    matched_pattern = pattern
                    break
            
            if matched_pattern:
                # Save previous section if it has content
                if current_section.strip():
                    sections.append({
                        "text": current_section.strip(),
                        "type": current_type
                    })
                
                # Start new section
                current_section = line
                current_type = "header"
            else:
                # Add to current section
                if current_section:
                    current_section += "\n" + line
                else:
                    current_section = line
                current_type = "content"
        
        # Add final section
        if current_section.strip():
            sections.append({
                "text": current_section.strip(),
                "type": current_type
            })
            
        return sections
    
    @staticmethod
    def clean_jurisdiction_specific(
        text: str,
        jurisdiction: str,
        custom_rules: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Apply jurisdiction-specific text cleaning rules.
        
        This allows scrapers to apply custom cleaning logic while
        still benefiting from the standardized base processing.
        
        Args:
            text: Text to clean
            jurisdiction: Jurisdiction code (e.g., "az", "ca", "federal")
            custom_rules: Additional cleaning rules
            
        Returns:
            str: Cleaned text with jurisdiction-specific rules applied
        """
        if not text:
            return ""
            
        # Jurisdiction-specific cleaning rules
        jurisdiction_rules = {
            "az": {
                "replacements": {
                    "A.R.S.": "Arizona Revised Statutes",
                    "Ch.": "Chapter"
                },
                "patterns_to_remove": [
                    r'\[Added by Laws \d+.*?\]',  # Remove legislative history
                ]
            },
            "ca": {
                "replacements": {
                    "Cal.": "California",
                    "Gov. Code": "Government Code"
                },
                "patterns_to_remove": [
                    r'\(Added by Stats\. \d+.*?\)',
                ]
            },
            "federal": {
                "replacements": {
                    "U.S.C.": "United States Code",
                    "C.F.R.": "Code of Federal Regulations"
                },
                "patterns_to_remove": [
                    r'\[Source:.*?\]',
                ]
            }
        }
        
        # Apply jurisdiction rules if available
        if jurisdiction in jurisdiction_rules:
            rules = jurisdiction_rules[jurisdiction]
            
            # Apply replacements
            if "replacements" in rules:
                for old, new in rules["replacements"].items():
                    text = text.replace(old, new)
            
            # Remove patterns
            if "patterns_to_remove" in rules:
                for pattern in rules["patterns_to_remove"]:
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Apply custom rules
        if custom_rules:
            if "replacements" in custom_rules:
                for old, new in custom_rules["replacements"].items():
                    text = text.replace(old, new)
            
            if "patterns_to_remove" in custom_rules:
                for pattern in custom_rules["patterns_to_remove"]:
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Final cleanup
        return TextProcessor.clean_text(text)


class TextAnalyzer:
    """
    Advanced text analysis utilities for legislative content.
    
    Provides analysis capabilities beyond basic cleaning, such as
    content type detection, complexity scoring, and structure analysis.
    """
    
    @staticmethod
    def detect_content_type(text: str) -> str:
        """
        Detect the type of legislative content.
        
        Args:
            text: Text to analyze
            
        Returns:
            str: Content type (definition, procedure, penalty, etc.)
        """
        if not text:
            return "unknown"
            
        text_lower = text.lower()
        
        # Definition patterns
        if any(phrase in text_lower for phrase in ["as used in", "means", "for purposes of"]):
            return "definition"
        
        # Penalty patterns  
        if any(phrase in text_lower for phrase in ["fine", "imprisonment", "penalty", "violation"]):
            return "penalty"
        
        # Procedure patterns
        if any(phrase in text_lower for phrase in ["shall", "must", "required to", "procedure"]):
            return "procedure"
        
        # Exception patterns
        if any(phrase in text_lower for phrase in ["except", "unless", "provided that"]):
            return "exception"
        
        return "general"
    
    @staticmethod
    def calculate_complexity_score(text: str) -> float:
        """
        Calculate a complexity score for legislative text.
        
        Args:
            text: Text to analyze
            
        Returns:
            float: Complexity score (0.0 to 1.0, higher = more complex)
        """
        if not text:
            return 0.0
        
        # Factors that increase complexity
        sentence_count = len(re.findall(r'[.!?]+', text))
        word_count = len(text.split())
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Long sentences increase complexity
        length_score = min(avg_sentence_length / 25.0, 1.0)
        
        # Legal jargon increases complexity
        legal_terms = [
            "whereas", "heretofore", "pursuant", "notwithstanding",
            "aforementioned", "thereof", "hereby", "wherein"
        ]
        jargon_count = sum(1 for term in legal_terms if term in text.lower())
        jargon_score = min(jargon_count / 5.0, 1.0)
        
        # Nested references increase complexity
        reference_count = len(re.findall(r'§\s*[\d.-]+', text))
        reference_score = min(reference_count / 10.0, 1.0)
        
        # Combined complexity score
        complexity = (length_score + jargon_score + reference_score) / 3.0
        return min(complexity, 1.0)