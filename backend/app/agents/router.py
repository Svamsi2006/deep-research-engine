"""Brain Router — classifies user intent and routes to the correct agent.

Uses a fast LLM call to determine if the query should be handled by:
  - chat:     Simple greetings, general Q&A, basic questions
  - research: Deep technical analysis, benchmarks, comparisons
  - pdf:      When user has uploaded a PDF for analysis
"""

from __future__ import annotations

import json
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

ROUTER_SYSTEM = """\
You are a query classifier. Given a user message, classify its intent into exactly ONE of these categories:

- "chat": Greetings (hi, hello), simple questions, general knowledge, coding help, casual conversation
- "research": Deep technical comparisons, benchmark analysis, architecture reviews, market research, anything needing web search and multiple sources

Respond with ONLY a JSON object: {"intent": "chat"} or {"intent": "research"}
Do NOT include any other text, explanation, or markdown. Just the JSON object.
"""


def classify_intent(query: str, has_pdf: bool = False) -> str:
    """
    Classify the user's query intent.

    Returns one of: "chat", "research", "pdf"
    """
    # If a PDF is attached, always route to PDF agent
    if has_pdf:
        logger.info(f"Router: PDF attached → pdf agent")
        return "pdf"

    settings = get_settings()

    from openai import OpenAI

    client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )

    try:
        response = client.chat.completions.create(
            model=settings.model_router,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM},
                {"role": "user", "content": query},
            ],
            max_tokens=50,
            temperature=0.0,
        )

        raw = response.choices[0].message.content or '{"intent": "chat"}'
        raw = raw.strip()

        # Try to parse JSON
        try:
            # Handle cases where model wraps in markdown
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)
            intent = result.get("intent", "chat")
        except (json.JSONDecodeError, KeyError):
            # Fallback: look for keywords in raw response
            raw_lower = raw.lower()
            if "research" in raw_lower:
                intent = "research"
            else:
                intent = "chat"

        # Validate
        if intent not in ("chat", "research"):
            intent = "chat"

        logger.info(f"Router: \"{query[:60]}\" → {intent} agent")
        return intent

    except Exception as e:
        logger.warning(f"Router classification failed: {e}, defaulting to chat")
        return "chat"
