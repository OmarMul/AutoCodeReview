import logging
import logging.config
import yaml
from pathlib import Path
import os

# ==========================================
# Setup Logging
# ==========================================

def setup_logging():
    """Setup logging configuration from YAML file"""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Load logging configuration
    config_path = Path("Config/logging.yaml")
    
    if not config_path.exists():
        # Fallback to basic logging if config file doesn't exist
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.warning(f"Logging config file not found at {config_path}. Using basic configuration.")
        return
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        logging.config.dictConfig(config)
        logging.info("Logging configured successfully from YAML file")
    except Exception as e:
        # Fallback to basic logging if config loading fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.error(f"Failed to load logging configuration: {e}. Using basic configuration.")


def get_logger(name: str):
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)
