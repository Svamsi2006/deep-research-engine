"""Optimized LLM model routing for different research tasks.

Strategy:
- Planner/Router: Fast, cheap models (gpt-4o-mini, Groq llama-3.3)
- Reasoning: Strong reasoning (claude-opus, llama-3.3-70b)
- Writing: Balanced (gpt-4o, llama-3.1-405b) 
- Judge: Fast evaluation (gpt-4o-mini, Groq)
- Synthesis: Creative (gpt-4 turbo)
"""

from app.config import get_settings

# Model profiles optimized for different tasks
PROFILE_PLANNER = {
    "name": "Planner",
    "priority": ["openrouter/meta-llama/llama-3.3-70b-instruct:free", "groq/llama-3.3-70b-versatile"],
    "max_tokens": 512,
    "temperature": 0.2,
    "timeout_secs": 15,
}

PROFILE_REASONING = {
    "name": "Reasoning",
    "priority": ["openrouter/meta-llama/llama-3.3-70b-instruct:free", "groq/llama-3.3-70b-versatile"],
    "max_tokens": 2000,
    "temperature": 0.3,
    "timeout_secs": 45,
}

PROFILE_WRITING = {
    "name": "Writing",
    "priority": ["openrouter/meta-llama/llama-3.3-70b-instruct:free", "groq/llama-3.3-70b-versatile"],
    "max_tokens": 3000,
    "temperature": 0.5,
    "timeout_secs": 60,
}

PROFILE_JUDGE = {
    "name": "Judge",
    "priority": ["openrouter/meta-llama/llama-3.3-70b-instruct:free", "groq/llama-3.3-70b-versatile"],
    "max_tokens": 1000,
    "temperature": 0.1,
    "timeout_secs": 20,
}

PROFILE_SYNTHESIS = {
    "name": "Synthesis",
    "priority": ["openrouter/meta-llama/llama-3.3-70b-instruct:free", "groq/llama-3.3-70b-versatile"],
    "max_tokens": 1500,
    "temperature": 0.4,
    "timeout_secs": 30,
}

PROFILE_ANSWER = {
    "name": "Answer",
    "priority": ["openrouter/meta-llama/llama-3.3-70b-instruct:free", "groq/llama-3.3-70b-versatile"],
    "max_tokens": 1500,
    "temperature": 0.5,
    "timeout_secs": 30,
}

# Map purposes to profiles
PROFILE_MAP = {
    "planner": PROFILE_PLANNER,
    "reasoning": PROFILE_REASONING,
    "writing": PROFILE_WRITING,
    "judge": PROFILE_JUDGE,
    "synthesis": PROFILE_SYNTHESIS,
    "answer": PROFILE_ANSWER,
    "discovery": PROFILE_REASONING,
    "harvest": PROFILE_WRITING,
    "clean": PROFILE_WRITING,
    "evaluation": PROFILE_JUDGE,
}


def get_model_profile(purpose: str) -> dict:
    """Get optimized model configuration for a task."""
    return PROFILE_MAP.get(purpose, PROFILE_ANSWER)


def get_recommended_model(purpose: str) -> str:
    """Get primary model for a purpose."""
    profile = get_model_profile(purpose)
    return profile["priority"][0] if profile["priority"] else ""
