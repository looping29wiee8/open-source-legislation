"""
Secure credential management for open-source-legislation scrapers.

This module provides secure credential management to replace hardcoded credentials
found throughout the codebase. All database credentials should be managed through
environment variables.
"""

import os
from typing import Optional, Dict


class CredentialManager:
    """Secure credential management for database connections and API access."""
    
    @staticmethod
    def get_database_user() -> str:
        """
        Get database user from environment variables.
        
        Returns:
            str: Database username
            
        Raises:
            ValueError: If OSL_DB_USER environment variable is not set
        """
        user = os.getenv('OSL_DB_USER')
        if user is None:
            raise ValueError(
                "OSL_DB_USER environment variable not set. "
                "Please set it to your database username."
            )
        return user
        
    @staticmethod
    def get_database_config() -> Dict[str, str]:
        """
        Get complete database configuration from environment variables.
        
        Returns:
            Dict[str, str]: Dictionary containing database configuration
            
        Raises:
            ValueError: If any required environment variable is not set
        """
        required_vars = ['OSL_DB_USER', 'OSL_DB_PASSWORD', 'OSL_DB_HOST', 'OSL_DB_NAME']
        config = {}
        
        for var in required_vars:
            value = os.getenv(var)
            if value is None:
                raise ValueError(f"Required environment variable {var} not set")
            # Allow empty passwords for databases with no authentication
            config[var.lower().replace('osl_db_', '')] = value
            
        return config
    
    @staticmethod
    def get_api_key(service: str) -> str:
        """
        Get API key for specified service.
        
        Args:
            service: Service name (e.g., 'openai', 'anthropic')
            
        Returns:
            str: API key
            
        Raises:
            ValueError: If API key environment variable is not set
        """
        env_var = f'OSL_{service.upper()}_API_KEY'
        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(
                f"{env_var} environment variable not set. "
                f"Please set it to your {service} API key."
            )
        return api_key
    
    @staticmethod
    def validate_environment() -> Dict[str, bool]:
        """
        Validate that all required environment variables are set.
        
        Returns:
            Dict[str, bool]: Status of each required environment variable
        """
        required_vars = [
            'OSL_DB_USER', 'OSL_DB_PASSWORD', 'OSL_DB_HOST', 'OSL_DB_NAME',
            'OSL_OPENAI_API_KEY'  # Common API key
        ]
        
        status = {}
        for var in required_vars:
            status[var] = os.getenv(var) is not None
            
        return status