"""
Configuration settings for the AI Hedge Fund Simulator.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Alpaca API settings
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"  # Paper trading URL
ALPACA_DATA_URL = "https://data.alpaca.markets"

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/hedgefund.db")

# Trading parameters
INITIAL_CAPITAL = 500000  # $500k starting capital
MAX_POSITION_SIZE = 0.05    # Maximum 5% of portfolio in a single position
RISK_FREE_RATE = 0.03       # 3% risk-free rate for calculations
MARKET_HOURS = {
    "open": "09:30",
    "close": "16:00",
    "timezone": "America/New_York"
}

# AI analysts configuration
AI_ANALYSTS = [
    {
        "name": "Value Investor",
        "model": "gpt-4-turbo",
        "temperature": 0.7,
        "specialty": "Finding undervalued companies with strong fundamentals",
        "timeframe": "long_term"
    },
    {
        "name": "Growth Hunter",
        "model": "gpt-4-turbo",
        "temperature": 0.8,
        "specialty": "Identifying high-growth potential companies",
        "timeframe": "medium_term"
    },
    {
        "name": "Technical Analyst",
        "model": "gpt-4-turbo",
        "temperature": 0.6,
        "specialty": "Analyzing price charts and technical indicators",
        "timeframe": "short_term"
    },
    {
        "name": "Sentiment Analyzer",
        "model": "gpt-4-turbo",
        "temperature": 0.8,
        "specialty": "Monitoring news, social media, and market sentiment",
        "timeframe": "short_term"
    },
    {
        "name": "Sector Specialist",
        "model": "gpt-4-turbo",
        "temperature": 0.7,
        "specialty": "Focusing on specific industry sectors",
        "timeframe": "medium_term"
    },
    {
        "name": "Macro Economist",
        "model": "gpt-4-turbo",
        "temperature": 0.6,
        "specialty": "Analyzing broader economic trends",
        "timeframe": "long_term"
    },
    {
        "name": "Risk Manager",
        "model": "gpt-4-turbo",
        "temperature": 0.5,
        "specialty": "Identifying and mitigating investment risks",
        "timeframe": "medium_term"
    },
    {
        "name": "Momentum Trader",
        "model": "gpt-4-turbo",
        "temperature": 0.8,
        "specialty": "Following market momentum and trends",
        "timeframe": "short_term"
    }
]

# Fund manager configuration
FUND_MANAGER = {
    "name": "Bill Ackman",
    "model": "gpt-4-turbo",
    "temperature": 0.5,
    "style": "Value-oriented activist investor with a focus on long-term value creation"
}

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.path.join(BASE_DIR, "hedgefund.log")

# Reporting configuration
REPORTING = {
    "save_dir": os.path.join(BASE_DIR, "reports"),
    "daily_report": True,
    "weekly_report": True,
    "monthly_report": True
}

# Dashboard configuration
DASHBOARD_PORT = 8050
DASHBOARD_HOST = "0.0.0.0" 