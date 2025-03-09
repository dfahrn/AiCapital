# AI Hedge Fund Simulator

An AI-powered hedge fund simulator that uses multiple AI agents to paper trade in the stock market in real-time. Each AI has its own investment strategy and personality, reporting to a virtual fund manager named Bill Ackman who makes the final investment decisions.

## Project Overview

This project simulates a hedge fund with 8 different AI "analysts" who provide investment recommendations based on their unique strategies and expertise. The fund manager (Bill Ackman) evaluates these recommendations and decides which trades to execute in a paper trading environment.

### AI Analysts

The system includes 8 different AI analysts, each with unique specialties:
1. **Value Investor** - Focuses on undervalued companies with strong fundamentals
2. **Growth Hunter** - Targets high-growth potential companies
3. **Technical Analyst** - Uses chart patterns and technical indicators
4. **Sentiment Analyzer** - Monitors news, social media, and market sentiment
5. **Sector Specialist** - Focuses on specific industry sectors (Tech, Healthcare, etc.)
6. **Macro Economist** - Analyzes broader economic trends and their impact
7. **Risk Manager** - Specializes in identifying and mitigating investment risks
8. **Momentum Trader** - Follows market momentum and trends

### Fund Manager (Bill Ackman)

The virtual fund manager reviews all recommendations from the AI analysts and makes the final decisions on which trades to execute, taking into account:
- Risk-reward profiles
- Portfolio diversification
- Market conditions
- Investment timeframes

## Project Structure

```
hedgefund/
├── agents/          # AI agents (analysts and fund manager)
├── config/          # Configuration settings
├── core/            # Core functionality
├── dashboard/       # Visualization and reporting
├── data/            # Data fetching and processing
├── models/          # Data models
├── trading/         # Paper trading execution
└── utils/           # Utility functions
```

## Setup Instructions

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_key
   ALPACA_API_KEY=your_alpaca_key
   ALPACA_SECRET_KEY=your_alpaca_secret
   ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
   ```
4. Run the system:
   ```
   python main.py
   ```

## Features

- Real-time paper trading with virtual portfolio
- Multiple AI analysts with different investment strategies
- AI fund manager to evaluate and approve trades
- Performance tracking and reporting
- Market data integration
- Portfolio visualization

## Disclaimer

This is a simulation tool for educational purposes only. It does not constitute financial advice, and the developers are not responsible for any investment decisions made based on this tool. # AiCapital
