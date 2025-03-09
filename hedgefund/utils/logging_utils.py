"""
Logging utilities for the AI Hedge Fund Simulator.
"""
import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from hedgefund.config import LOG_LEVEL, LOG_FILE


def setup_logging(log_level: str = LOG_LEVEL, log_file: str = LOG_FILE) -> logging.Logger:
    """
    Set up logging for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: The path to the log file.
        
    Returns:
        The configured logger.
    """
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Clean log_level if it contains comments
    if log_level and '#' in log_level:
        log_level = log_level.split('#')[0].strip()
    
    # Get the numeric logging level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    return logger


def log_performance(logger, portfolio_data: dict):
    """
    Log portfolio performance information.
    
    Args:
        logger: The logger to use.
        portfolio_data: Dictionary with portfolio information.
    """
    try:
        logger.info(f"Portfolio Performance ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        logger.info(f"Cash: ${portfolio_data.get('cash', 0):,.2f}")
        logger.info(f"Positions Value: ${portfolio_data.get('positions_value', 0):,.2f}")
        logger.info(f"Total Equity: ${portfolio_data.get('equity', 0):,.2f}")
        logger.info(f"P&L: ${portfolio_data.get('total_pl', 0):,.2f} ({portfolio_data.get('total_pl_percent', 0):.2f}%)")
        
        positions = portfolio_data.get('positions', [])
        if positions:
            logger.info(f"Current Positions ({len(positions)}):")
            for position in positions:
                logger.info(
                    f"  {position.get('symbol')}: {position.get('quantity')} shares @ ${position.get('avg_entry_price', 0):,.2f} "
                    f"(Current: ${position.get('current_price', 0):,.2f}, P&L: ${position.get('unrealized_pl', 0):,.2f}, "
                    f"{position.get('unrealized_pl_percent', 0):.2f}%)"
                )
        else:
            logger.info("No current positions")
            
    except Exception as e:
        logger.error(f"Error logging performance: {e}") 