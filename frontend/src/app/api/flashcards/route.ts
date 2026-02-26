/**
 * POST /api/flashcards — Generate flashcards from report content via direct LLM call.
 * No Render backend needed. Reads API keys from Vercel env vars.
 */

import { NextRequest } from "next/server";
import { callLLM } from "@/lib/llm";
import { createSSEStream, thought, done } from "@/lib/sse";
import { randomUUID } from "crypto";

export const runtime = "nodejs";
export const maxDuration = 60;

const FLASHCARD_SYSTEM = `\
You are an expert educator. Generate flashcards from the provided report.
Return ONLY valid JSON — an array of flashcard objects. Nothing else before or after the JSON.
Each flashcard must have:
  "front": string (question/term, max 120 chars)
  "back": string (answer/definition, max 300 chars)
  "tags": string[] (2-4 topic tags)
  "source_citations": string[] (leave empty [])

Generate 8-12 cards covering the most important concepts.
Example: [{"front":"What is X?","back":"X is...","tags":["topic"],"source_citations":[]}]`;

export async function POST(request: NextRequest) {
    const body = await request.json();
    const reportMd: string = body.report_md || "";
    const question: string = body.question || "";
    const reportId: string = body.report_id || randomUUID();

    if (!reportMd.trim()) {
        return new Response(
            JSON.stringify({ detail: "report_md is required" }),
            { status: 400, headers: { "Content-Type": "application/json" } }
        );
    }

    return createSSEStream(async (push) => {
        thought(push, "flashcards", "🃏 Generating flashcards from report...", "running");

        const result = await callLLM(
            [
                { role: "system", content: FLASHCARD_SYSTEM },
                {
                    role: "user",
                    content: `Topic: ${question}\n\nReport content:\n${reportMd.slice(0, 3000)}`,
                },
            ],
            1024,
            0.4
        );

        // Parse JSON from LLM response
        let cards: object[] = [];
        try {
            const match = result.text.match(/\[[\s\S]*\]/);
            if (match) {
                cards = JSON.parse(match[0]);
            }
        } catch {
            // Fallback: try to parse entire response
            try {
                cards = JSON.parse(result.text);
            } catch {
                cards = [];
            }
        }

        if (cards.length === 0) {
            push("error", { message: "Could not parse flashcards from LLM response. Try again.", node: "flashcards" });
            done(push, reportId, 0);
            return;
        }

        thought(push, "flashcards", `✅ Generated ${cards.length} flashcards`, "completed");

        // Build CSV
        const csvRows = [
            "front,back,tags,source_citations",
            ...cards.map((c: unknown) => {
                const card = c as { front?: string; back?: string; tags?: string[]; source_citations?: string[] };
                const front = (card.front || "").replace(/"/g, '""');
                const back = (card.back || "").replace(/"/g, '""');
                const tags = (card.tags || []).join(";");
                return `"${front}","${back}","${tags}",""`;
            }),
        ];
        const csv = csvRows.join("\n");

        push("flashcards", {
            cards,
            csv,
            count: cards.length,
        });

        done(push, reportId);
    });
}
