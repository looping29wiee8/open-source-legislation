"""
Unified database management for open-source-legislation scrapers.

This module provides the DatabaseManager class that standardizes all database
operations across scrapers, replacing the 3 different database insertion patterns
found in the codebase.

Key features:
- Consistent duplicate handling with versioning
- Batch insertion for performance
- Secure credential management
- Comprehensive error handling and logging
- Connection pooling and management
"""

import psycopg
import json
import logging
from typing import List, Optional, Any, Dict
from src.utils.pydanticModels import Node, NodeID
from src.utils import utilityFunctions as util
from src.utils.base.credentials import CredentialManager


class DatabaseManager:
    """
    Unified database operations for all scrapers.
    
    This class standardizes the 3 different database interaction patterns
    found across scrapers:
    1. scrapingHelpers.insert_node() - Complex duplicate handling
    2. Direct util.pydantic_insert() - Simple insertion
    3. Manual SQL with cursors - Raw database access
    
    The DatabaseManager provides a single, consistent interface with
    secure credential management and standardized error handling.
    """
    
    def __init__(self, table_name: str, user: Optional[str] = None):
        """
        Initialize database manager for a specific table.
        
        Args:
            table_name: Database table name (e.g., "us_az_statutes")
            user: Optional user for logging (uses CredentialManager if None)
        """
        self.table_name = table_name
        self.user = user or CredentialManager.get_database_user()
        self.logger = logging.getLogger(f"db.{table_name}")
        
        # Validate credentials are available
        try:
            CredentialManager.get_database_config()
        except ValueError as e:
            self.logger.error(f"Database credentials not configured: {e}")
            raise
        
    def insert_node(self, node: Node, ignore_duplicate: bool = False, 
                   debug: bool = False) -> Node:
        """
        Standardized node insertion with consistent duplicate handling.
        
        This replaces the inconsistent patterns found across scrapers:
        - scrapingHelpers.insert_node(node, table, True, True)
        - util.pydantic_insert(table, [node], user=user)
        - Manual cursor operations
        
        Args:
            node: Node to insert
            ignore_duplicate: If True, silently ignore duplicates
            debug: If True, log insertion details
            
        Returns:
            Node: The inserted node (potentially with modified ID if duplicate)
            
        Raises:
            DatabaseError: If insertion fails after all retry attempts
        """
        try:
            if debug:
                self.logger.debug(f"Inserting node: {node.node_id}")
                
            # Use existing utility function for now - will be replaced with
            # direct implementation once we verify compatibility
            util.pydantic_insert(self.table_name, [node])
            return node
            
        except psycopg.errors.UniqueViolation:
            if ignore_duplicate:
                if debug:
                    self.logger.debug(f"Ignoring duplicate: {node.node_id}")
                return node
            else:
                return self._handle_duplicate_with_version(node, debug)
                
        except Exception as e:
            self.logger.error(f"Failed to insert node {node.node_id}: {e}")
            raise DatabaseError(f"Database insertion failed: {e}") from e
    
    def _handle_duplicate_with_version(self, node: Node, debug: bool) -> Node:
        """
        Handle duplicates by adding version numbers.
        
        This implements the same versioning logic found in scrapingHelpers.insert_node()
        but with improved error handling and logging.
        """
        base_id = node.node_id
        original_id = base_id
        
        # Tag original ID in metadata for traceability
        if node.core_metadata:
            node.core_metadata["duplicated_from_node_id"] = original_id
        else:
            node.core_metadata = {"duplicated_from_node_id": original_id}
        
        for i in range(2, 10):
            try:
                # Remove any existing version number
                v_index = base_id.find("-v_")
                if v_index != -1:
                    base_id = base_id[:v_index]
                    
                new_id = f"{base_id}-v_{i}"
                node.id = NodeID(raw_id=new_id)
                
                if debug:
                    self.logger.debug(f"Trying version: {new_id}")
                    
                util.pydantic_insert(self.table_name, [node])
                
                if debug:
                    self.logger.debug(f"Successfully inserted with version: {new_id}")
                return node
                
            except psycopg.errors.UniqueViolation:
                continue
                
        # If we get here, we couldn't insert after 8 attempts
        raise DatabaseError(f"Could not insert node after 8 version attempts: {original_id}")
    
    def batch_insert(self, nodes: List[Node], batch_size: int = 100, 
                    ignore_duplicates: bool = False, debug: bool = False) -> List[Node]:
        """
        Efficient batch insertion for large datasets.
        
        This provides better performance than individual insertions and
        handles errors gracefully by attempting individual insertions
        for failed batches.
        
        Args:
            nodes: List of nodes to insert
            batch_size: Number of nodes per batch
            ignore_duplicates: Whether to ignore duplicate errors
            debug: Whether to log detailed information
            
        Returns:
            List[Node]: Successfully inserted nodes (may have modified IDs)
        """
        if not nodes:
            return []
            
        successful_nodes = []
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            
            try:
                if debug:
                    self.logger.debug(f"Batch inserting {len(batch)} nodes")
                    
                # Try batch insertion first
                util.pydantic_insert(self.table_name, batch)
                successful_nodes.extend(batch)
                
                if debug:
                    self.logger.debug(f"Batch insert successful")
                    
            except Exception as e:
                if debug:
                    self.logger.debug(f"Batch insert failed, trying individual inserts: {e}")
                
                # Fall back to individual insertions for this batch
                for node in batch:
                    try:
                        inserted_node = self.insert_node(
                            node, 
                            ignore_duplicate=ignore_duplicates, 
                            debug=debug
                        )
                        successful_nodes.append(inserted_node)
                    except Exception as individual_error:
                        self.logger.warning(
                            f"Failed to insert individual node {node.node_id}: {individual_error}"
                        )
                        if not ignore_duplicates:
                            raise
                            
        return successful_nodes
    
    def node_exists(self, node_id: str) -> bool:
        """
        Check if a node exists in the database.
        
        Args:
            node_id: Node ID to check
            
        Returns:
            bool: True if node exists, False otherwise
        """
        try:
            sql = f"SELECT 1 FROM {self.table_name} WHERE id = %s LIMIT 1"
            result = util.regular_select(sql, (node_id,))
            return len(result) > 0
        except Exception as e:
            self.logger.warning(f"Error checking node existence for {node_id}: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """
        Retrieve a single node by ID.
        
        Args:
            node_id: Node ID to retrieve
            
        Returns:
            Optional[Node]: The node if found, None otherwise
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE id = %s LIMIT 1"
            nodes = util.pydantic_select(sql, Node)
            return nodes[0] if nodes else None
        except Exception as e:
            self.logger.warning(f"Error retrieving node {node_id}: {e}")
            return None
    
    def get_children(self, parent_id: str, node_type: Optional[str] = None) -> List[Node]:
        """
        Get all child nodes of a parent.
        
        Args:
            parent_id: Parent node ID
            node_type: Optional filter by node type ("structure" or "content")
            
        Returns:
            List[Node]: Child nodes
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE parent = %s"
            params = [parent_id]
            
            if node_type:
                sql += " AND node_type = %s"
                params.append(node_type)
                
            sql += " ORDER BY id"
            
            return util.pydantic_select(sql, Node)
        except Exception as e:
            self.logger.warning(f"Error retrieving children of {parent_id}: {e}")
            return []
    
    def update_node(self, node: Node) -> bool:
        """
        Update an existing node.
        
        Args:
            node: Node with updated data
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            util.pydantic_update(self.table_name, [node], "id")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update node {node.node_id}: {e}")
            return False
    
    def delete_node(self, node_id: str) -> bool:
        """
        Delete a node by ID.
        
        Args:
            node_id: Node ID to delete
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            conn = util.db_connect()
            with conn.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {self.table_name} WHERE id = %s",
                    (node_id,)
                )
                conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete node {node_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics for this table.
        
        Returns:
            Dict[str, Any]: Statistics including counts by type, status, etc.
        """
        try:
            stats = {}
            
            # Total count
            result = util.regular_select(f"SELECT COUNT(*) FROM {self.table_name}")
            stats['total_nodes'] = result[0][0] if result else 0
            
            # Count by node type
            result = util.regular_select(
                f"SELECT node_type, COUNT(*) FROM {self.table_name} "
                f"WHERE node_type IS NOT NULL GROUP BY node_type"
            )
            stats['by_type'] = {row[0]: row[1] for row in result}
            
            # Count by status
            result = util.regular_select(
                f"SELECT status, COUNT(*) FROM {self.table_name} "
                f"WHERE status IS NOT NULL GROUP BY status"
            )
            stats['by_status'] = {row[0]: row[1] for row in result}
            
            return stats
            
        except Exception as e:
            self.logger.warning(f"Error getting stats: {e}")
            return {}


class DatabaseError(Exception):
    """Custom exception for database operation failures."""
    pass


class ConnectionManager:
    """
    Connection pooling and management utilities.
    
    This provides connection management features that can be used
    by DatabaseManager for improved performance.
    """
    
    _connections = {}
    
    @classmethod
    def get_connection(cls, table_name: str):
        """Get or create a connection for a table."""
        if table_name not in cls._connections:
            cls._connections[table_name] = util.db_connect()
        return cls._connections[table_name]
    
    @classmethod
    def close_all(cls):
        """Close all managed connections."""
        for conn in cls._connections.values():
            try:
                conn.close()
            except:
                pass
        cls._connections.clear()