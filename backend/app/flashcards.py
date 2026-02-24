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
You are a flashcard generator for engineering study.

Given a technical report, generate flashcards that test understanding of key concepts.

Output ONLY valid JSON array (no markdown wrapping):
[
  {
    "front": "Question text",
    "back": "Answer text (concise, factual)",
    "tags": ["topic1", "topic2"],
    "source_citations": ["citation ref from report"]
  },
  ...
]

Rules:
- Generate 3-5 flashcards per major section of the report
- Front: Clear question that tests understanding (not trivia)
- Back: Concise answer with key facts/numbers
- Include comparison questions where relevant
- Include "why" questions, not just "what" questions
- Tags should reflect the topic area
"""


def generate_flashcards(report_md: str, question: str) -> list[Flashcard]:
    """Generate flashcards from a report."""
    messages = [
        {"role": "system", "content": FLASHCARD_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Original question: {question}\n\n"
                f"Report:\n{report_md[:8000]}\n\n"
                "Generate flashcards for this report."
            ),
        },
    ]

    result = call_llm(messages, purpose="flashcards", max_tokens=2048, temperature=0.3)

    try:
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        cards_data = json.loads(text)
        if not isinstance(cards_data, list):
            cards_data = [cards_data]

        cards = []
        for item in cards_data:
            cards.append(Flashcard(
                front=item.get("front", ""),
                back=item.get("back", ""),
                tags=item.get("tags", []),
                source_citations=item.get("source_citations", []),
            ))

        logger.info(f"Generated {len(cards)} flashcards")
        return cards

    except json.JSONDecodeError:
        logger.warning(f"Flashcard generation returned non-JSON: {result.text[:200]}")
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
