"""
Market data module for fetching stock prices and other market information.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

import pandas as pd
import numpy as np
import yfinance as yf
from alpaca_trade_api import REST as AlpacaREST
from alpha_vantage.timeseries import TimeSeries

from hedgefund.config import (
    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL,
    ALPHA_VANTAGE_API_KEY
)

logger = logging.getLogger(__name__)


class MarketData:
    """Class for fetching and managing market data."""

    def __init__(self):
        """Initialize the market data service."""
        self.alpaca = AlpacaREST(
            key_id=ALPACA_API_KEY,
            secret_key=ALPACA_SECRET_KEY,
            base_url=ALPACA_BASE_URL
        )
        self.alpha_vantage = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        self._cached_data = {}  # Simple in-memory cache

    def get_current_price(self, symbol: str) -> float:
        """
        Get the current market price for a symbol.
        
        Args:
            symbol: The stock symbol.
            
        Returns:
            The current price.
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if data.empty:
                raise ValueError(f"No data found for symbol {symbol}")
            return data['Close'].iloc[-1]
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            # Fallback to Alpaca
            try:
                price = self.alpaca.get_latest_trade(symbol).price
                return float(price)
            except Exception as e:
                logger.error(f"Error fetching price from Alpaca for {symbol}: {e}")
                raise

    def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1y", 
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical price data for a symbol.
        
        Args:
            symbol: The stock symbol.
            period: The time period to fetch (e.g., "1d", "5d", "1mo", "3mo", "1y").
            interval: The data interval (e.g., "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo").
            
        Returns:
            A pandas DataFrame with the historical data.
        """
        cache_key = f"{symbol}_{period}_{interval}"
        if cache_key in self._cached_data:
            # Only use cached data if it's less than 1 hour old
            cached_time, cached_data = self._cached_data[cache_key]
            if datetime.now() - cached_time < timedelta(hours=1):
                return cached_data
            
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                raise ValueError(f"No historical data found for symbol {symbol}")
                
            # Cache the data
            self._cached_data[cache_key] = (datetime.now(), data)
            return data
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            raise

    def get_company_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get company information for a symbol.
        
        Args:
            symbol: The stock symbol.
            
        Returns:
            A dictionary with company information.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Filter out the most important information
            filtered_info = {
                'symbol': symbol,
                'name': info.get('shortName', 'N/A'),
                'sector': info.get('sector', 'N/A'),
                'industry': info.get('industry', 'N/A'),
                'market_cap': info.get('marketCap', 'N/A'),
                'pe_ratio': info.get('trailingPE', 'N/A'),
                'dividend_yield': info.get('dividendYield', 'N/A'),
                'beta': info.get('beta', 'N/A'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 'N/A'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 'N/A'),
                'description': info.get('longBusinessSummary', 'N/A')
            }
            return filtered_info
        except Exception as e:
            logger.error(f"Error fetching company info for {symbol}: {e}")
            raise

    def get_market_news(self, symbols: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """
        Get market news for specified symbols or general market news.
        
        Args:
            symbols: Optional list of stock symbols. If None, returns general market news.
            
        Returns:
            A list of news items.
        """
        try:
            # If symbols provided, get specific news
            if symbols:
                all_news = []
                for symbol in symbols:
                    ticker = yf.Ticker(symbol)
                    news = ticker.news
                    for item in news:
                        item['symbol'] = symbol
                    all_news.extend(news)
                return all_news
            
            # Otherwise get general market news using a market ETF like SPY
            ticker = yf.Ticker("SPY")
            return ticker.news
        except Exception as e:
            logger.error(f"Error fetching market news: {e}")
            return []

    def get_portfolio_value(self, positions: List[Dict[str, Union[str, int, float]]]) -> Dict[str, float]:
        """
        Calculate the current value of a portfolio.
        
        Args:
            positions: A list of position dictionaries, each with 'symbol' and 'quantity' keys.
            
        Returns:
            A dictionary with 'total_value' and other portfolio metrics.
        """
        total_value = 0.0
        position_values = []
        
        for position in positions:
            symbol = position['symbol']
            quantity = position['quantity']
            
            current_price = self.get_current_price(symbol)
            position_value = current_price * quantity
            total_value += position_value
            
            position_values.append({
                'symbol': symbol,
                'quantity': quantity,
                'current_price': current_price,
                'value': position_value
            })
        
        return {
            'total_value': total_value,
            'positions': position_values,
            'timestamp': datetime.now().isoformat()
        }

    def get_technical_indicators(self, symbol: str, period: str = "1y") -> Dict[str, float]:
        """
        Calculate technical indicators for a symbol.
        
        Args:
            symbol: The stock symbol.
            period: The time period for calculation.
            
        Returns:
            A dictionary with various technical indicators.
        """
        data = self.get_historical_data(symbol, period=period)
        
        # Skip calculation if not enough data
        if len(data) < 50:
            return {"error": "Not enough data for technical analysis"}
        
        # Calculate indicators
        close_prices = data['Close']
        
        # Simple Moving Averages
        sma_20 = close_prices.rolling(window=20).mean().iloc[-1]
        sma_50 = close_prices.rolling(window=50).mean().iloc[-1]
        sma_200 = close_prices.rolling(window=200).mean().iloc[-1] if len(close_prices) >= 200 else None
        
        # Exponential Moving Averages
        ema_12 = close_prices.ewm(span=12, adjust=False).mean().iloc[-1]
        ema_26 = close_prices.ewm(span=26, adjust=False).mean().iloc[-1]
        
        # MACD
        macd = ema_12 - ema_26
        macd_signal = pd.Series(macd).ewm(span=9, adjust=False).mean().iloc[-1]
        
        # RSI (14-period)
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Bollinger Bands
        sma_20 = close_prices.rolling(window=20).mean()
        std_20 = close_prices.rolling(window=20).std()
        upper_band = (sma_20 + (std_20 * 2)).iloc[-1]
        lower_band = (sma_20 - (std_20 * 2)).iloc[-1]
        
        current_price = close_prices.iloc[-1]
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'sma_200': sma_200,
            'ema_12': ema_12,
            'ema_26': ema_26,
            'macd': macd,
            'macd_signal': macd_signal,
            'rsi': rsi,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'timestamp': datetime.now().isoformat()
        }

    def is_market_open(self) -> bool:
        """
        Check if the U.S. stock market is currently open.
        
        Returns:
            True if the market is open, False otherwise.
        """
        try:
            return self.alpaca.get_clock().is_open
        except Exception as e:
            logger.error(f"Error checking if market is open: {e}")
            
            # Fallback method using datetime
            now = datetime.now()
            
            # Check if it's a weekday
            if now.weekday() >= 5:  # 5=Saturday, 6=Sunday
                return False
            
            # Check if it's between 9:30 AM and 4:00 PM Eastern Time
            # This is a crude check that doesn't account for holidays
            market_open = now.replace(hour=9, minute=30, second=0)
            market_close = now.replace(hour=16, minute=0, second=0)
            
            return market_open <= now <= market_close 