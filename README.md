# AI Hedge Fund Simulator

An AI-powered hedge fund simulator that uses multiple AI agents to paper trade in the stock market in real-time. Each AI has its own investment strategy and personality, reporting to a virtual fund manager who makes the final investment decisions.

## Project Overview

This project simulates a hedge fund with 8 different AI "analysts" who provide investment recommendations based on their unique strategies and expertise. The fund manager evaluates these recommendations and decides which trades to execute in a paper trading environment.

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

### Fund Manager

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

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Python 3.12, `alpaca-trade-api==3.0.2` hard-pins `PyYAML==6.0`, which fails to
build. If the install stops there, use:

```bash
pip install -r requirements.txt --no-deps alpaca-trade-api
pip install "PyYAML>=6.0.1" "websockets>=9.0,<11" "websocket-client>=0.56.0,<2" msgpack deprecation
pip install --no-deps alpaca-trade-api==3.0.2
```

### 2. Choose an LLM provider

The agents talk to any **OpenAI-compatible** chat-completions endpoint, so the
simulator runs on free providers as well as OpenAI. Copy the template and fill
in one block:

```bash
cp .env.template .env
```

| Provider | Free? | `LLM_BASE_URL` | Example model |
|---|---|---|---|
| **Groq** (default) | Free tier, no card | `https://api.groq.com/openai/v1` | `openai/gpt-oss-120b` |
| **Google Gemini** | Free tier, but see below | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-3.6-flash` |
| **OpenRouter** | Free `:free` models | `https://openrouter.ai/api/v1` | `deepseek/deepseek-chat-v3-0324:free` |
| **Ollama** | Free, local, offline | `http://localhost:11434/v1` | `llama3.1` |
| **OpenAI** | Paid | `https://api.openai.com/v1` | `gpt-4o-mini` |

Get a free Groq key at [console.groq.com/keys](https://console.groq.com/keys).

#### Budgeting free-tier requests

A full cycle makes **8 x (1 + `SYMBOLS_PER_ANALYST`)** LLM calls - 48 at the
default. Check that against your provider's quota before running one:

- **Gemini's free tier is 20 requests/day and 5/minute per model**, so a full
  cycle cannot complete there. Set `SYMBOLS_PER_ANALYST=1` (16 calls) and
  `LLM_REQUEST_DELAY=13`, and expect about one cycle per day.
- **Groq's free tier** is large enough for the default, which is why it is the
  default here.
- Gemini's daily quota is **per model**, so switching `LLM_MODEL` gives a fresh
  allowance.

Run `python check_llm.py --list` to see the models a key can use; providers
retire model names regularly.

Relevant settings:

- `LLM_MODEL` — used by all 8 analysts and the fund manager.
- `LLM_JSON_MODE` — set to `false` for models without OpenAI JSON mode
  (common on OpenRouter's free tier and small local models). The client then
  asks for JSON in the prompt and parses it leniently.
- `LLM_REQUEST_DELAY` — minimum seconds between calls, measured from the
  previous request. Raise it if a free tier rate-limits you.
- `SYMBOLS_PER_ANALYST` — symbols each analyst researches per cycle (default
  `5`). The main lever on how many calls a cycle makes.
- `LLM_MAX_RETRIES` — retries with exponential backoff on transient errors.

### 3. Add Alpaca paper-trading keys

Create a free paper account at [alpaca.markets](https://alpaca.markets), then
**Home → API Keys → Generate**, and put them in `.env`:

```
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
```

### 4. Verify the model works

```bash
python check_llm.py          # connectivity and JSON-mode check
python check_llm.py AAPL     # plus one real analyst run, no Alpaca needed
```

### 5. Run the system

```bash
python main.py --initialize-db --run-once --force-run
```

Then for continuous operation:

```bash
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
