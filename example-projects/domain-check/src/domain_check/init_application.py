#!/usr/bin/env python3
"""
Application Initialization Module

This module loads environment variables from a .env file and initializes
all necessary components for the domain-check application.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='application.log'
)

logger = logging.getLogger(__name__)

def load_environment() -> Dict[str, str]:
    """
    Load environment variables from .env file.
    
    Returns:
        Dict of loaded environment variables
    """
    # Determine the project root directory
    env_path = find_dotenv_path()
    
    # Load environment variables
    loaded = load_dotenv(env_path)
    
    if loaded:
        logger.info(f"Loaded environment variables from {env_path}")
    else:
        logger.warning(f"No .env file found at {env_path}, using default values")
    
    # Return a dictionary of all environment variables used by the application
    # Collect all environment variables
    env_vars = {}
    
    # Define default values for required variables
    defaults = {
        # Redis configuration
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "",
        "REDIS_NAMESPACE": "",
        
        # SMTP configuration for email notifications
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "FROM_EMAIL": "domaincheck@example.com",
        
        # Application configuration
        "NOTIFICATION_THRESHOLD_DAYS": "30",
        "MAX_DOMAINS_PER_CHECK": "5",
        "APP_HOST": "0.0.0.0",
        "APP_PORT": "8000",
        "DEBUG": "False",
    }
    
    # Add all environment variables with defaults when specified
    for key, default in defaults.items():
        env_vars[key] = os.environ.get(key, default)
    
    # # Add any additional environment variables that start with specific prefixes
    # # (useful for capturing all related config without explicitly listing each one)
    # prefixes = ["DOMAIN_", "APP_", "REDIS_", "SMTP_", "GCP_"]
    for key, value in os.environ.items():
        #if any(key.startswith(prefix) for prefix in prefixes) and key not in env_vars:
            env_vars[key] = value
    
    return env_vars

def find_dotenv_path() -> Path:
    """
    Find the .env file by searching up from the current directory.
    
    Returns:
        Path to the .env file
    """
    # Start with the current file's directory
    current_dir = Path(__file__).parent
    
    # Try to find .env by traversing up the directory tree
    max_levels = 5  # Limit the number of levels to search
    for _ in range(max_levels):
        # Try current directory
        env_path = current_dir / '.env'
        if env_path.exists():
            return env_path
        
        # Try parent directory
        current_dir = current_dir.parent
        if current_dir == current_dir.parent:  # At root directory
            break
    
    # If not found, default to the package directory
    return Path(__file__).parent / '.env'

def init_application() -> Dict[str, Any]:
    """
    Initialize the application by loading environment variables
    and setting up required components.
    
    Returns:
        Dict containing initialization results
    """
    # Load environment variables
    env_vars = load_environment()
    
    # Log what we're using (but hide sensitive information)
    logger.info(f"Using Redis host: {env_vars['REDIS_HOST']}")
    logger.info(f"Using SMTP server: {env_vars['SMTP_SERVER']}")
    
    # Set debug mode
    debug_mode = env_vars["DEBUG"].lower() == "true"
    if debug_mode:
        # Set root logger to DEBUG level
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Return initialization results
    return {
        "initialized": True,
        "debug_mode": debug_mode,
        "env_vars": {k:v for k, v in env_vars.items()},
    }

# Run initialization if this module is imported
initialization_result = init_application()
print("Initialization result:", initialization_result)
# Export for use in other modules
__all__ = ['init_application', 'load_environment', 'initialization_result']