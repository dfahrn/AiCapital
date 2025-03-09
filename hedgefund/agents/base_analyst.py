"""
Base class for AI analyst agents.
"""
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

import openai
from sqlalchemy.orm import Session

from hedgefund.config import OPENAI_API_KEY
from hedgefund.models import Analyst, Recommendation, TimeframeEnum, OrderSideEnum
from hedgefund.data import MarketData

# Configure logging
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = OPENAI_API_KEY


class BaseAnalyst(ABC):
    """Base class for AI analyst agents."""
    
    def __init__(
        self,
        name: str,
        specialty: str,
        timeframe: str,
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        """
        Initialize the AI analyst.
        
        Args:
            name: The name of the analyst.
            specialty: The analyst's area of expertise.
            timeframe: The analyst's preferred investment timeframe.
            model: The OpenAI model to use.
            temperature: The temperature for the AI response (creativity level).
            db: Optional database session.
            market_data: Optional market data service.
        """
        self.name = name
        self.specialty = specialty
        self.timeframe = timeframe
        self.model = model
        self.temperature = temperature
        self.db = db
        self.market_data = market_data or MarketData()
        
        # Create or get analyst record in the database
        if db:
            self._init_db_record()
    
    def _init_db_record(self):
        """Create or retrieve the analyst record in the database."""
        existing_analyst = self.db.query(Analyst).filter_by(name=self.name).first()
        
        if existing_analyst:
            self.db_record = existing_analyst
        else:
            timeframe_enum = TimeframeEnum[self.timeframe.upper()] if isinstance(self.timeframe, str) else self.timeframe
            new_analyst = Analyst(
                name=self.name,
                specialty=self.specialty,
                timeframe=timeframe_enum,
                description=f"AI analyst specializing in {self.specialty}"
            )
            self.db.add(new_analyst)
            self.db.commit()
            self.db.refresh(new_analyst)
            self.db_record = new_analyst
    
    def _format_system_prompt(self) -> str:
        """
        Format the system prompt for the AI.
        
        Returns:
            The system prompt string.
        """
        return f"""You are {self.name}, an AI financial analyst for a hedge fund, specializing in {self.specialty}. 
Your job is to analyze stocks and provide investment recommendations.

When making recommendations:
1. Focus on your specialty: {self.specialty}
2. Consider the current market conditions
3. Provide clear reasoning for your recommendation
4. Be objective and data-driven
5. Indicate your confidence level in your recommendation (0.0-1.0)
6. Recommend a specific action (BUY or SELL), target price, and stop-loss level
7. Focus on {self.timeframe} investment opportunities

Format your response as a JSON object with the following fields:
- symbol: The stock ticker symbol
- action: "BUY" or "SELL"
- confidence: A value between 0.0 and 1.0 
- target_price: Your price target
- stop_loss: Recommended stop loss price
- reasoning: Detailed explanation for your recommendation
- quantity: Suggested position size (number of shares)
- timeframe: "{self.timeframe}" (your specialty timeframe)
- data_sources: List of data types you used to make this decision

Only respond with valid JSON. Do not include any other text outside the JSON object."""
    
    def _get_user_prompt(self, symbol: str, context: Dict[str, Any]) -> str:
        """
        Format the user prompt for the AI.
        
        Args:
            symbol: The stock symbol to analyze.
            context: Context information for the analysis.
            
        Returns:
            The formatted user prompt.
        """
        price_data = context.get('price_data', {})
        company_info = context.get('company_info', {})
        technical_indicators = context.get('technical_indicators', {})
        market_news = context.get('market_news', [])
        
        prompt = f"""Please analyze {symbol} and provide an investment recommendation.

Current Information:
- Current Price: ${price_data.get('close', 'N/A')}
- 52-Week High: ${company_info.get('fifty_two_week_high', 'N/A')}
- 52-Week Low: ${company_info.get('fifty_two_week_low', 'N/A')}
- Company: {company_info.get('name', 'N/A')}
- Industry: {company_info.get('industry', 'N/A')}
- Sector: {company_info.get('sector', 'N/A')}
- Market Cap: ${company_info.get('market_cap', 'N/A')}
- P/E Ratio: {company_info.get('pe_ratio', 'N/A')}

Technical Indicators:
- SMA (20-day): {technical_indicators.get('sma_20', 'N/A')}
- SMA (50-day): {technical_indicators.get('sma_50', 'N/A')}
- SMA (200-day): {technical_indicators.get('sma_200', 'N/A')}
- RSI (14-day): {technical_indicators.get('rsi', 'N/A')}
- MACD: {technical_indicators.get('macd', 'N/A')}

Recent News Headlines:
"""
        # Add recent news to the prompt
        for i, news in enumerate(market_news[:5]):
            prompt += f"- {news.get('title', 'N/A')}\n"
        
        prompt += "\nBased on this information and your expertise in {self.specialty}, provide your recommendation."
        return prompt
    
    def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze a stock and generate a recommendation.
        
        Args:
            symbol: The stock symbol to analyze.
            
        Returns:
            A dictionary with the recommendation details.
        """
        # Gather data
        context = self._gather_stock_data(symbol)
        
        # Create prompts
        system_prompt = self._format_system_prompt()
        user_prompt = self._get_user_prompt(symbol, context)
        
        # Get recommendation from OpenAI
        try:
            response = openai.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            recommendation_text = response.choices[0].message.content
            import json
            recommendation_data = json.loads(recommendation_text)
            
            # Save to database if available
            if self.db:
                self._save_recommendation(recommendation_data)
                
            return recommendation_data
            
        except Exception as e:
            logger.error(f"Error getting recommendation from OpenAI: {e}")
            raise
    
    def _gather_stock_data(self, symbol: str) -> Dict[str, Any]:
        """
        Gather data about a stock for analysis.
        
        Args:
            symbol: The stock symbol.
            
        Returns:
            A dictionary with gathered data.
        """
        try:
            # Get price data
            historical_data = self.market_data.get_historical_data(symbol, period="3mo")
            price_data = {
                "close": historical_data['Close'].iloc[-1],
                "open": historical_data['Open'].iloc[-1],
                "high": historical_data['High'].iloc[-1],
                "low": historical_data['Low'].iloc[-1],
                "volume": historical_data['Volume'].iloc[-1]
            }
            
            # Get company info
            company_info = self.market_data.get_company_info(symbol)
            
            # Get technical indicators
            technical_indicators = self.market_data.get_technical_indicators(symbol)
            
            # Get news
            market_news = self.market_data.get_market_news([symbol])
            
            return {
                "price_data": price_data,
                "company_info": company_info,
                "technical_indicators": technical_indicators,
                "market_news": market_news
            }
        except Exception as e:
            logger.error(f"Error gathering data for {symbol}: {e}")
            return {}
    
    def _save_recommendation(self, recommendation_data: Dict[str, Any]):
        """
        Save a recommendation to the database.
        
        Args:
            recommendation_data: The recommendation data to save.
        """
        try:
            # Parse timeframe
            timeframe_str = recommendation_data.get('timeframe', self.timeframe).upper()
            timeframe = TimeframeEnum[timeframe_str] if isinstance(timeframe_str, str) else timeframe_str
            
            # Parse action
            action = recommendation_data.get('action', 'BUY').upper()
            side = OrderSideEnum.BUY if action == 'BUY' else OrderSideEnum.SELL
            
            # Create recommendation
            recommendation = Recommendation(
                analyst_id=self.db_record.id,
                symbol=recommendation_data.get('symbol'),
                side=side,
                target_price=recommendation_data.get('target_price'),
                stop_loss=recommendation_data.get('stop_loss'),
                quantity=recommendation_data.get('quantity'),
                timeframe=timeframe,
                confidence=recommendation_data.get('confidence', 0.5),
                reasoning=recommendation_data.get('reasoning', ''),
                data_sources=recommendation_data.get('data_sources', [])
            )
            
            self.db.add(recommendation)
            self.db.commit()
            logger.info(f"Saved recommendation for {recommendation_data.get('symbol')} from {self.name}")
            
        except Exception as e:
            logger.error(f"Error saving recommendation to database: {e}")
            self.db.rollback()
    
    @abstractmethod
    def get_investment_ideas(self) -> List[str]:
        """
        Generate investment ideas (stock symbols to analyze).
        
        Returns:
            A list of stock symbols to analyze.
        """
        pass 