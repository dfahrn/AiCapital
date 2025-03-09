"""
Orchestrator module for managing the AI Hedge Fund Simulator system.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
import threading
import schedule

from sqlalchemy.orm import Session

from hedgefund.config import AI_ANALYSTS, FUND_MANAGER, INITIAL_CAPITAL
from hedgefund.models import Base, engine, SessionLocal
from hedgefund.data import MarketData
from hedgefund.agents import (
    ValueInvestor, GrowthHunter, TechnicalAnalyst, SentimentAnalyzer,
    SectorSpecialist, MacroEconomist, RiskManager, MomentumTrader,
    FundManager
)
from hedgefund.trading import PaperTrader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrator for managing the AI Hedge Fund Simulator system."""
    
    def __init__(self, initialize_db: bool = True):
        """
        Initialize the orchestrator.
        
        Args:
            initialize_db: Whether to initialize the database.
        """
        self.market_data = MarketData()
        self.db = SessionLocal()
        
        # Initialize the database if needed
        if initialize_db:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized")
        
        # Create paper trader
        self.paper_trader = PaperTrader(
            initial_capital=INITIAL_CAPITAL,
            db=self.db,
            market_data=self.market_data
        )
        
        # Create fund manager
        self.fund_manager = FundManager(
            db=self.db,
            market_data=self.market_data
        )
        
        # Create AI analysts
        self.analysts = self._create_analysts()
        
        # Scheduling
        self.scheduler_thread = None
        self.scheduler_running = False
        
        logger.info("Orchestrator initialized")
    
    def _create_analysts(self) -> Dict[str, Any]:
        """
        Create all AI analyst agents.
        
        Returns:
            A dictionary of analyst instances keyed by name.
        """
        analysts = {}
        
        # Create each analyst type
        analysts['value_investor'] = ValueInvestor(
            db=self.db,
            market_data=self.market_data
        )
        
        analysts['growth_hunter'] = GrowthHunter(
            db=self.db,
            market_data=self.market_data
        )
        
        analysts['technical_analyst'] = TechnicalAnalyst(
            db=self.db,
            market_data=self.market_data
        )
        
        analysts['sentiment_analyzer'] = SentimentAnalyzer(
            db=self.db,
            market_data=self.market_data
        )
        
        analysts['sector_specialist'] = SectorSpecialist(
            sector="Technology",  # Default to Technology sector
            db=self.db,
            market_data=self.market_data
        )
        
        analysts['macro_economist'] = MacroEconomist(
            db=self.db,
            market_data=self.market_data
        )
        
        analysts['risk_manager'] = RiskManager(
            db=self.db,
            market_data=self.market_data
        )
        
        analysts['momentum_trader'] = MomentumTrader(
            db=self.db,
            market_data=self.market_data
        )
        
        logger.info(f"Created {len(analysts)} AI analysts")
        return analysts
    
    def run_analyst_cycle(self, analyst_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Run a cycle for a specific analyst or all analysts.
        
        Args:
            analyst_name: The name of the analyst to run, or None to run all.
            
        Returns:
            A list of recommendations generated.
        """
        results = []
        
        try:
            # Determine which analysts to run
            analysts_to_run = {}
            if analyst_name:
                if analyst_name in self.analysts:
                    analysts_to_run[analyst_name] = self.analysts[analyst_name]
                else:
                    logger.error(f"Analyst {analyst_name} not found")
            else:
                analysts_to_run = self.analysts
            
            # Run each analyst
            for name, analyst in analysts_to_run.items():
                try:
                    logger.info(f"Running analyst: {name}")
                    
                    # Get investment ideas
                    symbols = analyst.get_investment_ideas()
                    logger.info(f"Analyst {name} generated {len(symbols)} investment ideas: {symbols}")
                    
                    # Analyze each stock
                    for symbol in symbols:
                        try:
                            recommendation = analyst.analyze_stock(symbol)
                            logger.info(f"Analyst {name} recommendation for {symbol}: {recommendation.get('action', 'UNKNOWN')} (confidence: {recommendation.get('confidence', 0)})")
                            results.append(recommendation)
                        except Exception as e:
                            logger.error(f"Error analyzing stock {symbol} with analyst {name}: {e}")
                            
                except Exception as e:
                    logger.error(f"Error running analyst {name}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in run_analyst_cycle: {e}")
            return []
    
    def run_fund_manager_cycle(self) -> List[Dict[str, Any]]:
        """
        Run a cycle for the fund manager to evaluate pending recommendations.
        
        Returns:
            A list of decisions made.
        """
        try:
            # Get portfolio information
            portfolio_info = self.paper_trader.get_portfolio_value()
            
            # Evaluate pending recommendations
            results = self.fund_manager.evaluate_pending_recommendations(portfolio_info)
            
            if results:
                logger.info(f"Fund manager evaluated {len(results)} recommendations")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in run_fund_manager_cycle: {e}")
            return []
    
    def run_trading_cycle(self) -> List[Dict[str, Any]]:
        """
        Run a cycle for executing pending trades.
        
        Returns:
            A list of trade execution results.
        """
        try:
            # Process pending orders
            results = self.paper_trader.process_pending_orders()
            
            if results:
                logger.info(f"Processed {len(results)} orders")
            
            # Take a portfolio snapshot
            self.paper_trader.take_portfolio_snapshot()
            
            return results
            
        except Exception as e:
            logger.error(f"Error in run_trading_cycle: {e}")
            return []
    
    def run_full_cycle(self, force_run: bool = False) -> Dict[str, Any]:
        """
        Run a complete cycle: analysts, fund manager, and trading.
        
        Args:
            force_run: If True, run the cycle even if the market is closed.
            
        Returns:
            A dictionary with the results of each stage.
        """
        if not force_run and not self.market_data.is_market_open():
            logger.info("Market is closed, skipping cycle")
            return {"status": "skipped", "reason": "market_closed"}
        
        results = {
            "analysts": {},
            "fund_manager": [],
            "trading": []
        }
        
        try:
            # Run each analyst
            for name, analyst in self.analysts.items():
                try:
                    logger.info(f"Running analyst: {name}")
                    
                    # Get investment ideas
                    symbols = analyst.get_investment_ideas()
                    logger.info(f"Analyst {name} generated {len(symbols)} investment ideas: {symbols}")
                    
                    # Analyze each stock
                    analyst_results = []
                    for symbol in symbols:
                        try:
                            recommendation = analyst.analyze_stock(symbol)
                            logger.info(f"Analyst {name} recommendation for {symbol}: {recommendation.get('action', 'UNKNOWN')} (confidence: {recommendation.get('confidence', 0)})")
                            analyst_results.append(recommendation)
                        except Exception as e:
                            logger.error(f"Error analyzing stock {symbol} with analyst {name}: {e}")
                    
                    results["analysts"][name] = analyst_results
                    
                except Exception as e:
                    logger.error(f"Error running analyst {name}: {e}")
            
            # Run fund manager
            logger.info("Running fund manager")
            portfolio_info = self.paper_trader.get_portfolio_value()
            fund_manager_results = self.fund_manager.evaluate_pending_recommendations(portfolio_info)
            results["fund_manager"] = fund_manager_results
            
            # Run trading
            logger.info("Running trading cycle")
            trading_results = self.paper_trader.process_pending_orders()
            self.paper_trader.take_portfolio_snapshot()
            results["trading"] = trading_results
            
            logger.info("Full cycle completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error in run_full_cycle: {e}")
            return {"status": "error", "error": str(e)}
    
    def start_scheduler(self):
        """Start the scheduling thread for automated cycles."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.warning("Scheduler already running")
            return
            
        self.scheduler_running = True
        
        def run_scheduler():
            # Schedule cycles
            schedule.every().day.at("09:35").do(self.run_full_cycle)  # Shortly after market open
            schedule.every().day.at("12:00").do(self.run_full_cycle)  # Midday
            schedule.every().day.at("15:45").do(self.run_full_cycle)  # Before market close
            
            # If we want more frequent analyst runs
            schedule.every(30).minutes.do(self.run_analyst_cycle)  # Run all analysts every 30 mins
            
            # Process orders more frequently
            schedule.every(5).minutes.do(self.run_trading_cycle)
            
            # Take portfolio snapshot hourly
            schedule.every(60).minutes.do(self.paper_trader.take_portfolio_snapshot)
            
            logger.info("Scheduler started")
            
            while self.scheduler_running:
                schedule.run_pending()
                time.sleep(1)
        
        self.scheduler_thread = threading.Thread(target=run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        logger.info("Scheduler thread started")
    
    def stop_scheduler(self):
        """Stop the scheduling thread."""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            logger.info("Scheduler stopped")
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        Get the current portfolio status.
        
        Returns:
            A dictionary with portfolio information.
        """
        return self.paper_trader.get_portfolio_value()
    
    def close(self):
        """Clean up resources."""
        self.stop_scheduler()
        if self.db:
            self.db.close()
        logger.info("Orchestrator closed") 