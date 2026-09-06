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
        
        # Initialize portfolio. These are replaced by the live Alpaca account
        # as soon as it can be read; initial_capital is only a fallback.
        self.cash = initial_capital
        self.buying_power = initial_capital
        self.positions = {}  # symbol -> Position object
        
        # Load portfolio from database if available
        if db:
            self._load_portfolio()
    
    def _load_portfolio(self):
        """
        Load the portfolio state.

        Alpaca is the book of record, so prefer the live account and fall back
        to the local mirror only if the broker cannot be reached.
        """
        if self.sync_from_alpaca():
            return

        logger.warning(
            "Falling back to the local portfolio mirror; it may be stale. "
            "Check ALPACA_API_KEY and ALPACA_SECRET_KEY."
        )
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
    
    def sync_from_alpaca(self) -> bool:
        """
        Refresh cash and positions from the Alpaca account.

        Alpaca is the book of record once orders are submitted there, so the
        local tables are a mirror for the dashboard rather than a ledger of
        their own. Returns False if the account could not be read, in which
        case the caller should not trade on stale local numbers.
        """
        try:
            account = self.alpaca.get_account()
            alpaca_positions = self.alpaca.list_positions()
        except Exception as e:
            logger.error(f"Could not read the Alpaca account: {e}")
            return False

        self.cash = float(account.cash)
        self.buying_power = float(account.buying_power)

        # Rebuild local positions to match the broker exactly, so a position
        # closed at Alpaca cannot linger here.
        self.positions = {}
        for p in alpaca_positions:
            quantity = int(float(p.qty))
            avg_price = float(p.avg_entry_price)
            current_price = float(p.current_price or avg_price)

            self.positions[p.symbol] = Position(
                symbol=p.symbol,
                quantity=quantity,
                avg_entry_price=avg_price,
                current_price=current_price,
                market_value=float(p.market_value or quantity * current_price),
                cost_basis=float(p.cost_basis or quantity * avg_price),
                unrealized_pl=float(p.unrealized_pl or 0.0),
                unrealized_pl_percent=float(p.unrealized_plpc or 0.0) * 100,
                updated_at=datetime.now()
            )

        if self.db:
            try:
                # Replace the mirror wholesale; stale rows would otherwise show
                # positions the account no longer holds.
                self.db.query(Position).delete()
                for position in self.positions.values():
                    self.db.add(position)
                self.db.commit()
            except Exception as e:
                logger.error(f"Error mirroring Alpaca positions to the database: {e}")
                self.db.rollback()

        logger.info(
            f"Synced from Alpaca: {len(self.positions)} positions, "
            f"${self.cash:,.2f} cash, ${self.buying_power:,.2f} buying power"
        )
        return True

    def reconcile_orders(self) -> List[Dict[str, Any]]:
        """
        Bring previously submitted orders up to date with the broker.

        Market orders placed outside trading hours queue until the open, so a
        submitted order is checked on later cycles rather than assumed filled.
        """
        if not self.db:
            return []

        pending = (
            self.db.query(Order)
            .filter(Order.status == OrderStatusEnum.SUBMITTED)
            .filter(Order.external_id.isnot(None))
            .all()
        )

        if not pending:
            return []

        # Alpaca's vocabulary for where an order ended up.
        terminal = {
            "filled": OrderStatusEnum.FILLED,
            "partially_filled": OrderStatusEnum.PARTIALLY_FILLED,
            "canceled": OrderStatusEnum.CANCELED,
            "cancelled": OrderStatusEnum.CANCELED,
            "expired": OrderStatusEnum.EXPIRED,
            "rejected": OrderStatusEnum.REJECTED,
            "done_for_day": OrderStatusEnum.EXPIRED,
        }

        results = []
        for order in pending:
            try:
                broker_order = self.alpaca.get_order(order.external_id)
            except Exception as e:
                logger.error(f"Could not read Alpaca order {order.external_id}: {e}")
                continue

            state = (broker_order.status or "").lower()
            if state not in terminal:
                continue  # Still working; check again next cycle.

            order.status = terminal[state]
            order.filled_quantity = int(float(broker_order.filled_qty or 0))
            if broker_order.filled_avg_price:
                order.filled_avg_price = float(broker_order.filled_avg_price)
            order.updated_at = datetime.now()

            logger.info(
                f"Order {order.external_id} for {order.symbol} is now "
                f"{order.status.value} ({order.filled_quantity}/{order.quantity} filled)"
            )
            results.append({
                "symbol": order.symbol,
                "status": order.status.value,
                "filled_quantity": order.filled_quantity,
                "filled_avg_price": order.filled_avg_price,
            })

        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error saving reconciled orders: {e}")
            self.db.rollback()

        # Fills move cash and positions, so refresh the mirror.
        if results:
            self.sync_from_alpaca()

        return results

    def execute_order(self, order: Union[Order, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Submit an order to Alpaca's paper trading account.

        The order is sent and recorded as SUBMITTED; it is not treated as
        filled here, because a market order placed while the market is closed
        queues until the open. reconcile_orders() picks up the outcome later.

        Args:
            order: The order to execute (either an Order object or a dictionary).

        Returns:
            A dictionary with the submission result.
        """
        symbol = getattr(order, "symbol", None) or (
            order.get("symbol") if isinstance(order, dict) else None
        )

        try:
            if isinstance(order, dict):
                class DictOrder:
                    pass

                dict_order = DictOrder()
                for key, value in order.items():
                    setattr(dict_order, key, value)
                order = dict_order

            symbol = order.symbol
            side = order.side.value if hasattr(order.side, "value") else str(order.side)
            side = side.lower()
            quantity = int(order.quantity)

            if quantity <= 0:
                return self._reject(order, symbol, side, quantity,
                                    "Order quantity must be positive")

            # Refuse to trade on numbers we could not verify with the broker.
            if not self.sync_from_alpaca():
                return self._reject(
                    order, symbol, side, quantity,
                    "Could not reach Alpaca to verify the account before trading"
                )

            current_price = self.market_data.get_current_price(symbol)

            if side == "buy":
                # The fund's own risk rule, checked against the real account.
                portfolio_value = self.cash + sum(
                    p.market_value for p in self.positions.values()
                )
                trade_value = current_price * quantity
                trade_percent = trade_value / portfolio_value if portfolio_value > 0 else 0

                if trade_percent > self.max_position_size:
                    return self._reject(
                        order, symbol, side, quantity,
                        f"Trade exceeds max position size "
                        f"({trade_percent:.2%} > {self.max_position_size:.2%})"
                    )

                if trade_value > getattr(self, "buying_power", self.cash):
                    return self._reject(
                        order, symbol, side, quantity,
                        f"Insufficient buying power: "
                        f"${getattr(self, 'buying_power', self.cash):,.2f} available, "
                        f"${trade_value:,.2f} required"
                    )

            elif side == "sell":
                held = self.positions.get(symbol)
                if not held:
                    return self._reject(order, symbol, side, quantity,
                                        f"Cannot sell {symbol}: no position at Alpaca")
                if held.quantity < quantity:
                    return self._reject(
                        order, symbol, side, quantity,
                        f"Cannot sell {quantity} shares of {symbol}: "
                        f"only {held.quantity} held"
                    )

            # Send it to the broker.
            submitted = self.alpaca.submit_order(
                symbol=symbol,
                qty=quantity,
                side=side,
                type="market",
                time_in_force="day"
            )

            if self.db and hasattr(order, "id"):
                db_order = self.db.query(Order).filter_by(id=order.id).first()
                if db_order:
                    db_order.external_id = submitted.id
                    db_order.status = OrderStatusEnum.SUBMITTED
                    db_order.updated_at = datetime.now()
                    self.db.commit()

            logger.info(
                f"Submitted {side} {quantity} {symbol} to Alpaca "
                f"(order {submitted.id}, status {submitted.status})"
            )

            return {
                "success": True,
                "message": f"Submitted {side} {quantity} shares of {symbol} to Alpaca",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": current_price,
                "value": quantity * current_price,
                "external_id": submitted.id,
                "broker_status": submitted.status,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # A broker rejection is a real outcome, not a reason to pretend the
            # trade happened: no position is invented that Alpaca does not know.
            logger.error(f"Error submitting order for {symbol}: {e}")
            return self._reject(
                order, symbol,
                getattr(order, "side", "unknown"),
                getattr(order, "quantity", 0),
                f"Alpaca rejected or was unreachable: {e}"
            )

    def _reject(self, order, symbol, side, quantity, reason: str) -> Dict[str, Any]:
        """Mark an order rejected and return the failure result."""
        logger.warning(f"Order rejected for {symbol}: {reason}")

        if self.db and hasattr(order, "id"):
            try:
                db_order = self.db.query(Order).filter_by(id=order.id).first()
                if db_order:
                    db_order.status = OrderStatusEnum.REJECTED
                    db_order.updated_at = datetime.now()
                    self.db.commit()
            except Exception as e:
                logger.error(f"Error recording rejection: {e}")
                self.db.rollback()

        side = side.value if hasattr(side, "value") else side
        return {
            "success": False,
            "message": reason,
            "symbol": symbol,
            "side": side,
            "quantity": quantity
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