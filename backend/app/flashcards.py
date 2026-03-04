"""Flashcard generator — creates Q&A flashcards from a report.

Supports export as JSON and Anki-compatible CSV.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, field

from app.llm_gateway import call_llm

logger = logging.getLogger(__name__)


@dataclass
class Flashcard:
    """A single flashcard."""
    front: str
    back: str
    tags: list[str] = field(default_factory=list)
    source_citations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "front": self.front,
            "back": self.back,
            "tags": self.tags,
            "source_citations": self.source_citations,
        }


FLASHCARD_SYSTEM = """\
Generate 5-8 flashcards from the report below. Return ONLY a raw JSON array, no markdown fences:
[{"front":"Question?","back":"Concise answer.","tags":["topic"],"source_citations":["ref"]}]
Rules:
- Front: test understanding (why/how questions, not trivia)
- Back: concise factual answer (1-3 sentences)
- Tags: 1-2 topic keywords
- source_citations: reference from the report if applicable
Return ONLY the JSON array. No extra text, no code fences, no explanation.
"""


def _extract_json_array(text: str) -> list:
    """Robustly extract a JSON array from LLM output that may have markdown fences or extra text."""
    import re
    
    text = text.strip()
    
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
    
    # Try direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass
    
    # Try to find the first [ ... ] block in the text
    bracket_match = re.search(r'\[.*\]', text, re.DOTALL)
    if bracket_match:
        try:
            data = json.loads(bracket_match.group())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    
    return []


def generate_flashcards(report_md: str, question: str) -> list[Flashcard]:
    """Generate flashcards from a report."""
    messages = [
        {"role": "system", "content": FLASHCARD_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Question: {question}\n\n"
                f"Report:\n{report_md[:4000]}\n\n"
                "Generate flashcards."
            ),
        },
    ]

    result = call_llm(messages, purpose="flashcards", max_tokens=1500, temperature=0.3)

    try:
        cards_data = _extract_json_array(result.text)

        if not cards_data:
            logger.warning(f"Flashcard generation returned no parseable JSON: {result.text[:300]}")
            return []

        cards = []
        for item in cards_data:
            if not isinstance(item, dict):
                continue
            front = item.get("front", "").strip()
            back = item.get("back", "").strip()
            if not front or not back:
                continue
            cards.append(Flashcard(
                front=front,
                back=back,
                tags=item.get("tags", []),
                source_citations=item.get("source_citations", []),
            ))

        logger.info(f"Generated {len(cards)} flashcards")
        return cards

    except Exception as e:
        logger.warning(f"Flashcard parsing error: {e} — raw: {result.text[:200]}")
        return []


def flashcards_to_csv(cards: list[Flashcard]) -> str:
    """Export flashcards as Anki-compatible CSV."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t")

    for card in cards:
        tags_str = " ".join(card.tags) if card.tags else ""
        writer.writerow([card.front, card.back, tags_str])

    return output.getvalue()


def flashcards_to_json(cards: list[Flashcard]) -> list[dict]:
    """Export flashcards as JSON list."""
    return [c.to_dict() for c in cards]
