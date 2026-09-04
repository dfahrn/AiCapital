#!/usr/bin/env python
"""
Check that the configured LLM provider works before running the simulator.

Usage:
    python check_llm.py            # connectivity + JSON mode check
    python check_llm.py AAPL       # also run one real analyst on a symbol
    python check_llm.py --list     # list model names this key can use
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from hedgefund.config import (
    LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, LLM_JSON_MODE, LLM_REQUEST_DELAY
)
from hedgefund.utils.llm_client import chat_text, chat_json


def list_models():
    """Print the model names the configured key can use."""
    from hedgefund.utils.llm_client import get_client

    print(f"Models available at {LLM_BASE_URL}:\n")
    for model in sorted(m.id for m in get_client().models.list()):
        print(f"  {model}")
    print("\nSet one as LLM_MODEL in .env (drop any 'models/' prefix).")
    return 0


def main():
    if "--list" in sys.argv:
        return list_models()

    print(f"Endpoint  : {LLM_BASE_URL}")
    print(f"Model     : {LLM_MODEL}")
    print(f"JSON mode : {LLM_JSON_MODE}")
    print(f"Delay     : {LLM_REQUEST_DELAY}s between calls")
    is_placeholder = LLM_API_KEY and (
        "your_" in LLM_API_KEY or LLM_API_KEY.endswith("_here")
    )
    if not LLM_API_KEY:
        key_status = "MISSING"
    elif is_placeholder:
        key_status = f"PLACEHOLDER ({LLM_API_KEY})"
    else:
        key_status = f"set ({LLM_API_KEY[:6]}...)"
    print(f"API key   : {key_status}")
    print()

    if not LLM_API_KEY:
        print("FAIL: no API key. Copy .env.template to .env and add one.")
        return 1

    if is_placeholder:
        print("FAIL: LLM_API_KEY is still the template placeholder.")
        print("      Edit .env and replace it with a real key.")
        return 1

    # 1. Plain text call, as used by the analysts' idea generation.
    print("[1/3] Plain text call...")
    try:
        reply = chat_text(
            system_prompt="You are a terse assistant.",
            user_prompt="Reply with exactly: OK",
            temperature=0
        )
        print(f"      -> {reply.strip()[:80]}")
    except Exception as e:
        print(f"      FAILED: {e}")
        return 1

    # 2. JSON call, as used for recommendations and manager decisions.
    print("[2/3] JSON call...")
    try:
        data = chat_json(
            system_prompt="You are a stock analyst that replies in JSON.",
            user_prompt=(
                'Return a JSON object with keys "symbol" (string), '
                '"action" (BUY, SELL or HOLD) and "confidence" (0-1) '
                'for a hypothetical analysis of MSFT.'
            ),
            temperature=0
        )
        print(f"      -> {data}")
    except Exception as e:
        print(f"      FAILED: {e}")
        print("      Try setting LLM_JSON_MODE=false in .env")
        return 1

    # 3. Optionally run a real analyst end to end (no database, no Alpaca).
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    symbol = args[0].upper() if args else None
    if not symbol:
        print("[3/3] Skipped real analyst run (pass a symbol, e.g. "
              "`python check_llm.py AAPL`)")
        print("\nLLM provider is working.")
        return 0

    print(f"[3/3] Running Value Investor on {symbol}...")
    try:
        from hedgefund.agents import ValueInvestor
        analyst = ValueInvestor()          # no db, no Alpaca
        result = analyst.analyze_stock(symbol)
        print()
        for key, value in result.items():
            print(f"      {key}: {value}")
    except Exception as e:
        print(f"      FAILED: {e}")
        return 1

    print("\nLLM provider is working.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
