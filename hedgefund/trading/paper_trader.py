"""
Paper trading system for executing trades and tracking portfolio performance.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

import pandas as pd
from sqlalchemy.orm import Session
from alpaca_trade_api import REST as AlpacaREST

from hedgefund.config import (
    ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL,
    INITIAL_CAPITAL, MAX_POSITION_SIZE
)
from hedgefund.models import (
    Order, Position, PortfolioSnapshot, OrderStatusEnum, SessionLocal
)
from hedgefund.data import MarketData
from hedgefund.utils import get_eastern_time

# Configure logging
logger = logging.getLogger(__name__)


class PaperTrader:
    """Paper trading system for simulating trades."""
    
    def __init__(
        self,
        initial_capital: float = INITIAL_CAPITAL,
        max_position_size: float = MAX_POSITION_SIZE,
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        """
        Initialize the paper trading system.
        
        Args:
            initial_capital: The initial capital for the portfolio.
            max_position_size: The maximum position size as a fraction of the portfolio.
            db: Optional database session.
            market_data: Optional market data service.
        """
        self.initial_capital = initial_capital
        self.max_position_size = max_position_size
        self.db = db
        self.market_data = market_data or MarketData()
        self.alpaca = AlpacaREST(
            key_id=ALPACA_API_KEY,
            secret_key=ALPACA_SECRET_KEY,
            base_url=ALPACA_BASE_URL
        )
        
        # Initialize portfolio
        self.cash = initial_capital
        self.positions = {}  # symbol -> Position object
        
        # Load portfolio from database if available
        if db:
            self._load_portfolio()
    
    def _load_portfolio(self):
        """Load the portfolio state from the database."""
        try:
            # Get the cash balance from the latest portfolio snapshot
            latest_snapshot = (
                self.db.query(PortfolioSnapshot)
                .order_by(PortfolioSnapshot.date.desc())
                .first()
            )
            
            if latest_snapshot:
                self.cash = latest_snapshot.cash
            
            # Get current positions
            positions = self.db.query(Position).all()
            for position in positions:
                self.positions[position.symbol] = position
                
            logger.info(f"Loaded portfolio from database: {len(self.positions)} positions, ${self.cash:,.2f} cash")
            
        except Exception as e:
            logger.error(f"Error loading portfolio from database: {e}")
            # Start with initial capital if loading fails
            self.cash = self.initial_capital
            self.positions = {}
    
    def get_portfolio_value(self) -> Dict[str, Any]:
        """
        Get the current portfolio value and holdings.
        
        Returns:
            A dictionary with portfolio information.
        """
        try:
            # Update positions with current market prices
            self._update_positions()
            
            # Calculate total value
            positions_value = sum(p.market_value for p in self.positions.values())
            total_value = self.cash + positions_value
            
            # Calculate total P&L
            total_pl = total_value - self.initial_capital
            total_pl_percent = (total_pl / self.initial_capital) * 100 if self.initial_capital > 0 else 0
            
            # Format position data
            positions_data = []
            for symbol, position in self.positions.items():
                positions_data.append({
                    'symbol': symbol,
                    'quantity': position.quantity,
                    'avg_entry_price': position.avg_entry_price,
                    'current_price': position.current_price,
                    'market_value': position.market_value,
                    'cost_basis': position.cost_basis,
                    'unrealized_pl': position.unrealized_pl,
                    'unrealized_pl_percent': position.unrealized_pl_percent
                })
            
            return {
                'cash': self.cash,
                'positions_value': positions_value,
                'equity': total_value,
                'initial_capital': self.initial_capital,
                'total_pl': total_pl,
                'total_pl_percent': total_pl_percent,
                'positions': positions_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
            return {
                'cash': self.cash,
                'positions_value': 0,
                'equity': self.cash,
                'initial_capital': self.initial_capital,
                'total_pl': self.cash - self.initial_capital,
                'total_pl_percent': ((self.cash - self.initial_capital) / self.initial_capital) * 100,
                'positions': [],
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _update_positions(self):
        """Update positions with current market prices."""
        for symbol, position in list(self.positions.items()):
            try:
                # Get current price
                current_price = self.market_data.get_current_price(symbol)
                
                # Update position
                position.current_price = current_price
                position.market_value = position.quantity * current_price
                position.unrealized_pl = position.market_value - position.cost_basis
                position.unrealized_pl_percent = (position.unrealized_pl / position.cost_basis) * 100 if position.cost_basis > 0 else 0
                position.updated_at = datetime.now()
                
                # Save to database if available
                if self.db:
                    self.db.add(position)
                    
            except Exception as e:
                logger.error(f"Error updating position for {symbol}: {e}")
        
        # Commit changes to database
        if self.db:
            try:
                self.db.commit()
            except Exception as e:
                logger.error(f"Error committing position updates to database: {e}")
                self.db.rollback()
    
    def execute_order(self, order: Union[Order, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a paper trade order.
        
        Args:
            order: The order to execute (either an Order object or a dictionary).
            
        Returns:
            A dictionary with the execution results.
        """
        try:
            # Convert dictionary to Order-like object if needed
            if isinstance(order, dict):
                class DictOrder:
                    pass
                
                dict_order = DictOrder()
                for key, value in order.items():
                    setattr(dict_order, key, value)
                order = dict_order
            
            # Get order details
            symbol = order.symbol
            side = order.side.value if hasattr(order.side, 'value') else order.side
            quantity = order.quantity
            
            # Get current price
            current_price = self.market_data.get_current_price(symbol)
            
            # Check if we can afford the trade
            if side.lower() == 'buy':
                cost = current_price * quantity
                if cost > self.cash:
                    return {
                        'success': False,
                        'message': f"Insufficient cash: ${self.cash:,.2f} available, ${cost:,.2f} required",
                        'symbol': symbol,
                        'side': side,
                        'quantity': quantity,
                        'price': current_price
                    }
            
            # Check position size limit
            portfolio_value = self.cash + sum(p.market_value for p in self.positions.values())
            trade_value = current_price * quantity
            trade_percent = trade_value / portfolio_value if portfolio_value > 0 else 0
            
            if side.lower() == 'buy' and trade_percent > self.max_position_size:
                return {
                    'success': False,
                    'message': f"Trade exceeds max position size ({trade_percent:.2%} > {self.max_position_size:.2%})",
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'price': current_price
                }
            
            # Execute the trade
            if side.lower() == 'buy':
                # Deduct cash
                self.cash -= current_price * quantity
                
                # Update position
                if symbol in self.positions:
                    # Add to existing position
                    position = self.positions[symbol]
                    
                    # Calculate new average price
                    total_quantity = position.quantity + quantity
                    new_cost = (position.avg_entry_price * position.quantity) + (current_price * quantity)
                    new_avg_price = new_cost / total_quantity
                    
                    # Update position
                    position.quantity = total_quantity
                    position.avg_entry_price = new_avg_price
                    position.cost_basis = new_cost
                    position.current_price = current_price
                    position.market_value = total_quantity * current_price
                    position.unrealized_pl = position.market_value - position.cost_basis
                    position.unrealized_pl_percent = (position.unrealized_pl / position.cost_basis) * 100 if position.cost_basis > 0 else 0
                    position.updated_at = datetime.now()
                else:
                    # Create new position
                    position = Position(
                        symbol=symbol,
                        quantity=quantity,
                        avg_entry_price=current_price,
                        current_price=current_price,
                        market_value=quantity * current_price,
                        cost_basis=quantity * current_price,
                        unrealized_pl=0.0,
                        unrealized_pl_percent=0.0
                    )
                    self.positions[symbol] = position
            
            elif side.lower() == 'sell':
                # Check if we have the position
                if symbol not in self.positions:
                    return {
                        'success': False,
                        'message': f"Cannot sell {symbol}: position does not exist",
                        'symbol': symbol,
                        'side': side,
                        'quantity': quantity,
                        'price': current_price
                    }
                
                position = self.positions[symbol]
                
                # Check if we have enough shares
                if position.quantity < quantity:
                    return {
                        'success': False,
                        'message': f"Cannot sell {quantity} shares of {symbol}: only {position.quantity} owned",
                        'symbol': symbol,
                        'side': side,
                        'quantity': quantity,
                        'price': current_price
                    }
                
                # Calculate profit/loss
                trade_pl = (current_price - position.avg_entry_price) * quantity
                
                # Add cash
                self.cash += current_price * quantity
                
                # Update position
                if position.quantity == quantity:
                    # Close position
                    del self.positions[symbol]
                else:
                    # Reduce position
                    position.quantity -= quantity
                    position.market_value = position.quantity * current_price
                    position.cost_basis = position.quantity * position.avg_entry_price
                    position.unrealized_pl = position.market_value - position.cost_basis
                    position.unrealized_pl_percent = (position.unrealized_pl / position.cost_basis) * 100 if position.cost_basis > 0 else 0
                    position.updated_at = datetime.now()
            
            # Save to database if available
            if self.db:
                try:
                    # Update order status
                    if hasattr(order, 'id'):
                        db_order = self.db.query(Order).filter_by(id=order.id).first()
                        if db_order:
                            db_order.status = OrderStatusEnum.FILLED
                            db_order.filled_quantity = quantity
                            db_order.filled_avg_price = current_price
                            db_order.updated_at = datetime.now()
                    
                    # Save position changes
                    if symbol in self.positions:
                        self.db.add(self.positions[symbol])
                    
                    self.db.commit()
                    
                except Exception as e:
                    logger.error(f"Error saving trade to database: {e}")
                    self.db.rollback()
            
            return {
                'success': True,
                'message': f"Executed {side} {quantity} shares of {symbol} at ${current_price:,.2f}",
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': current_price,
                'value': quantity * current_price,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing order: {e}")
            return {
                'success': False,
                'message': f"Error executing order: {str(e)}",
                'symbol': getattr(order, 'symbol', 'unknown'),
                'side': getattr(order, 'side', 'unknown'),
                'quantity': getattr(order, 'quantity', 0)
            }
    
    def process_pending_orders(self) -> List[Dict[str, Any]]:
        """
        Process all pending orders in the database.
        
        Returns:
            A list of execution results.
        """
        if not self.db:
            logger.error("Cannot process pending orders without a database connection")
            return []
        
        # Get pending orders
        pending_orders = (
            self.db.query(Order)
            .filter(Order.status == OrderStatusEnum.NEW)
            .all()
        )
        
        results = []
        for order in pending_orders:
            result = self.execute_order(order)
            results.append(result)
            
        return results
    
    def take_portfolio_snapshot(self) -> Dict[str, Any]:
        """
        Take a snapshot of the current portfolio and save it to the database.
        
        Returns:
            A dictionary with the snapshot data.
        """
        # Get current portfolio value
        portfolio = self.get_portfolio_value()
        
        # Create snapshot object
        snapshot = PortfolioSnapshot(
            date=get_eastern_time(),
            cash=portfolio["cash"],
            equity=portfolio["equity"],
            total_positions_value=portfolio["positions_value"],
            total_pl=portfolio["total_pl"],
            total_pl_percent=portfolio["total_pl_percent"],
            positions_data=portfolio["positions"]
        )
        
        # Save to database
        db = SessionLocal()
        try:
            db.add(snapshot)
            db.commit()
        except Exception as e:
            db.rollback()
            logging.error(f"Error saving portfolio snapshot: {e}")
        finally:
            db.close()
        
        return portfolio 