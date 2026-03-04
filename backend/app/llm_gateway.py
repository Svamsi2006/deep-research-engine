"""LLM Gateway — unified interface with token-aware routing.

Usage:
    response = call_llm(messages, purpose="planner", max_tokens=512)
    print(response.text, response.model, response.provider)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Rough token estimation (4 chars ≈ 1 token) ──────────────────────────
CHARS_PER_TOKEN = 4


def estimate_tokens(messages: list[dict]) -> int:
    """Estimate the number of input tokens for a message list."""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return total_chars // CHARS_PER_TOKEN + len(messages) * 4  # 4 tok overhead per msg


def truncate_content(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget."""
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated to fit token budget ...]"


# ── Circuit breaker: skip providers that recently returned 429 ───────────
# Maps provider name → timestamp when it can be retried (epoch seconds).
_circuit_open_until: dict[str, float] = {}
_CIRCUIT_COOLDOWN_SECS = 60  # skip provider for 60s after a 429


def _circuit_is_open(provider: str) -> bool:
    """Return True if this provider is temporarily blocked by the circuit breaker."""
    deadline = _circuit_open_until.get(provider, 0)
    if deadline and time.time() < deadline:
        return True
    # Reset once the cooldown has passed
    _circuit_open_until.pop(provider, None)
    return False


def _circuit_trip(provider: str) -> None:
    """Open the circuit for a provider after a rate-limit hit."""
    _circuit_open_until[provider] = time.time() + _CIRCUIT_COOLDOWN_SECS
    logger.info(f"Circuit breaker tripped for '{provider}' — skipping for {_CIRCUIT_COOLDOWN_SECS}s")


def _is_rate_limit_error(e: Exception) -> bool:
    """Check if an exception is a 429 rate-limit error."""
    return "429" in str(e)


# ── Provider rate-limit profiles (input tok per minute for free tiers) ───
PROVIDER_RATE_LIMITS = {
    "gemini":      15_000,   # Gemini free: ~15k TPM
    "openrouter":  200_000,  # varies by model
    "groq":        6_000,    # free: 6k TPM on large models
    "ollama":      999_999,  # local, effectively unlimited
    "openai":      200_000,
    "deepseek":    200_000,
    "grok":        200_000,
}


PROVIDER_DEFAULTS = {
    "ollama":     {"base_url": "http://localhost:11434", "model": "llama3.1:8b"},
    "openai":     {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "gemini":     {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-2.0-flash"},
    "deepseek":   {"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "model": "meta-llama/llama-3.3-70b-instruct:free"},
    "grok":       {"base_url": "https://api.x.ai/v1", "model": "grok-2-latest"},
    "groq":       {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
}


def _normalize_base_url(provider: str, base_url: str) -> str:
    """Strip trailing slashes and fix common provider URL mistakes."""
    normalized = (base_url or "").strip().rstrip("/")
    # Gemini: users sometimes append /v1 to the OpenAI compat endpoint
    if provider == "gemini" and normalized.endswith("/v1"):
        normalized = normalized[:-3].rstrip("/")
        logger.info(f"Gemini base URL corrected: removed trailing /v1")
    return normalized


def _ollama_base_url_candidates(base_url: str) -> list[str]:
    normalized = (base_url or "").strip().rstrip("/")
    if not normalized:
        normalized = "http://localhost:11434"

    if normalized.endswith("/v1"):
        without_v1 = normalized[:-3].rstrip("/")
        return [normalized, without_v1]

    return [normalized, f"{normalized}/v1"]


def _resolve_provider_api_key(settings, provider: str) -> str:
    if settings.ai_api_key:
        return settings.ai_api_key

    provider_keys = {
        "openrouter": settings.openrouter_api_key,
        "groq": settings.groq_api_key,
        "openai": settings.openai_api_key,
        "gemini": settings.google_api_key,
        "deepseek": settings.deepseek_api_key,
        "grok": settings.grok_api_key,
        "ollama": "",
    }
    return provider_keys.get(provider, "")


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
    model = settings.openrouter_model
    # Fix dead model references
    dead_models = ["deepseek-chat-v3-0324:free", "gemini-2.0-flash-exp:free"]
    if any(dead in model for dead in dead_models):
        model = "meta-llama/llama-3.3-70b-instruct:free"
        logger.info(f"OpenRouter model override: dead model replaced with {model}")

    client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )

    t0 = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency = (time.time() - t0) * 1000

    text = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0
    used_model = response.model or model

    return LLMResponse(
        text=text,
        model=used_model,
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


def _call_provider(
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> LLMResponse:
    """Generic OpenAI-compatible provider call."""
    client = OpenAI(base_url=base_url, api_key=api_key or "ollama")

    t0 = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    latency = (time.time() - t0) * 1000

    text = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0
    used_model = response.model or model

    return LLMResponse(
        text=text,
        model=used_model,
        provider=provider,
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
    Call an LLM with token-aware routing, circuit-breaker, and fallback.

    Priority: user-selected provider → OpenRouter → Groq.
    A 429 on any provider trips a circuit breaker (60s cooldown) so
    subsequent pipeline steps skip the rate-limited provider instantly.
    """
    settings = get_settings()

    # ── Token budget guard ────────────────────────────────────────────
    est = estimate_tokens(messages)
    logger.info(f"LLM [{purpose}] estimated input: ~{est} tokens, max_output: {max_tokens}")

    # ── Try user-selected dynamic provider first ─────────────────────
    provider = (settings.ai_provider or "").strip().lower()
    tried_openrouter_as_primary = False

    if provider and not _circuit_is_open(provider):
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        base_url = settings.ai_api_base_url or defaults.get("base_url", "")
        base_url = _normalize_base_url(provider, base_url)
        model = settings.ai_model or defaults.get("model", "")

        api_key = _resolve_provider_api_key(settings, provider)

        if base_url and model and (api_key or provider == "ollama"):
            if provider == "openrouter":
                tried_openrouter_as_primary = True
            try:
                if provider == "ollama":
                    last_error: Exception | None = None
                    for candidate in _ollama_base_url_candidates(base_url):
                        try:
                            result = _call_provider(
                                provider=provider,
                                base_url=candidate,
                                api_key=api_key,
                                model=model,
                                messages=messages,
                                max_tokens=max_tokens,
                                temperature=temperature,
                            )
                            logger.info(f"Ollama endpoint selected: {candidate}")
                            logger.info(
                                f"LLM [{purpose}] via {result.provider}/{result.model} "
                                f"({result.tokens_used} tok, {result.latency_ms}ms)"
                            )
                            return result
                        except Exception as candidate_error:
                            last_error = candidate_error
                            logger.warning(f"Ollama call failed on endpoint {candidate}: {candidate_error}")

                    raise RuntimeError(
                        "Ollama provider selected but request failed on both base URL variants "
                        f"for configured endpoint '{base_url}'."
                    ) from last_error

                result = _call_provider(
                    provider=provider,
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                logger.info(
                    f"LLM [{purpose}] via {result.provider}/{result.model} "
                    f"({result.tokens_used} tok, {result.latency_ms}ms)"
                )
                return result
            except Exception as e:
                logger.warning(f"Dynamic provider {provider} failed for [{purpose}]: {e}")
                if _is_rate_limit_error(e):
                    _circuit_trip(provider)
                # For explicitly-chosen providers (not openrouter/groq):
                # surface the error instead of silently burning fallbacks
                if provider in ("ollama", "gemini", "openai", "deepseek", "grok"):
                    raise RuntimeError(
                        f"Provider '{provider}' failed for [{purpose}]: {e}. "
                        "Check rate limits or switch provider in Settings."
                    ) from e
                # For openrouter/groq as primary, allow fallback below
    elif provider and _circuit_is_open(provider):
        logger.info(f"LLM [{purpose}] skipping {provider} (circuit breaker open)")
        if provider == "openrouter":
            tried_openrouter_as_primary = True  # don't retry in fallback either

    # ── Fallback: OpenRouter (skip if already tried or circuit is open) ──
    if (
        settings.openrouter_api_key
        and not tried_openrouter_as_primary
        and not _circuit_is_open("openrouter")
    ):
        try:
            result = _call_openrouter(messages, max_tokens, temperature)
            logger.info(
                f"LLM [{purpose}] via {result.provider}/{result.model} "
                f"(fallback, {result.tokens_used} tok, {result.latency_ms}ms)"
            )
            return result
        except Exception as e:
            logger.warning(f"OpenRouter [{purpose}] fallback failed: {e}")
            if _is_rate_limit_error(e):
                _circuit_trip("openrouter")

    # ── Fallback: Groq ────────────────────────────────────────────────
    if settings.groq_api_key and not _circuit_is_open("groq"):
        try:
            result = _call_groq(messages, max_tokens, temperature)
            logger.info(
                f"LLM [{purpose}] via {result.provider}/{result.model} "
                f"(fallback, {result.tokens_used} tok, {result.latency_ms}ms)"
            )
            return result
        except Exception as e:
            logger.error(f"Groq [{purpose}] also failed: {e}")
            if _is_rate_limit_error(e):
                _circuit_trip("groq")
            raise RuntimeError(f"All providers failed for [{purpose}]: {e}") from e

    raise RuntimeError("No LLM provider configured. Set an AI provider in Settings.")
