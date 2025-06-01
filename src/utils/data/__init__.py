"""
Data processing utilities for open-source-legislation.

This module provides standardized data processing utilities including:
- Node factory patterns for consistent Node creation
- Data validation and compliance checking
- Enhanced Pydantic model utilities

Key components:
- NodeFactory: Standardized Node creation with consistent patterns
- NodeBuilder: Fluent interface for complex Node construction
- Data validation utilities (future implementation)
"""

from .factories import NodeFactory, NodeBuilder

__all__ = [
    'NodeFactory',
    'NodeBuilder'
]