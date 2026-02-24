"""LLM Gateway — unified interface with OpenRouter → Groq failover.

Usage:
    response = await call_llm(messages, purpose="planner", max_tokens=512)
    print(response.text, response.model, response.provider)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Result from an LLM call."""
    text: str
    model: str
    provider: str          # "openrouter" or "groq"
    tokens_used: int
    latency_ms: float


def _call_openrouter(messages: list[dict], max_tokens: int, temperature: float) -> LLMResponse:
    """Call OpenRouter with the free auto-router model."""
    settings = get_settings()
    client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )

    t0 = time.time()
    response = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency = (time.time() - t0) * 1000

    text = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0
    model = response.model or settings.openrouter_model

    return LLMResponse(
        text=text,
        model=model,
        provider="openrouter",
        tokens_used=tokens,
        latency_ms=round(latency, 1),
    )


def _call_groq(messages: list[dict], max_tokens: int, temperature: float) -> LLMResponse:
    """Call Groq as fallback."""
    settings = get_settings()
    client = OpenAI(
        base_url=settings.groq_base_url,
        api_key=settings.groq_api_key,
    )

    t0 = time.time()
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency = (time.time() - t0) * 1000

    text = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0

    return LLMResponse(
        text=text,
        model=settings.groq_model,
        provider="groq",
        tokens_used=tokens,
        latency_ms=round(latency, 1),
    )


def call_llm(
    messages: list[dict],
    purpose: str = "general",
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> LLMResponse:
    """
    Call an LLM with automatic failover.

    Tries OpenRouter first (free models).
    On 429/5xx/timeout → retry once → fallback to Groq.

    Args:
        messages: OpenAI-format messages list
        purpose: Label for logging (e.g., "planner", "writer", "judge")
        max_tokens: Max output tokens
        temperature: Sampling temperature

    Returns:
        LLMResponse with text, model used, provider, tokens, latency
    """
    settings = get_settings()

    # ── Try OpenRouter ────────────────────────────────────────────────
    if settings.openrouter_api_key:
        for attempt in range(2):  # retry once
            try:
                result = _call_openrouter(messages, max_tokens, temperature)
                logger.info(
                    f"LLM [{purpose}] via {result.provider}/{result.model} "
                    f"({result.tokens_used} tok, {result.latency_ms}ms)"
                )
                return result
            except Exception as e:
                err_str = str(e)
                is_retryable = any(code in err_str for code in ["429", "500", "502", "503", "timeout"])
                if is_retryable and attempt == 0:
                    logger.warning(f"OpenRouter [{purpose}] attempt {attempt+1} failed: {e}, retrying...")
                    continue
                elif is_retryable:
                    logger.warning(f"OpenRouter [{purpose}] failed after retry: {e}, falling back to Groq")
                    break
                else:
                    logger.warning(f"OpenRouter [{purpose}] non-retryable error: {e}, falling back to Groq")
                    break

    # ── Fallback to Groq ──────────────────────────────────────────────
    if settings.groq_api_key:
        try:
            result = _call_groq(messages, max_tokens, temperature)
            logger.info(
                f"LLM [{purpose}] via {result.provider}/{result.model} "
                f"(fallback, {result.tokens_used} tok, {result.latency_ms}ms)"
            )
            return result
        except Exception as e:
            logger.error(f"Groq [{purpose}] also failed: {e}")
            raise RuntimeError(f"Both OpenRouter and Groq failed for [{purpose}]: {e}") from e

    raise RuntimeError("No LLM provider configured. Set OPENROUTER_API_KEY or GROQ_API_KEY.")
