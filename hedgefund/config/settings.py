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

# ---------------------------------------------------------------------------
# LLM provider configuration
#
# The agents talk to any OpenAI-compatible chat-completions endpoint, so a free
# provider can be used by pointing LLM_BASE_URL / LLM_API_KEY / LLM_MODEL at it.
# Defaults target Groq's free tier, which is generous enough for a full cycle.
#
#   Gemini     https://generativelanguage.googleapis.com/v1beta/openai/
#   Groq       https://api.groq.com/openai/v1
#   OpenRouter https://openrouter.ai/api/v1
#   Ollama     http://localhost:11434/v1
#   OpenAI     https://api.openai.com/v1
# ---------------------------------------------------------------------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")

# Falls back to OPENAI_API_KEY so existing .env files keep working.
LLM_API_KEY = os.getenv("LLM_API_KEY") or OPENAI_API_KEY

# Default model for every analyst and the fund manager.
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

# Some free/local models do not implement OpenAI's JSON mode
# (response_format={"type": "json_object"}). Set LLM_JSON_MODE=false to fall
# back to prompt-instructed JSON with lenient parsing.
LLM_JSON_MODE = os.getenv("LLM_JSON_MODE", "true").lower() not in ("false", "0", "no")

# Retries for transient failures (rate limits are common on free tiers).
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

# Seconds to pause between agent calls, to stay under free-tier rate limits.
LLM_REQUEST_DELAY = float(os.getenv("LLM_REQUEST_DELAY", "0"))

# Symbols each analyst researches per cycle. This is the main driver of how many
# LLM calls a full cycle makes: 8 analysts x (1 idea call + this many analyses).
# At the default 5 that is 48 calls, which exceeds most free daily quotas.
SYMBOLS_PER_ANALYST = int(os.getenv("SYMBOLS_PER_ANALYST", "5"))
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
        "model": LLM_MODEL,
        "temperature": 0.7,
        "specialty": "Finding undervalued companies with strong fundamentals",
        "timeframe": "long_term"
    },
    {
        "name": "Growth Hunter",
        "model": LLM_MODEL,
        "temperature": 0.8,
        "specialty": "Identifying high-growth potential companies",
        "timeframe": "medium_term"
    },
    {
        "name": "Technical Analyst",
        "model": LLM_MODEL,
        "temperature": 0.6,
        "specialty": "Analyzing price charts and technical indicators",
        "timeframe": "short_term"
    },
    {
        "name": "Sentiment Analyzer",
        "model": LLM_MODEL,
        "temperature": 0.8,
        "specialty": "Monitoring news, social media, and market sentiment",
        "timeframe": "short_term"
    },
    {
        "name": "Sector Specialist",
        "model": LLM_MODEL,
        "temperature": 0.7,
        "specialty": "Focusing on specific industry sectors",
        "timeframe": "medium_term"
    },
    {
        "name": "Macro Economist",
        "model": LLM_MODEL,
        "temperature": 0.6,
        "specialty": "Analyzing broader economic trends",
        "timeframe": "long_term"
    },
    {
        "name": "Risk Manager",
        "model": LLM_MODEL,
        "temperature": 0.5,
        "specialty": "Identifying and mitigating investment risks",
        "timeframe": "medium_term"
    },
    {
        "name": "Momentum Trader",
        "model": LLM_MODEL,
        "temperature": 0.8,
        "specialty": "Following market momentum and trends",
        "timeframe": "short_term"
    }
]

# Fund manager configuration
FUND_MANAGER = {
    "name": "Bill Ackman",
    "model": LLM_MODEL,
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