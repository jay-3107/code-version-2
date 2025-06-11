# logging_config.py - Logging configuration for the application

import logging
import sys
from datetime import datetime
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

def setup_logger(name='abdm_integration'):
    """Set up a logger with consistent formatting and handlers"""
    logger = logging.getLogger(name)
    
    # Only configure if not already set up
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        
        # File handler - rotated daily
        log_filename = f"logs/abdm_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        
        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger