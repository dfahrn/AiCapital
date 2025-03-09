"""
Utilities package for the AI Hedge Fund Simulator.
"""

from .logging_utils import setup_logging, log_performance
from datetime import datetime
import pytz

def get_eastern_time():
    """
    Get the current datetime in Eastern Time (ET/NYC).
    
    Returns:
        datetime: The current time in Eastern Time zone
    """
    # Get the current UTC time properly
    utc_now = datetime.utcnow().replace(tzinfo=pytz.UTC)
    
    # Convert to Eastern Time
    eastern = pytz.timezone('America/New_York')
    eastern_time = utc_now.astimezone(eastern)
    
    return eastern_time 