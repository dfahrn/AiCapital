"""
Implementation of specific AI analyst types.
"""
import logging
import random
from typing import Dict, Any, List, Optional

import openai
from sqlalchemy.orm import Session

from hedgefund.config import OPENAI_API_KEY
from hedgefund.data import MarketData
from .base_analyst import BaseAnalyst

# Configure logging
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = OPENAI_API_KEY


class ValueInvestor(BaseAnalyst):
    """Value investor AI analyst."""
    
    def __init__(
        self,
        name: str = "Value Investor",
        specialty: str = "Finding undervalued companies with strong fundamentals",
        timeframe: str = "LONG_TERM",
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        super().__init__(name, specialty, timeframe, model, temperature, db, market_data)
    
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas focused on value stocks.
        
        Returns:
            A list of stock symbols to analyze.
        """
        # Start with a list of common value stocks to analyze
        value_stocks = ["BRK-B", "JPM", "JNJ", "PG", "KO", "CVX", "VZ", "IBM", "INTC", "WMT", "CVS", "MRK", "PFE", "BAC", "C"]
        
        # Get additional ideas using OpenAI
        try:
            system_prompt = f"""You are {self.name}, a value investor looking for undervalued companies with strong fundamentals.
Your job is to suggest 5 stock tickers (symbols only) that might be undervalued in the current market.
Focus on companies with:
- Low P/E ratios relative to industry
- Strong balance sheets
- Stable cash flows
- Good dividend history
- Competitive advantages
Return just the tickers as a comma-separated list, with no additional text."""

            user_prompt = "Suggest 5 potentially undervalued stocks to analyze based on current market conditions."
            
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse the response
            ai_suggestions = response.choices[0].message.content.strip().split(',')
            ai_suggestions = [s.strip().upper() for s in ai_suggestions if s.strip()]
            
            # Combine with our predefined list and return a subset
            all_ideas = list(set(value_stocks + ai_suggestions))
            return random.sample(all_ideas, min(5, len(all_ideas)))
            
        except Exception as e:
            logger.error(f"Error getting investment ideas: {e}")
            # Fallback to predefined list
            return random.sample(value_stocks, min(5, len(value_stocks)))


class GrowthHunter(BaseAnalyst):
    """Growth-focused AI analyst."""
    
    def __init__(
        self,
        name: str = "Growth Hunter",
        specialty: str = "Identifying high-growth potential companies",
        timeframe: str = "MEDIUM_TERM",
        model: str = "gpt-4-turbo",
        temperature: float = 0.8,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        super().__init__(name, specialty, timeframe, model, temperature, db, market_data)
    
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas focused on growth stocks.
        
        Returns:
            A list of stock symbols to analyze.
        """
        # Start with a list of common growth stocks to analyze
        growth_stocks = ["NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "CRM", "AMD", "ADBE", "SHOP", "SNOW", "NET", "CRWD", "ENPH"]
        
        # Get additional ideas using OpenAI
        try:
            system_prompt = f"""You are {self.name}, a growth-focused investor looking for companies with high growth potential.
Your job is to suggest 5 stock tickers (symbols only) that might have strong growth prospects in the current market.
Focus on companies with:
- Strong revenue growth
- Expanding markets
- Innovative products or services
- Competitive advantages
- Potential for market disruption
Return just the tickers as a comma-separated list, with no additional text."""

            user_prompt = "Suggest 5 potential high-growth stocks to analyze based on current market conditions."
            
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse the response
            ai_suggestions = response.choices[0].message.content.strip().split(',')
            ai_suggestions = [s.strip().upper() for s in ai_suggestions if s.strip()]
            
            # Combine with our predefined list and return a subset
            all_ideas = list(set(growth_stocks + ai_suggestions))
            return random.sample(all_ideas, min(5, len(all_ideas)))
            
        except Exception as e:
            logger.error(f"Error getting investment ideas: {e}")
            # Fallback to predefined list
            return random.sample(growth_stocks, min(5, len(growth_stocks)))


class TechnicalAnalyst(BaseAnalyst):
    """Technical analysis focused AI analyst."""
    
    def __init__(
        self,
        name: str = "Technical Analyst",
        specialty: str = "Analyzing price charts and technical indicators",
        timeframe: str = "SHORT_TERM",
        model: str = "gpt-4-turbo",
        temperature: float = 0.6,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        super().__init__(name, specialty, timeframe, model, temperature, db, market_data)
    
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas based on technical analysis.
        
        Returns:
            A list of stock symbols to analyze.
        """
        # Start with major indices and liquid stocks good for technical analysis
        technical_stocks = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AMD", "NVDA", "BA", "DIS", "JPM", "GS"]
        
        # Get additional ideas using OpenAI
        try:
            system_prompt = f"""You are {self.name}, a technical analyst focusing on chart patterns and indicators.
Your job is to suggest 5 stock tickers (symbols only) that might have interesting technical setups in the current market.
Focus on stocks with:
- Clear chart patterns (e.g., breakouts, support/resistance)
- Volume patterns
- Momentum indicators
- Moving average crossovers
- High liquidity for accurate technical analysis
Return just the tickers as a comma-separated list, with no additional text."""

            user_prompt = "Suggest 5 stocks that might have interesting technical setups to analyze in the current market."
            
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse the response
            ai_suggestions = response.choices[0].message.content.strip().split(',')
            ai_suggestions = [s.strip().upper() for s in ai_suggestions if s.strip()]
            
            # Combine with our predefined list and return a subset
            all_ideas = list(set(technical_stocks + ai_suggestions))
            return random.sample(all_ideas, min(5, len(all_ideas)))
            
        except Exception as e:
            logger.error(f"Error getting investment ideas: {e}")
            # Fallback to predefined list
            return random.sample(technical_stocks, min(5, len(technical_stocks)))


class SentimentAnalyzer(BaseAnalyst):
    """News and sentiment focused AI analyst."""
    
    def __init__(
        self,
        name: str = "Sentiment Analyzer",
        specialty: str = "Monitoring news, social media, and market sentiment",
        timeframe: str = "SHORT_TERM",
        model: str = "gpt-4-turbo",
        temperature: float = 0.8,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        super().__init__(name, specialty, timeframe, model, temperature, db, market_data)
    
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas based on news and sentiment.
        
        Returns:
            A list of stock symbols to analyze.
        """
        # Start with stocks that often have significant news impact
        news_driven_stocks = ["TSLA", "AAPL", "MSFT", "META", "GOOGL", "AMZN", "NFLX", "DIS", "BABA", "TWTR", "COIN", "GME", "AMC", "PLTR", "SPCE"]
        
        # Get market news
        try:
            market_news = self.market_data.get_market_news()
            
            # Use the latest news to identify trending stocks
            system_prompt = f"""You are {self.name}, an analyst focusing on news sentiment and market trends.
Below is recent market news. Based on this information, suggest 5 stock tickers (symbols only) that might be affected by this news.
Focus on stocks with:
- Significant recent news coverage
- Potential sentiment shifts
- Event-driven opportunities
- High social media attention
Return just the tickers as a comma-separated list, with no additional text."""

            # Format the news into the prompt
            news_text = "Recent Market News:\n"
            for i, news in enumerate(market_news[:10]):
                news_text += f"- {news.get('title', 'N/A')}\n"
            
            user_prompt = f"{news_text}\n\nBased on this news, suggest 5 stocks that might be affected by current sentiment and news flow."
            
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse the response
            ai_suggestions = response.choices[0].message.content.strip().split(',')
            ai_suggestions = [s.strip().upper() for s in ai_suggestions if s.strip()]
            
            # Combine with our predefined list and return a subset
            all_ideas = list(set(news_driven_stocks + ai_suggestions))
            return random.sample(all_ideas, min(5, len(all_ideas)))
            
        except Exception as e:
            logger.error(f"Error getting investment ideas: {e}")
            # Fallback to predefined list
            return random.sample(news_driven_stocks, min(5, len(news_driven_stocks)))


class SectorSpecialist(BaseAnalyst):
    """Sector-focused AI analyst."""
    
    def __init__(
        self,
        name: str = "Sector Specialist",
        specialty: str = "Focusing on specific industry sectors",
        timeframe: str = "MEDIUM_TERM",
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
        sector: str = "Technology",
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        self.sector = sector
        specialty = f"Analyzing companies in the {sector} sector"
        super().__init__(name, specialty, timeframe, model, temperature, db, market_data)
    
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas focused on a specific sector.
        
        Returns:
            A list of stock symbols to analyze.
        """
        # Define stocks by sector
        sector_stocks = {
            "Technology": ["AAPL", "MSFT", "NVDA", "AMD", "INTC", "CRM", "ADBE", "CSCO", "ORCL", "IBM", "PYPL", "QCOM", "TXN", "AVGO", "MU"],
            "Healthcare": ["JNJ", "PFE", "MRK", "ABBV", "UNH", "BMY", "LLY", "AMGN", "GILD", "ISRG", "TMO", "MDT", "CVS", "ABT", "BIIB"],
            "Consumer": ["AMZN", "WMT", "HD", "MCD", "SBUX", "NKE", "TGT", "LOW", "COST", "PG", "KO", "PEP", "CL", "EL", "MDLZ"],
            "Financial": ["JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "V", "MA", "BLK", "SCHW", "COF", "USB", "PNC", "TFC"],
            "Energy": ["XOM", "CVX", "COP", "EOG", "SLB", "PXD", "OXY", "MPC", "PSX", "VLO", "KMI", "WMB", "HAL", "DVN", "BP"]
        }
        
        # Get stocks for the chosen sector, default to Technology
        base_stocks = sector_stocks.get(self.sector, sector_stocks["Technology"])
        
        # Get additional ideas using OpenAI
        try:
            system_prompt = f"""You are {self.name}, a sector specialist focusing on the {self.sector} sector.
Your job is to suggest 5 stock tickers (symbols only) within the {self.sector} sector that might be good investment opportunities.
Focus on companies with:
- Strong position within the {self.sector} sector
- Potential catalysts specific to this sector
- Competitive advantages
- Sector-specific growth trends
Return just the tickers as a comma-separated list, with no additional text."""

            user_prompt = f"Suggest 5 promising stocks within the {self.sector} sector based on current market and sector conditions."
            
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse the response
            ai_suggestions = response.choices[0].message.content.strip().split(',')
            ai_suggestions = [s.strip().upper() for s in ai_suggestions if s.strip()]
            
            # Combine with our predefined list and return a subset
            all_ideas = list(set(base_stocks + ai_suggestions))
            return random.sample(all_ideas, min(5, len(all_ideas)))
            
        except Exception as e:
            logger.error(f"Error getting investment ideas: {e}")
            # Fallback to predefined list
            return random.sample(base_stocks, min(5, len(base_stocks)))


class MacroEconomist(BaseAnalyst):
    """Macro-economic focused AI analyst."""
    
    def __init__(
        self,
        name: str = "Macro Economist",
        specialty: str = "Analyzing broader economic trends",
        timeframe: str = "LONG_TERM",
        model: str = "gpt-4-turbo",
        temperature: float = 0.6,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        super().__init__(name, specialty, timeframe, model, temperature, db, market_data)
    
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas based on macroeconomic trends.
        
        Returns:
            A list of stock symbols to analyze.
        """
        # Start with ETFs and stocks sensitive to macro trends
        macro_stocks = ["SPY", "QQQ", "DIA", "IWM", "GLD", "SLV", "USO", "TLT", "XLF", "XLE", "XLI", "XLK", "XLV", "XLP", "XLRE"]
        
        # Get additional ideas using OpenAI
        try:
            system_prompt = f"""You are {self.name}, a macro-economic analyst focusing on broad economic trends.
Your job is to suggest 5 stock or ETF tickers (symbols only) that might benefit from current macroeconomic conditions.
Focus on:
- Interest rate trends
- Inflation/deflation dynamics
- Economic growth projections
- Geopolitical factors
- Sector rotation based on economic cycle
Return just the tickers as a comma-separated list, with no additional text."""

            user_prompt = "Suggest 5 stocks or ETFs that might perform well given current macroeconomic conditions and trends."
            
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse the response
            ai_suggestions = response.choices[0].message.content.strip().split(',')
            ai_suggestions = [s.strip().upper() for s in ai_suggestions if s.strip()]
            
            # Combine with our predefined list and return a subset
            all_ideas = list(set(macro_stocks + ai_suggestions))
            return random.sample(all_ideas, min(5, len(all_ideas)))
            
        except Exception as e:
            logger.error(f"Error getting investment ideas: {e}")
            # Fallback to predefined list
            return random.sample(macro_stocks, min(5, len(macro_stocks)))


class RiskManager(BaseAnalyst):
    """Risk-focused AI analyst."""
    
    def __init__(
        self,
        name: str = "Risk Manager",
        specialty: str = "Identifying and mitigating investment risks",
        timeframe: str = "MEDIUM_TERM",
        model: str = "gpt-4-turbo",
        temperature: float = 0.5,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        super().__init__(name, specialty, timeframe, model, temperature, db, market_data)
    
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas with a focus on risk management.
        
        Returns:
            A list of stock symbols to analyze from a risk perspective.
        """
        # Focus on blue chips, defensive stocks, and volatility indicators
        risk_stocks = ["VIX", "TLT", "GLD", "MCD", "JNJ", "PG", "KO", "XLP", "XLU", "USMV", "SPLV", "SH", "PSQ", "JPST", "MINT"]
        
        # Get additional ideas using OpenAI
        try:
            system_prompt = f"""You are {self.name}, a risk-focused analyst prioritizing downside protection.
Your job is to suggest 5 stock or ETF tickers (symbols only) to analyze from a risk management perspective.
Focus on:
- Potential risks in popular stocks
- Defensive plays
- Hedging opportunities
- Low volatility securities
- Risk-reward asymmetry
Return just the tickers as a comma-separated list, with no additional text."""

            user_prompt = "Suggest 5 stocks or ETFs to analyze from a risk management perspective in the current market."
            
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse the response
            ai_suggestions = response.choices[0].message.content.strip().split(',')
            ai_suggestions = [s.strip().upper() for s in ai_suggestions if s.strip()]
            
            # Combine with our predefined list and return a subset
            all_ideas = list(set(risk_stocks + ai_suggestions))
            return random.sample(all_ideas, min(5, len(all_ideas)))
            
        except Exception as e:
            logger.error(f"Error getting investment ideas: {e}")
            # Fallback to predefined list
            return random.sample(risk_stocks, min(5, len(risk_stocks)))


class MomentumTrader(BaseAnalyst):
    """Momentum-focused AI analyst."""
    
    def __init__(
        self,
        name: str = "Momentum Trader",
        specialty: str = "Following market momentum and trends",
        timeframe: str = "SHORT_TERM",
        model: str = "gpt-4-turbo",
        temperature: float = 0.8,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        super().__init__(name, specialty, timeframe, model, temperature, db, market_data)
    
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas based on market momentum.
        
        Returns:
            A list of stock symbols to analyze.
        """
        # Start with stocks that often exhibit momentum
        momentum_stocks = ["TSLA", "NVDA", "AMD", "SHOP", "PLTR", "SNOW", "NET", "DKNG", "RBLX", "MSTR", "UPST", "CRWD", "RIVN", "SNAP", "SOFI"]
        
        # Get additional ideas using OpenAI
        try:
            system_prompt = f"""You are {self.name}, a momentum-focused trader looking for stocks with strong directional trends.
Your job is to suggest 5 stock tickers (symbols only) that might currently have strong momentum or are setting up for momentum trades.
Focus on stocks with:
- Strong recent price performance
- High relative strength
- Increasing volume patterns
- Breakouts from consolidation
- Sector or thematic momentum
Return just the tickers as a comma-separated list, with no additional text."""

            user_prompt = "Suggest 5 stocks that might currently have strong momentum or are setting up for momentum trades."
            
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse the response
            ai_suggestions = response.choices[0].message.content.strip().split(',')
            ai_suggestions = [s.strip().upper() for s in ai_suggestions if s.strip()]
            
            # Combine with our predefined list and return a subset
            all_ideas = list(set(momentum_stocks + ai_suggestions))
            return random.sample(all_ideas, min(5, len(all_ideas)))
            
        except Exception as e:
            logger.error(f"Error getting investment ideas: {e}")
            # Fallback to predefined list
            return random.sample(momentum_stocks, min(5, len(momentum_stocks))) 