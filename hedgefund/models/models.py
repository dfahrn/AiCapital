"""
Database models for the AI Hedge Fund Simulator.
"""
import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Enum, 
    DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from .base import Base


class TimeframeEnum(enum.Enum):
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class OrderSideEnum(enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderTypeEnum(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatusEnum(enum.Enum):
    NEW = "new"
    APPROVED = "approved"
    REJECTED = "rejected"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    EXPIRED = "expired"


class Analyst(Base):
    """AI analyst model."""
    __tablename__ = "analysts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    specialty = Column(String(200), nullable=False)
    timeframe = Column(Enum(TimeframeEnum), nullable=False)
    description = Column(Text)
    
    # Relationships
    recommendations = relationship("Recommendation", back_populates="analyst")

    def __repr__(self):
        return f"<Analyst {self.name}>"


class Recommendation(Base):
    """Investment recommendation from an AI analyst."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(Enum(OrderSideEnum), nullable=False)
    target_price = Column(Float)
    stop_loss = Column(Float)
    quantity = Column(Integer)
    timeframe = Column(Enum(TimeframeEnum), nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    reasoning = Column(Text, nullable=False)
    data_sources = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    analyst = relationship("Analyst", back_populates="recommendations")
    decisions = relationship("ManagerDecision", back_populates="recommendation")

    def __repr__(self):
        return f"<Recommendation {self.id}: {self.side.value} {self.symbol}>"


class ManagerDecision(Base):
    """Decision made by the fund manager on a recommendation."""
    __tablename__ = "manager_decisions"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=False)
    approved = Column(Boolean, nullable=False)
    reasoning = Column(Text, nullable=False)
    modified_quantity = Column(Integer)
    modified_target_price = Column(Float)
    modified_stop_loss = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    recommendation = relationship("Recommendation", back_populates="decisions")
    orders = relationship("Order", back_populates="manager_decision")

    def __repr__(self):
        return f"<ManagerDecision {self.id}: {'Approved' if self.approved else 'Rejected'}>"


class Order(Base):
    """Order placed in the paper trading system."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    manager_decision_id = Column(Integer, ForeignKey("manager_decisions.id"), nullable=False)
    external_id = Column(String(100))  # ID from the trading platform
    symbol = Column(String(20), nullable=False)
    side = Column(Enum(OrderSideEnum), nullable=False)
    type = Column(Enum(OrderTypeEnum), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float)  # Limit price if applicable
    stop_price = Column(Float)  # Stop price if applicable
    status = Column(Enum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.NEW)
    filled_quantity = Column(Integer, default=0)
    filled_avg_price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    manager_decision = relationship("ManagerDecision", back_populates="orders")

    def __repr__(self):
        return f"<Order {self.id}: {self.side.value} {self.quantity} {self.symbol}>"


class Position(Base):
    """Current holdings in the portfolio."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, unique=True)
    quantity = Column(Integer, nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    market_value = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=False)
    unrealized_pl = Column(Float, nullable=False)
    unrealized_pl_percent = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Position {self.symbol}: {self.quantity} @ {self.avg_entry_price}>"


class PortfolioSnapshot(Base):
    """Daily snapshot of the portfolio performance."""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, unique=True)
    cash = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    total_positions_value = Column(Float, nullable=False)
    total_pl = Column(Float, nullable=False)
    total_pl_percent = Column(Float, nullable=False)
    positions_data = Column(JSON)  # Snapshot of all positions
    
    def __repr__(self):
        return f"<PortfolioSnapshot {self.date.date()}: ${self.equity:,.2f}>"


class AnalystPerformance(Base):
    """Performance tracking for each AI analyst."""
    __tablename__ = "analyst_performances"

    id = Column(Integer, primary_key=True, index=True)
    analyst_id = Column(Integer, ForeignKey("analysts.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    recommendations_count = Column(Integer, nullable=False, default=0)
    approved_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    successful_trades = Column(Integer, nullable=False, default=0)
    unsuccessful_trades = Column(Integer, nullable=False, default=0)
    profit_generated = Column(Float, nullable=False, default=0.0)
    average_return = Column(Float)
    
    # Relationships
    analyst = relationship("Analyst")
    
    def __repr__(self):
        return f"<AnalystPerformance {self.id}: {self.analyst.name} on {self.date.date()}>" 