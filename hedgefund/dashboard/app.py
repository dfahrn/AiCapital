"""
Dashboard application for the AI Hedge Fund Simulator.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, callback, Output, Input
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

from hedgefund.config import DASHBOARD_PORT, DASHBOARD_HOST
from hedgefund.models import SessionLocal
from hedgefund.models import (
    PortfolioSnapshot, Position, Recommendation, ManagerDecision,
    Order, AnalystPerformance, Analyst
)
from hedgefund.utils import setup_logging, get_eastern_time

# Set up logging
logger = logging.getLogger(__name__)

# Initialize the dashboard app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="AI Hedge Fund Dashboard"
)

# Define layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("AI Hedge Fund Dashboard", className="text-center my-4"),
            html.Hr()
        ], width=12)
    ]),
    
    # Auto-refresh indicator
    dbc.Row([
        dbc.Col([
            dbc.Alert([
                html.I(className="fas fa-sync-alt mr-2"),
                "Portfolio data auto-refreshes every 3 minutes",
                html.Span(id="refresh-countdown", className="ml-2 font-weight-bold")
            ], color="info", className="text-center mb-4")
        ], width=12)
    ]),
    
    # Portfolio Overview
    dbc.Row([
        dbc.Col([
            html.H3("Portfolio Overview"),
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H5("Total Equity"),
                            html.H3(id="total-equity", className="text-primary")
                        ], width=4),
                        dbc.Col([
                            html.H5("Cash"),
                            html.H3(id="cash-balance", className="text-info")
                        ], width=4),
                        dbc.Col([
                            html.H5("P&L"),
                            html.H3(id="total-pl", className="")
                        ], width=4)
                    ])
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Equity Chart
    dbc.Row([
        dbc.Col([
            html.H3("Equity Performance"),
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id="equity-chart")
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Positions and Analyst Performance
    dbc.Row([
        # Current Positions
        dbc.Col([
            html.H3("Current Positions"),
            dbc.Card([
                dbc.CardBody([
                    html.Div(id="positions-table")
                ])
            ], className="mb-4")
        ], width=6),
        
        # Analyst Performance
        dbc.Col([
            html.H3("Analyst Performance"),
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id="analyst-performance-chart")
                ])
            ], className="mb-4")
        ], width=6)
    ]),
    
    # Recent Activity
    dbc.Row([
        dbc.Col([
            html.H3("Recent Activity"),
            dbc.Card([
                dbc.CardBody([
                    html.Div(id="recent-activity")
                ])
            ], className="mb-4")
        ], width=12)
    ]),
    
    # Refresh interval
    dcc.Interval(
        id='interval-component',
        interval=180000,  # refresh every 3 minutes (180000 ms)
        n_intervals=0
    ),
    
    # Countdown timer interval (updates every second)
    dcc.Interval(
        id='countdown-interval',
        interval=1000,  # update every second
        n_intervals=0
    )
], fluid=True)

# Callback for countdown timer
@app.callback(
    Output("refresh-countdown", "children"),
    [Input("countdown-interval", "n_intervals"),
     Input("interval-component", "n_intervals")]
)
def update_countdown(countdown_n, refresh_n):
    """Update the countdown timer showing seconds until next refresh."""
    # Calculate seconds remaining until next refresh
    seconds_remaining = 180 - (countdown_n % 180)
    
    # Format as minutes:seconds
    minutes = seconds_remaining // 60
    seconds = seconds_remaining % 60
    
    return f"(Next refresh in: {minutes:01d}:{seconds:02d})"

# Callbacks to update dashboard components
@app.callback(
    [
        Output("total-equity", "children"),
        Output("cash-balance", "children"),
        Output("total-pl", "children"),
        Output("total-pl", "className")
    ],
    [Input("interval-component", "n_intervals")]
)
def update_portfolio_overview(n):
    """Update the portfolio overview metrics."""
    try:
        db = SessionLocal()
        
        # Get latest portfolio snapshot
        latest_snapshot = (
            db.query(PortfolioSnapshot)
            .order_by(PortfolioSnapshot.date.desc())
            .first()
        )
        
        if latest_snapshot:
            # Format values
            equity = f"${latest_snapshot.equity:,.2f}"
            cash = f"${latest_snapshot.cash:,.2f}"
            pl = f"${latest_snapshot.total_pl:,.2f} ({latest_snapshot.total_pl_percent:.2f}%)"
            
            # Determine P&L color
            pl_class = "text-success" if latest_snapshot.total_pl >= 0 else "text-danger"
            
            return equity, cash, pl, pl_class
        
        return "$0.00", "$0.00", "$0.00 (0.00%)", "text-secondary"
    
    except Exception as e:
        logger.error(f"Error updating portfolio overview: {e}")
        return "$0.00", "$0.00", "$0.00 (0.00%)", "text-secondary"
    finally:
        db.close()


@app.callback(
    Output("equity-chart", "figure"),
    [Input("interval-component", "n_intervals")]
)
def update_equity_chart(n):
    """Update the equity performance chart."""
    try:
        db = SessionLocal()
        
        # Get portfolio snapshot history
        snapshots = (
            db.query(PortfolioSnapshot)
            .order_by(PortfolioSnapshot.date.asc())
            .all()
        )
        
        if snapshots:
            # Create DataFrame
            data = pd.DataFrame([
                {
                    'date': snapshot.date,
                    'equity': snapshot.equity,
                    'cash': snapshot.cash,
                    'positions_value': snapshot.total_positions_value
                }
                for snapshot in snapshots
            ])
            
            # Create figure
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=data['date'],
                y=data['equity'],
                mode='lines',
                name='Total Equity',
                line=dict(color='rgb(41, 128, 185)', width=3)
            ))
            
            fig.add_trace(go.Scatter(
                x=data['date'],
                y=data['cash'],
                mode='lines',
                name='Cash',
                line=dict(color='rgb(46, 204, 113)', width=2, dash='dot')
            ))
            
            fig.add_trace(go.Scatter(
                x=data['date'],
                y=data['positions_value'],
                mode='lines',
                name='Positions Value',
                line=dict(color='rgb(155, 89, 182)', width=2, dash='dot')
            ))
            
            fig.update_layout(
                title='Portfolio Equity Over Time',
                xaxis_title='Date',
                yaxis_title='Value ($)',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                template='plotly_white'
            )
            
            return fig
        
        # Empty chart if no data
        return go.Figure()
    
    except Exception as e:
        logger.error(f"Error updating equity chart: {e}")
        return go.Figure()
    finally:
        db.close()


@app.callback(
    Output("positions-table", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_positions_table(n):
    """Update the current positions table."""
    try:
        db = SessionLocal()
        
        # Get current positions
        positions = db.query(Position).all()
        
        # Add timestamp for last update
        last_updated = get_eastern_time().strftime("%Y-%m-%d %H:%M:%S")
        
        if positions:
            # Create table
            table_content = [
                html.Thead([
                    html.Tr([
                        html.Th("Symbol"),
                        html.Th("Quantity"),
                        html.Th("Avg Price"),
                        html.Th("Current Price"),
                        html.Th("Value"),
                        html.Th("P&L"),
                        html.Th("P&L %"),
                        html.Th("Recommended By")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(position.symbol, style={'font-weight': 'bold'}),
                        html.Td(f"{position.quantity:,}"),
                        html.Td(f"${position.avg_entry_price:,.2f}"),
                        html.Td(f"${position.current_price:,.2f}"),
                        html.Td(f"${position.market_value:,.2f}"),
                        html.Td(
                            f"${position.unrealized_pl:,.2f}",
                            style={'color': 'green' if position.unrealized_pl >= 0 else 'red', 'font-weight': 'bold'}
                        ),
                        html.Td(
                            f"{position.unrealized_pl_percent:.2f}%",
                            style={'color': 'green' if position.unrealized_pl_percent >= 0 else 'red', 'font-weight': 'bold'}
                        ),
                        html.Td(position.analyst_name if hasattr(position, 'analyst_name') else "N/A")
                    ])
                    for position in positions
                ])
            ]
            
            # Create the table with the contents
            table = dbc.Table(table_content, bordered=True, hover=True, striped=True, className="table-sm")
            
            # Add last updated information
            return html.Div([
                table,
                html.Div(f"Last updated: {last_updated}", className="text-muted text-right small mt-2")
            ])
        
        return html.Div([
            html.P("No active positions", className="text-center p-3"),
            html.Div(f"Last updated: {last_updated}", className="text-muted text-right small mt-2")
        ])
    
    except Exception as e:
        logger.error(f"Error updating positions table: {e}")
        return html.P(f"Error loading positions: {str(e)}")
    finally:
        db.close()


@app.callback(
    Output("analyst-performance-chart", "figure"),
    [Input("interval-component", "n_intervals")]
)
def update_analyst_performance(n):
    """Update the analyst performance chart."""
    try:
        db = SessionLocal()
        
        # Get analyst performance data
        performances = (
            db.query(AnalystPerformance)
            .join(Analyst)
            .all()
        )
        
        if performances:
            # Create DataFrame
            data = []
            for perf in performances:
                data.append({
                    'analyst': perf.analyst.name,
                    'approved_count': perf.approved_count,
                    'rejected_count': perf.rejected_count,
                    'success_rate': (perf.successful_trades / perf.approved_count) * 100 if perf.approved_count > 0 else 0,
                    'profit_generated': perf.profit_generated,
                    'average_return': perf.average_return or 0
                })
            
            df = pd.DataFrame(data)
            
            # Group by analyst
            df_grouped = df.groupby('analyst').agg({
                'approved_count': 'sum',
                'rejected_count': 'sum',
                'profit_generated': 'sum',
                'average_return': 'mean'
            }).reset_index()
            
            # Create figure
            fig = px.bar(
                df_grouped,
                x='analyst',
                y='profit_generated',
                color='average_return',
                text='approved_count',
                title='Analyst Performance (Profit Generated)',
                labels={
                    'analyst': 'Analyst',
                    'profit_generated': 'Profit Generated ($)',
                    'average_return': 'Avg Return (%)',
                    'approved_count': 'Approved Trades'
                },
                color_continuous_scale=px.colors.sequential.Viridis
            )
            
            fig.update_layout(template='plotly_white')
            
            return fig
        
        # Empty chart if no data
        return px.bar(title="No analyst performance data available")
    
    except Exception as e:
        logger.error(f"Error updating analyst performance: {e}")
        return px.bar(title=f"Error: {str(e)}")
    finally:
        db.close()


@app.callback(
    Output("recent-activity", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_recent_activity(n):
    """Update the recent activity feed."""
    try:
        db = SessionLocal()
        
        # Get recent orders
        recent_orders = (
            db.query(Order)
            .order_by(Order.created_at.desc())
            .limit(5)
            .all()
        )
        
        # Get recent recommendations
        recent_recommendations = (
            db.query(Recommendation)
            .order_by(Recommendation.created_at.desc())
            .limit(5)
            .all()
        )
        
        # Get recent decisions
        recent_decisions = (
            db.query(ManagerDecision)
            .order_by(ManagerDecision.created_at.desc())
            .limit(5)
            .all()
        )
        
        # Create activity feed
        items = []
        
        for order in recent_orders:
            items.append({
                'type': 'order',
                'time': order.created_at,
                'content': f"Order {'executed' if order.status.value == 'filled' else order.status.value}: {order.side.value.upper()} {order.quantity} shares of {order.symbol}"
            })
        
        for decision in recent_decisions:
            items.append({
                'type': 'decision',
                'time': decision.created_at,
                'content': f"Bill Ackman {'approved' if decision.approved else 'rejected'} recommendation for {decision.recommendation.symbol}"
            })
        
        for rec in recent_recommendations:
            items.append({
                'type': 'recommendation',
                'time': rec.created_at,
                'content': f"{rec.analyst.name} recommended to {rec.side.value.upper()} {rec.symbol} (Confidence: {rec.confidence:.2f})"
            })
        
        # Sort by time
        items.sort(key=lambda x: x['time'], reverse=True)
        
        # Create feed
        feed = dbc.ListGroup([
            dbc.ListGroupItem([
                html.Div([
                    html.Small(item['time'].strftime("%Y-%m-%d %H:%M:%S"), className="text-muted"),
                    html.P(item['content'], className="mb-1")
                ])
            ], 
            color="primary" if item['type'] == 'order' else (
                   "success" if item['type'] == 'decision' else "info"))
            for item in items[:10]  # Show the 10 most recent activities
        ])
        
        return feed
    
    except Exception as e:
        logger.error(f"Error updating recent activity: {e}")
        return html.P(f"Error loading recent activity: {str(e)}")
    finally:
        db.close()


def run_dashboard(host: str = DASHBOARD_HOST, port: int = DASHBOARD_PORT, debug: bool = False):
    """
    Run the dashboard application.
    
    Args:
        host: The host address to run on.
        port: The port to run on.
        debug: Whether to run in debug mode.
    """
    app.run_server(host=host, port=port, debug=debug)


if __name__ == "__main__":
    # Set up logging
    setup_logging()
    
    # Run the dashboard
    run_dashboard(debug=True) 