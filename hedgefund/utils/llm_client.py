"""
Shared LLM client for the AI agents.

Every agent talks to an OpenAI-compatible chat-completions endpoint, which means
any provider exposing that API works: Google Gemini, Groq, OpenRouter, a local
Ollama server, or OpenAI itself. The endpoint is chosen with LLM_BASE_URL /
LLM_API_KEY / LLM_MODEL in the .env file.
"""
import json
import logging
import re
import time
from typing import Any, Dict, Optional

from openai import OpenAI

from hedgefund.config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_JSON_MODE,
    LLM_MAX_RETRIES, LLM_REQUEST_DELAY
)

logger = logging.getLogger(__name__)

_client: Optional[OpenAI] = None
_last_request_at: float = 0.0


def _throttle() -> None:
    """
    Space requests at least LLM_REQUEST_DELAY seconds apart.

    Measured from the previous request rather than slept blindly, so time the
    call itself spent counts toward the interval. Free tiers cap requests per
    minute (Gemini's is 5/min), and a full cycle makes dozens of calls.
    """
    global _last_request_at

    if LLM_REQUEST_DELAY:
        wait = LLM_REQUEST_DELAY - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)

    _last_request_at = time.monotonic()


def get_client() -> OpenAI:
    """Return the shared OpenAI-compatible client, creating it on first use."""
    global _client

    if _client is None:
        if not LLM_API_KEY:
            raise RuntimeError(
                "No LLM API key configured. Set LLM_API_KEY (or OPENAI_API_KEY) "
                "in your .env file. See .env.template for free provider options."
            )
        # max_retries=0: the SDK's own retries would nest inside our retry loop
        # (up to 9 HTTP requests per call), and every attempt counts against a
        # free tier's quota. We do the retrying ourselves, below.
        _client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            max_retries=0
        )
        logger.info(f"LLM client configured: {LLM_BASE_URL} (model: {LLM_MODEL})")

    return _client


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Parse JSON out of a model response.

    Models without real JSON mode often wrap the object in prose or a markdown
    fence, so fall back to pulling out the outermost braces.
    """
    text = (text or "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip a markdown code fence if present.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Last resort: the outermost {...} span.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from model response: {text[:500]}")


def chat_json(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    Send a chat completion and return the parsed JSON response.

    Args:
        system_prompt: The system message.
        user_prompt: The user message.
        model: Model name; defaults to LLM_MODEL.
        temperature: Sampling temperature.

    Returns:
        The parsed JSON object from the model.
    """
    client = get_client()
    model = model or LLM_MODEL

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Without native JSON mode, ask for JSON in the prompt instead.
    if not LLM_JSON_MODE:
        messages[1]["content"] += (
            "\n\nRespond with a single valid JSON object and nothing else. "
            "Do not wrap it in markdown."
        )

    kwargs: Dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages
    }
    if LLM_JSON_MODE:
        kwargs["response_format"] = {"type": "json_object"}

    last_error: Optional[Exception] = None

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            _throttle()

            response = client.chat.completions.create(**kwargs)
            return _extract_json(response.choices[0].message.content)

        except Exception as e:
            last_error = e

            # A provider that rejects JSON mode should be retried without it.
            if "response_format" in kwargs and _is_json_mode_error(e):
                logger.warning(
                    f"{model} rejected JSON mode; retrying with prompt-instructed "
                    f"JSON. Set LLM_JSON_MODE=false to skip this."
                )
                kwargs.pop("response_format")
                kwargs["messages"][1]["content"] += (
                    "\n\nRespond with a single valid JSON object and nothing else."
                )
                continue

            if _is_permanent_error(e):
                logger.error(
                    f"LLM call failed and will not be retried: {e}\n"
                    f"Check LLM_MODEL ({model}) and LLM_API_KEY in your .env. "
                    f"Run `python check_llm.py --list` to see available models."
                )
                raise

            if _is_daily_quota_exhausted(e):
                logger.error(
                    f"Daily free-tier quota for {model} is exhausted. Retrying "
                    f"will not help until it resets. Switch LLM_MODEL to another "
                    f"model (each has its own daily quota), move to a provider "
                    f"with a larger free tier, or wait for the reset."
                )
                raise

            if attempt < LLM_MAX_RETRIES:
                # Prefer the provider's own advice over blind exponential backoff.
                backoff = _retry_after_seconds(e) or 2 ** attempt
                logger.warning(
                    f"LLM call failed (attempt {attempt}/{LLM_MAX_RETRIES}): {e}. "
                    f"Retrying in {backoff:.0f}s."
                )
                time.sleep(backoff)
            else:
                logger.error(f"LLM call failed after {LLM_MAX_RETRIES} attempts: {e}")

    raise last_error


def chat_text(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """
    Send a chat completion and return the raw text response.

    Used for free-form answers such as ticker suggestions, where no JSON
    structure is expected.
    """
    client = get_client()
    model = model or LLM_MODEL

    last_error: Optional[Exception] = None

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            _throttle()

            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            last_error = e
            if _is_permanent_error(e):
                logger.error(
                    f"LLM call failed and will not be retried: {e}\n"
                    f"Check LLM_MODEL ({model}) and LLM_API_KEY in your .env. "
                    f"Run `python check_llm.py --list` to see available models."
                )
                raise

            if _is_daily_quota_exhausted(e):
                logger.error(
                    f"Daily free-tier quota for {model} is exhausted. Retrying "
                    f"will not help until it resets. Switch LLM_MODEL to another "
                    f"model (each has its own daily quota), move to a provider "
                    f"with a larger free tier, or wait for the reset."
                )
                raise

            if attempt < LLM_MAX_RETRIES:
                # Prefer the provider's own advice over blind exponential backoff.
                backoff = _retry_after_seconds(e) or 2 ** attempt
                logger.warning(
                    f"LLM call failed (attempt {attempt}/{LLM_MAX_RETRIES}): {e}. "
                    f"Retrying in {backoff:.0f}s."
                )
                time.sleep(backoff)
            else:
                logger.error(f"LLM call failed after {LLM_MAX_RETRIES} attempts: {e}")

    raise last_error


def _is_json_mode_error(error: Exception) -> bool:
    """Whether an error looks like the provider not supporting JSON mode."""
    message = str(error).lower()
    return "response_format" in message or "json_object" in message


def _retry_after_seconds(error: Exception) -> Optional[float]:
    """
    The delay a provider asks us to wait, if it says so.

    Gemini returns a RetryInfo block ("retryDelay": "47s") and most providers
    send a Retry-After header. Honouring it beats guessing with backoff.
    """
    response = getattr(error, "response", None)
    if response is not None:
        header = response.headers.get("retry-after")
        if header:
            try:
                return float(header)
            except ValueError:
                pass

    match = re.search(r"'retryDelay':\s*'(\d+(?:\.\d+)?)s'", str(error))
    if match:
        return float(match.group(1))

    return None


def _is_daily_quota_exhausted(error: Exception) -> bool:
    """
    Whether a 429 is the per-day quota rather than the per-minute rate limit.

    Waiting does not help until the quota window resets, so we stop instead of
    grinding through retries that cannot succeed.
    """
    return getattr(error, "status_code", None) == 429 and "PerDay" in str(error)


def _is_permanent_error(error: Exception) -> bool:
    """
    Whether retrying is pointless: a bad key, or a model name that does not
    exist. Providers retire model names regularly, so this is common.
    """
    status = getattr(error, "status_code", None)
    return status in (400, 401, 403, 404)
