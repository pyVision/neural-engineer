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
    env_vars = {
        # Redis configuration
        "REDIS_HOST": os.environ.get("REDIS_HOST", "localhost"),
        "REDIS_PORT": os.environ.get("REDIS_PORT", "6379"),
        "REDIS_PASSWORD": os.environ.get("REDIS_PASSWORD", ""),
        
        # SMTP configuration for email notifications
        "SMTP_SERVER": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "SMTP_PORT": os.environ.get("SMTP_PORT", "587"),
        "SMTP_USERNAME": os.environ.get("SMTP_USERNAME", ""),
        "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD", ""),
        "FROM_EMAIL": os.environ.get("FROM_EMAIL", "domaincheck@example.com"),
        
        # Application configuration
        "NOTIFICATION_THRESHOLD_DAYS": os.environ.get("NOTIFICATION_THRESHOLD_DAYS", "30"),
        "MAX_DOMAINS_PER_CHECK": os.environ.get("MAX_DOMAINS_PER_CHECK", "5"),
        "APP_HOST": os.environ.get("APP_HOST", "0.0.0.0"),
        "APP_PORT": os.environ.get("APP_PORT", "8000"),
        "DEBUG": os.environ.get("DEBUG", "False"),
        
        # # GCP specific settings for Memorystore
        # "GCP_PROJECT": os.environ.get("GCP_PROJECT", ""),
        # "GCP_REGION": os.environ.get("GCP_REGION", ""),
        # "MEMORYSTORE_INSTANCE_ID": os.environ.get("MEMORYSTORE_INSTANCE_ID", ""),
    }
    
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