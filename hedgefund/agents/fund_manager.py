"""
Fund manager agent (Bill Ackman) who evaluates recommendations from analysts.
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

import openai
from sqlalchemy.orm import Session

from hedgefund.config import OPENAI_API_KEY, FUND_MANAGER
from hedgefund.models import (
    Recommendation, ManagerDecision, Order, OrderSideEnum, 
    OrderTypeEnum, OrderStatusEnum
)
from hedgefund.data import MarketData

# Configure logging
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = OPENAI_API_KEY


class FundManager:
    """Fund manager AI agent (Bill Ackman)."""
    
    def __init__(
        self,
        name: str = FUND_MANAGER["name"],
        model: str = FUND_MANAGER["model"],
        temperature: float = FUND_MANAGER["temperature"],
        style: str = FUND_MANAGER["style"],
        db: Optional[Session] = None,
        market_data: Optional[MarketData] = None
    ):
        """
        Initialize the fund manager.
        
        Args:
            name: The name of the fund manager.
            model: The OpenAI model to use.
            temperature: The temperature for the AI response.
            style: The investment style of the fund manager.
            db: Optional database session.
            market_data: Optional market data service.
        """
        self.name = name
        self.model = model
        self.temperature = temperature
        self.style = style
        self.db = db
        self.market_data = market_data or MarketData()
    
    def _format_system_prompt(self) -> str:
        """
        Format the system prompt for the AI.
        
        Returns:
            The system prompt string.
        """
        return f"""You are {self.name}, a hedge fund manager with {self.style}.
Your job is to evaluate investment recommendations from your team of analysts.

When evaluating a recommendation:
1. Consider the analyst's specialty and track record
2. Evaluate the strength of the reasoning
3. Assess the risk-reward profile
4. Consider how it fits with the overall portfolio
5. Make a final decision: approve, modify, or reject

Format your response as a JSON object with the following fields:
- decision: "APPROVE", "MODIFY", or "REJECT"
- reasoning: Detailed explanation for your decision
- modified_quantity: (if "MODIFY") Your adjusted position size
- modified_target_price: (if "MODIFY") Your adjusted target price
- modified_stop_loss: (if "MODIFY") Your adjusted stop loss
- confidence: Your confidence in this decision (0.0-1.0)

Only respond with valid JSON. Do not include any other text outside the JSON object."""
    
    def _get_user_prompt(
        self, 
        recommendation: Dict[str, Any], 
        analyst_info: Dict[str, Any],
        portfolio_info: Dict[str, Any]
    ) -> str:
        """
        Format the user prompt for the AI.
        
        Args:
            recommendation: The recommendation data.
            analyst_info: Information about the analyst.
            portfolio_info: Information about the current portfolio.
            
        Returns:
            The formatted user prompt.
        """
        prompt = f"""Please evaluate the following investment recommendation:

Analyst: {analyst_info.get('name', 'Unknown')}
Specialty: {analyst_info.get('specialty', 'Unknown')}
Timeframe: {analyst_info.get('timeframe', 'Unknown')}

Recommendation:
- Symbol: {recommendation.get('symbol', 'Unknown')}
- Action: {recommendation.get('action', 'Unknown')}
- Target Price: ${recommendation.get('target_price', 'N/A')}
- Stop Loss: ${recommendation.get('stop_loss', 'N/A')}
- Quantity: {recommendation.get('quantity', 'N/A')} shares
- Confidence: {recommendation.get('confidence', 'N/A')}

Reasoning:
{recommendation.get('reasoning', 'No reasoning provided')}

Current Portfolio Information:
- Cash Available: ${portfolio_info.get('cash', 0):,.2f}
- Total Equity: ${portfolio_info.get('equity', 0):,.2f}
- Number of Positions: {len(portfolio_info.get('positions', []))}
"""

        # Add existing position if we already own this stock
        for position in portfolio_info.get('positions', []):
            if position.get('symbol') == recommendation.get('symbol'):
                prompt += f"""
Existing Position in {recommendation.get('symbol')}:
- Current Shares: {position.get('quantity', 0)}
- Average Cost: ${position.get('avg_entry_price', 0):,.2f}
- Current Value: ${position.get('market_value', 0):,.2f}
- Unrealized P/L: ${position.get('unrealized_pl', 0):,.2f} ({position.get('unrealized_pl_percent', 0):.2f}%)
"""
                break
        
        prompt += """
Based on this information, please decide whether to approve, modify, or reject this recommendation.
Consider the analyst's expertise, the strength of the reasoning, risk-reward, and how it fits with the overall portfolio.
"""
        return prompt
    
    def evaluate_recommendation(
        self, 
        recommendation: Dict[str, Any], 
        analyst_info: Dict[str, Any],
        portfolio_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a recommendation from an analyst.
        
        Args:
            recommendation: The recommendation data.
            analyst_info: Information about the analyst.
            portfolio_info: Information about the current portfolio.
            
        Returns:
            A dictionary with the evaluation decision.
        """
        # Create prompts
        system_prompt = self._format_system_prompt()
        user_prompt = self._get_user_prompt(recommendation, analyst_info, portfolio_info)
        
        # Get evaluation from OpenAI
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
            decision_text = response.choices[0].message.content
            decision_data = json.loads(decision_text)
            
            # Save to database if available
            if self.db and 'recommendation_id' in recommendation:
                self._save_decision(recommendation['recommendation_id'], decision_data)
                
            return decision_data
            
        except Exception as e:
            logger.error(f"Error getting evaluation from OpenAI: {e}")
            raise
    
    def _save_decision(self, recommendation_id: int, decision_data: Dict[str, Any]) -> Optional[ManagerDecision]:
        """
        Save a manager decision to the database.
        
        Args:
            recommendation_id: The ID of the recommendation being evaluated.
            decision_data: The decision data to save.
            
        Returns:
            The saved ManagerDecision object or None if an error occurred.
        """
        try:
            # Parse decision
            decision = decision_data.get('decision', '').upper()
            approved = decision == 'APPROVE' or decision == 'MODIFY'
            
            # Create decision
            manager_decision = ManagerDecision(
                recommendation_id=recommendation_id,
                approved=approved,
                reasoning=decision_data.get('reasoning', ''),
                modified_quantity=decision_data.get('modified_quantity'),
                modified_target_price=decision_data.get('modified_target_price'),
                modified_stop_loss=decision_data.get('modified_stop_loss')
            )
            
            self.db.add(manager_decision)
            self.db.commit()
            self.db.refresh(manager_decision)
            
            logger.info(f"Saved manager decision for recommendation {recommendation_id}: {'Approved' if approved else 'Rejected'}")
            return manager_decision
            
        except Exception as e:
            logger.error(f"Error saving manager decision to database: {e}")
            self.db.rollback()
            return None
    
    def create_order(self, manager_decision_id: int, recommendation: Dict[str, Any], decision: Dict[str, Any]) -> Optional[Order]:
        """
        Create an order based on an approved recommendation.
        
        Args:
            manager_decision_id: The ID of the manager decision.
            recommendation: The recommendation data.
            decision: The decision data.
            
        Returns:
            The created Order object or None if an error occurred.
        """
        try:
            # Only create orders for approved recommendations
            decision_type = decision.get('decision', '').upper()
            if decision_type not in ['APPROVE', 'MODIFY']:
                logger.info(f"Not creating order for rejected recommendation {recommendation.get('recommendation_id')}")
                return None
            
            # Parse order details
            side_str = recommendation.get('action', 'BUY').upper()
            side = OrderSideEnum.BUY if side_str == 'BUY' else OrderSideEnum.SELL
            
            # Use modified values if provided, otherwise use original recommendation
            quantity = decision.get('modified_quantity', recommendation.get('quantity', 0))
            
            # Create order
            order = Order(
                manager_decision_id=manager_decision_id,
                symbol=recommendation.get('symbol', ''),
                side=side,
                type=OrderTypeEnum.MARKET,  # Default to market order
                quantity=quantity,
                status=OrderStatusEnum.NEW
            )
            
            self.db.add(order)
            self.db.commit()
            self.db.refresh(order)
            
            logger.info(f"Created order for {side.value} {quantity} shares of {recommendation.get('symbol')}")
            return order
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            self.db.rollback()
            return None
    
    def evaluate_pending_recommendations(self, portfolio_info: Dict[str, Any]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Evaluate all pending recommendations in the database.
        
        Args:
            portfolio_info: Information about the current portfolio.
            
        Returns:
            A list of tuples with (recommendation, decision) for each evaluated recommendation.
        """
        if not self.db:
            logger.error("Cannot evaluate pending recommendations without a database connection")
            return []
        
        # Get pending recommendations
        pending_recommendations = (
            self.db.query(Recommendation)
            .filter(~Recommendation.decisions.any())  # No decisions yet
            .all()
        )
        
        results = []
        for rec in pending_recommendations:
            try:
                # Convert to dictionary
                recommendation = {
                    'recommendation_id': rec.id,
                    'symbol': rec.symbol,
                    'action': rec.side.value.upper(),
                    'target_price': rec.target_price,
                    'stop_loss': rec.stop_loss,
                    'quantity': rec.quantity,
                    'timeframe': rec.timeframe.value,
                    'confidence': rec.confidence,
                    'reasoning': rec.reasoning
                }
                
                # Get analyst info
                analyst_info = {
                    'name': rec.analyst.name,
                    'specialty': rec.analyst.specialty,
                    'timeframe': rec.analyst.timeframe.value
                }
                
                # Evaluate recommendation
                decision = self.evaluate_recommendation(recommendation, analyst_info, portfolio_info)
                
                # Save decision to database
                manager_decision = self._save_decision(rec.id, decision)
                
                # Create order if approved
                if manager_decision and decision.get('decision', '').upper() in ['APPROVE', 'MODIFY']:
                    self.create_order(manager_decision.id, recommendation, decision)
                
                results.append((recommendation, decision))
                
            except Exception as e:
                logger.error(f"Error evaluating recommendation {rec.id}: {e}")
        
        return results 