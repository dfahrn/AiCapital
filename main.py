#!/usr/bin/env python
"""
Main entry point for the AI Hedge Fund Simulator.
"""
import os
import sys
import argparse
import threading
import logging
from typing import Dict, Any

from hedgefund.core import Orchestrator
from hedgefund.dashboard import run_dashboard
from hedgefund.utils import setup_logging, log_performance

# Set up logging
logger = setup_logging()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AI Hedge Fund Simulator")
    
    parser.add_argument(
        "--initialize-db",
        action="store_true",
        help="Initialize the database (creates tables)"
    )
    
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Don't start the dashboard"
    )
    
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Start only the dashboard, not the orchestrator"
    )
    
    parser.add_argument(
        "--no-scheduler",
        action="store_true",
        help="Don't start the scheduler"
    )
    
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run one full cycle and exit"
    )
    
    parser.add_argument(
        "--force-run",
        action="store_true",
        help="Force run cycle even if market is closed"
    )
    
    parser.add_argument(
        "--run-analyst",
        metavar="NAME",
        help="Run a specific analyst (value_investor, growth_hunter, technical_analyst, etc.)"
    )
    
    parser.add_argument(
        "--run-fund-manager",
        action="store_true",
        help="Run the fund manager to evaluate pending recommendations"
    )
    
    parser.add_argument(
        "--run-trading",
        action="store_true",
        help="Run the trading system to execute pending orders"
    )
    
    return parser.parse_args()


def run_dashboard_thread():
    """Run the dashboard in a separate thread."""
    try:
        run_dashboard()
    except Exception as e:
        logger.error(f"Error running dashboard: {e}")


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    try:
        # If dashboard only, just start the dashboard
        if args.dashboard_only:
            logger.info("Starting dashboard only")
            run_dashboard()
            return
        
        # Create orchestrator
        logger.info("Initializing AI Hedge Fund Simulator")
        orchestrator = Orchestrator(initialize_db=args.initialize_db)
        
        # Start dashboard in separate thread if requested
        dashboard_thread = None
        if not args.no_dashboard:
            logger.info("Starting dashboard")
            dashboard_thread = threading.Thread(target=run_dashboard_thread)
            dashboard_thread.daemon = True
            dashboard_thread.start()
        
        # Start scheduler if requested
        if not args.no_scheduler:
            logger.info("Starting scheduler")
            orchestrator.start_scheduler()
        
        # Run specific components if requested
        if args.run_analyst:
            logger.info(f"Running analyst: {args.run_analyst}")
            results = orchestrator.run_analyst_cycle(args.run_analyst)
            logger.info(f"Generated {len(results)} recommendations")
        
        if args.run_fund_manager:
            logger.info("Running fund manager")
            results = orchestrator.run_fund_manager_cycle()
            logger.info(f"Made {len(results)} decisions")
        
        if args.run_trading:
            logger.info("Running trading system")
            results = orchestrator.run_trading_cycle()
            logger.info(f"Executed {len(results)} trades")
        
        # Run a full cycle if requested
        if args.run_once:
            logger.info("Running one full cycle")
            results = orchestrator.run_full_cycle(force_run=args.force_run)
            logger.info("Full cycle completed")
        
        # Log current portfolio status
        portfolio = orchestrator.get_portfolio_status()
        log_performance(logger, portfolio)
        
        # If run once, exit
        if args.run_once or args.run_analyst or args.run_fund_manager or args.run_trading:
            logger.info("Requested operations completed")
            orchestrator.close()
            return
        
        # Keep the main thread alive
        logger.info("AI Hedge Fund Simulator running. Press Ctrl+C to exit.")
        try:
            # Wait for the dashboard thread if it exists
            if dashboard_thread:
                while dashboard_thread.is_alive():
                    dashboard_thread.join(1)
            else:
                # Otherwise just keep the main thread alive
                import time
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
        finally:
            orchestrator.close()
            
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 