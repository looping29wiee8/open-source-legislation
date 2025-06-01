"""
Node factory patterns for consistent Node creation across scrapers.

This module provides the NodeFactory class that standardizes Node creation
patterns, replacing the inconsistent Node creation logic found across scrapers.

Key features:
- Consistent NodeID generation using hierarchical patterns
- Standardized status determination (reserved, repealed, etc.)
- Template methods for structure vs. content nodes
- Built-in validation and error handling
- Support for jurisdiction-specific customization
"""

import re
from typing import Optional, List, Dict, Any
from src.utils.pydanticModels import Node, NodeID, NodeText, Addendum


class NodeFactory:
    """
    Factory for creating standardized Node instances.
    
    This class addresses the inconsistent Node creation patterns found
    across scrapers, particularly:
    
    Arizona (Good pattern):
    ```python
    title_node = Node(
        id=title_node_id,
        link=url,
        top_level_title=top_level_title,
        node_type=node_type, 
        level_classifier=level_classifier,
        node_name=title_name,
        parent=parent,
        number=number
    )
    ```
    
    California (Problematic):
    ```python
    node_id = f"{node_parent.node_id}"  # Should use NodeID class
    new_partial_node.id = new_partial_node.id.add_level(
        new_partial_node.level_classifier, 
        new_partial_node.number
    )
    ```
    """
    
    # Standard reserved keywords that indicate non-active nodes
    DEFAULT_RESERVED_KEYWORDS = [
        "REPEALED", "RESERVED", "TRANSFERRED", "OMITTED", 
        "DELETED", "EXPIRED", "SUPERSEDED"
    ]
    
    @staticmethod
    def create_structure_node(
        parent_id: str,
        level_classifier: str,
        number: str,
        name: str,
        link: str,
        top_level_title: str,
        status: Optional[str] = None,
        citation: Optional[str] = None,
        reserved_keywords: Optional[List[str]] = None
    ) -> Node:
        """
        Create a structure node with consistent ID generation.
        
        This standardizes the structure node creation pattern used
        across all scrapers for titles, chapters, articles, etc.
        
        Args:
            parent_id: Parent node ID (e.g., "us/az/statutes")
            level_classifier: Node level (e.g., "title", "chapter", "article")
            number: Node number (e.g., "1", "2A", "101")
            name: Node name (e.g., "General Provisions")
            link: URL to the node's content
            top_level_title: Top-level title identifier
            status: Optional explicit status
            citation: Optional citation string
            reserved_keywords: Custom reserved keywords for this jurisdiction
            
        Returns:
            Node: Standardized structure node
            
        Example:
            ```python
            title_node = NodeFactory.create_structure_node(
                parent_id="us/az/statutes",
                level_classifier="title",
                number="1",
                name="Title 1 - General Provisions",
                link="https://www.azleg.gov/ars/title1/",
                top_level_title="1"
            )
            ```
        """
        # Generate hierarchical ID using NodeID class
        parent_node_id = NodeID(raw_id=parent_id)
        node_id = parent_node_id.add_level(level_classifier.lower(), number)
        
        # Determine status using standardized logic
        final_status = NodeFactory._determine_status(
            name, status, reserved_keywords
        )
        
        return Node(
            id=node_id,
            citation=citation,
            link=link,
            status=final_status,
            node_type="structure",
            top_level_title=top_level_title,
            level_classifier=level_classifier.upper(),
            number=number,
            node_name=name,
            parent=parent_id
        )
    
    @staticmethod  
    def create_content_node(
        parent_id: str,
        number: str,
        name: str,
        link: str,
        citation: str,
        top_level_title: str,
        node_text: Optional[NodeText] = None,
        addendum: Optional[Addendum] = None,
        status: Optional[str] = None,
        level_classifier: str = "section",
        reserved_keywords: Optional[List[str]] = None
    ) -> Node:
        """
        Create a content node with standardized structure.
        
        Content nodes contain the actual text of legislation and
        require special handling for text content and addenda.
        
        Args:
            parent_id: Parent node ID
            number: Section number
            name: Section name/title
            link: URL to section content
            citation: Legal citation (required for content nodes)
            top_level_title: Top-level title identifier
            node_text: Optional NodeText with paragraph content
            addendum: Optional addendum with metadata
            status: Optional explicit status
            level_classifier: Level classifier (default: "section")
            reserved_keywords: Custom reserved keywords
            
        Returns:
            Node: Standardized content node
        """
        # Generate hierarchical ID
        parent_node_id = NodeID(raw_id=parent_id)
        node_id = parent_node_id.add_level(level_classifier.lower(), number)
        
        # Determine status
        final_status = NodeFactory._determine_status(
            name, status, reserved_keywords
        )
        
        return Node(
            id=node_id,
            citation=citation,
            link=link,
            status=final_status,
            node_type="content",
            top_level_title=top_level_title,
            level_classifier=level_classifier.upper(),
            number=number,
            node_name=name,
            parent=parent_id,
            node_text=node_text,
            addendum=addendum
        )
    
    @staticmethod
    def create_jurisdiction_node(
        country: str,
        jurisdiction: str,
        corpus: str,
        base_url: Optional[str] = None
    ) -> Node:
        """
        Create the base jurisdiction and corpus nodes.
        
        This replaces the insert_jurisdiction_and_corpus_node() pattern
        with a factory method that returns the corpus node.
        
        Args:
            country: Country code (e.g., "us")
            jurisdiction: Jurisdiction code (e.g., "az", "federal")
            corpus: Corpus type (e.g., "statutes", "regulations")
            base_url: Optional base URL for the jurisdiction
            
        Returns:
            Node: The corpus node (jurisdiction node is created as parent)
        """
        # Create jurisdiction node ID
        jurisdiction_id = f"{country}/{jurisdiction}"
        
        # Create corpus node ID  
        corpus_id = f"{country}/{jurisdiction}/{corpus}"
        
        return Node(
            id=corpus_id,
            link=base_url,
            node_type="structure",
            level_classifier="corpus",
            node_name=f"{jurisdiction.upper()} {corpus.title()}",
            parent=jurisdiction_id
        )
    
    @staticmethod
    def _determine_status(
        name: str, 
        explicit_status: Optional[str],
        reserved_keywords: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Determine node status based on name and explicit status.
        
        This standardizes the status determination logic that was
        scattered across different scrapers with different approaches.
        
        Args:
            name: Node name to analyze
            explicit_status: Explicitly provided status
            reserved_keywords: Custom reserved keywords for jurisdiction
            
        Returns:
            Optional[str]: Determined status or None
        """
        if explicit_status:
            return explicit_status
            
        # Use custom keywords if provided, otherwise use defaults
        keywords = reserved_keywords or NodeFactory.DEFAULT_RESERVED_KEYWORDS
        
        name_upper = name.upper()
        
        for keyword in keywords:
            if keyword in name_upper:
                return "reserved"
                
        return None
    
    @staticmethod
    def extract_number_from_name(name: str, patterns: Optional[List[str]] = None) -> Optional[str]:
        """
        Extract number from node name using common patterns.
        
        This standardizes number extraction logic that varies across scrapers.
        
        Args:
            name: Node name (e.g., "Title 1 - General Provisions")
            patterns: Custom regex patterns for number extraction
            
        Returns:
            Optional[str]: Extracted number or None
            
        Example:
            ```python
            number = NodeFactory.extract_number_from_name("Title 1 - General")
            # Returns: "1"
            
            number = NodeFactory.extract_number_from_name("Chapter 2A")  
            # Returns: "2A"
            ```
        """
        if patterns is None:
            patterns = [
                r'^(?:Title|Chapter|Article|Section|Part)\s+([A-Z]?\d+[A-Z]?)',
                r'^([A-Z]?\d+[A-Z]?)\s*[-.]',
                r'^(\d+[A-Z]?)\.',
                r'(\d+[A-Z]?)$'
            ]
        
        for pattern in patterns:
            match = re.search(pattern, name.strip(), re.IGNORECASE)
            if match:
                return match.group(1)
                
        return None
    
    @staticmethod
    def clean_node_name(name: str, remove_number: bool = False) -> str:
        """
        Clean and standardize node names.
        
        Args:
            name: Raw node name
            remove_number: Whether to remove leading numbers/prefixes
            
        Returns:
            str: Cleaned node name
        """
        # Basic cleaning
        cleaned = name.strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
        
        if remove_number:
            # Remove leading number patterns
            patterns = [
                r'^(?:Title|Chapter|Article|Section|Part)\s+[A-Z]?\d+[A-Z]?\s*[-.]?\s*',
                r'^[A-Z]?\d+[A-Z]?\s*[-.]?\s*'
            ]
            for pattern in patterns:
                cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
                
        return cleaned.strip()


class NodeBuilder:
    """
    Builder pattern for complex Node creation scenarios.
    
    This provides a fluent interface for building nodes when the factory
    methods are too restrictive or when building nodes incrementally.
    """
    
    def __init__(self):
        self._data = {}
        
    def parent(self, parent_id: str) -> 'NodeBuilder':
        """Set parent node ID."""
        self._data['parent'] = parent_id
        return self
        
    def level(self, classifier: str, number: str) -> 'NodeBuilder':
        """Set level classifier and number."""
        self._data['level_classifier'] = classifier.upper()
        self._data['number'] = number
        return self
        
    def name(self, name: str) -> 'NodeBuilder':
        """Set node name."""
        self._data['node_name'] = name
        return self
        
    def link(self, url: str) -> 'NodeBuilder':
        """Set node link."""
        self._data['link'] = url
        return self
        
    def type(self, node_type: str) -> 'NodeBuilder':
        """Set node type (structure or content)."""
        if node_type not in ["structure", "content"]:
            raise ValueError("Node type must be 'structure' or 'content'")
        self._data['node_type'] = node_type
        return self
        
    def title(self, top_level_title: str) -> 'NodeBuilder':
        """Set top level title."""
        self._data['top_level_title'] = top_level_title
        return self
        
    def status(self, status: str) -> 'NodeBuilder':
        """Set node status."""
        self._data['status'] = status
        return self
        
    def citation(self, citation: str) -> 'NodeBuilder':
        """Set citation."""
        self._data['citation'] = citation
        return self
        
    def text(self, node_text: NodeText) -> 'NodeBuilder':
        """Set node text content."""
        self._data['node_text'] = node_text
        return self
        
    def addendum(self, addendum: Addendum) -> 'NodeBuilder':
        """Set addendum."""
        self._data['addendum'] = addendum
        return self
        
    def build(self) -> Node:
        """
        Build the Node with current configuration.
        
        Returns:
            Node: Constructed node
            
        Raises:
            ValueError: If required fields are missing
        """
        # Validate required fields
        required = ['parent', 'level_classifier', 'number', 'node_name', 'node_type']
        missing = [field for field in required if field not in self._data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
            
        # Generate node ID
        parent_id = self._data['parent']
        level_classifier = self._data['level_classifier']
        number = self._data['number']
        
        parent_node_id = NodeID(raw_id=parent_id)
        node_id = parent_node_id.add_level(level_classifier.lower(), number)
        
        # Build node
        node_data = dict(self._data)
        node_data['id'] = node_id
        
        return Node(**node_data)