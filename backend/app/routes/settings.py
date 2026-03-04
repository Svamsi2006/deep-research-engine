"""Runtime settings API — user-configurable AI and Web Search settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from dotenv import set_key

from app.config import get_settings, reload_settings

router = APIRouter()

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


AI_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "ollama": {
        "api_base_url": "http://localhost:11434",
        "model": "llama3.1:8b",
        "context_length": 8192,
    },
    "openai": {
        "api_base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "context_length": 128000,
    },
    "gemini": {
        "api_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "context_length": 1048576,
    },
    "deepseek": {
        "api_base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "context_length": 128000,
    },
    "openrouter": {
        "api_base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "context_length": 128000,
    },
    "grok": {
        "api_base_url": "https://api.x.ai/v1",
        "model": "grok-2-latest",
        "context_length": 128000,
    },
    "groq": {
        "api_base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "context_length": 32768,
    },
}

WEB_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "tavily": {"supports_topic": True, "supports_advanced": True},
    "firecrawl": {"supports_topic": False, "supports_advanced": False},
    "duckduckgo": {"supports_topic": False, "supports_advanced": False},
}


class SettingsResponse(BaseModel):
    ai_provider: str
    ai_api_key: str
    ai_api_base_url: str
    ai_model: str
    ai_context_length: int
    web_search_provider: str
    web_search_api_key: str
    web_search_concurrency_limit: int
    web_search_advanced: bool
    web_search_topic: str
    ai_provider_presets: dict[str, dict[str, Any]]
    web_provider_presets: dict[str, dict[str, Any]]


class SettingsUpdateRequest(BaseModel):
    ai_provider: str = Field(default="openrouter")
    ai_api_key: str = Field(default="")
    ai_api_base_url: str = Field(default="")
    ai_model: str = Field(default="")
    ai_context_length: int = Field(default=128000, ge=1024)

    web_search_provider: str = Field(default="tavily")
    web_search_api_key: str = Field(default="")
    web_search_concurrency_limit: int = Field(default=2, ge=1, le=10)
    web_search_advanced: bool = Field(default=False)
    web_search_topic: str = Field(default="general")


def _mask_key(value: str) -> str:
    if not value:
        return ""
    if len(value) < 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


@router.get("/settings", response_model=SettingsResponse)
async def get_runtime_settings():
    s = get_settings()

    ai_api_key = s.ai_api_key
    if not ai_api_key:
        if s.ai_provider == "openrouter":
            ai_api_key = s.openrouter_api_key
        elif s.ai_provider == "groq":
            ai_api_key = s.groq_api_key

    web_key = s.web_search_api_key or s.tavily_api_key

    ai_base = s.ai_api_base_url
    ai_model = s.ai_model
    ai_ctx = s.ai_context_length

    if not ai_base or not ai_model:
        preset = AI_PROVIDER_PRESETS.get(s.ai_provider, {})
        ai_base = ai_base or preset.get("api_base_url", "")
        ai_model = ai_model or preset.get("model", "")
        ai_ctx = ai_ctx or preset.get("context_length", 128000)

    return SettingsResponse(
        ai_provider=s.ai_provider,
        ai_api_key=ai_api_key,
        ai_api_base_url=ai_base,
        ai_model=ai_model,
        ai_context_length=ai_ctx,
        web_search_provider=s.web_search_provider,
        web_search_api_key=web_key,
        web_search_concurrency_limit=s.web_search_concurrency_limit,
        web_search_advanced=s.web_search_advanced,
        web_search_topic=s.web_search_topic,
        ai_provider_presets=AI_PROVIDER_PRESETS,
        web_provider_presets=WEB_PROVIDER_PRESETS,
    )


@router.post("/settings")
async def update_runtime_settings(payload: SettingsUpdateRequest):
    if payload.ai_provider not in AI_PROVIDER_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unsupported ai_provider: {payload.ai_provider}")

    if payload.web_search_provider not in WEB_PROVIDER_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unsupported web_search_provider: {payload.web_search_provider}")

    _ENV_FILE.parent.mkdir(parents=True, exist_ok=True)

    normalized_ai_base = (payload.ai_api_base_url or "").strip().rstrip("/")

    set_key(str(_ENV_FILE), "AI_PROVIDER", payload.ai_provider)
    set_key(str(_ENV_FILE), "AI_API_KEY", payload.ai_api_key)
    set_key(str(_ENV_FILE), "AI_API_BASE_URL", normalized_ai_base)
    set_key(str(_ENV_FILE), "AI_MODEL", payload.ai_model)
    set_key(str(_ENV_FILE), "AI_CONTEXT_LENGTH", str(payload.ai_context_length))

    set_key(str(_ENV_FILE), "WEB_SEARCH_PROVIDER", payload.web_search_provider)
    set_key(str(_ENV_FILE), "WEB_SEARCH_API_KEY", payload.web_search_api_key)
    set_key(str(_ENV_FILE), "WEB_SEARCH_CONCURRENCY_LIMIT", str(payload.web_search_concurrency_limit))
    set_key(str(_ENV_FILE), "WEB_SEARCH_ADVANCED", "true" if payload.web_search_advanced else "false")
    set_key(str(_ENV_FILE), "WEB_SEARCH_TOPIC", payload.web_search_topic)

    if payload.ai_provider == "openrouter":
        set_key(str(_ENV_FILE), "OPENROUTER_API_KEY", payload.ai_api_key)
        set_key(str(_ENV_FILE), "OPENROUTER_BASE_URL", normalized_ai_base)
    elif payload.ai_provider == "groq":
        set_key(str(_ENV_FILE), "GROQ_API_KEY", payload.ai_api_key)
        set_key(str(_ENV_FILE), "GROQ_BASE_URL", normalized_ai_base)
    elif payload.ai_provider == "openai":
        set_key(str(_ENV_FILE), "OPENAI_API_KEY", payload.ai_api_key)
    elif payload.ai_provider == "gemini":
        set_key(str(_ENV_FILE), "GOOGLE_API_KEY", payload.ai_api_key)
    elif payload.ai_provider == "deepseek":
        set_key(str(_ENV_FILE), "DEEPSEEK_API_KEY", payload.ai_api_key)
    elif payload.ai_provider == "grok":
        set_key(str(_ENV_FILE), "GROK_API_KEY", payload.ai_api_key)

    if payload.web_search_provider == "tavily":
        set_key(str(_ENV_FILE), "TAVILY_API_KEY", payload.web_search_api_key)

    updated = reload_settings()

    return {
        "ok": True,
        "message": "Settings saved and reloaded",
        "ai_provider": updated.ai_provider,
        "web_search_provider": updated.web_search_provider,
        "ai_model": updated.ai_model,
        "ai_api_base_url": updated.ai_api_base_url,
    }
