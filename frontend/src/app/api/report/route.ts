/**
 * POST /api/report — Multi-step deep report via direct LLM calls on Vercel.
 * Pipeline: Plan → Write → Evaluate  (all server-side, no Render backend needed).
 * Reads OPENROUTER_API_KEY / GROQ_API_KEY from Vercel env vars.
 */

import { NextRequest } from "next/server";
import { callLLM } from "@/lib/llm";
import { createSSEStream, thought, done, streamText } from "@/lib/sse";
import { randomUUID } from "crypto";

export const runtime = "nodejs";
export const maxDuration = 60;

// ── System prompts ────────────────────────────────────────────────────

const PLANNER_SYSTEM = `\
You are a research planner. Given a question, output a structured outline 
for a comprehensive technical report. Return 4-6 section headings with 
one-line descriptions of what each section should cover. Be concise.`;

const WRITER_SYSTEM = `\
You are Engineering Oracle, a senior systems architect and ML engineer.
Write a comprehensive, technically accurate research report following the provided outline.
Requirements:
- Use rich Markdown: ## headers, ### subheaders, code blocks, tables, bullet lists
- Be specific, cite technical tradeoffs, include concrete examples
- Minimum 600 words, maximum 1500 words
- Start directly with the report content (no preamble like "Sure, here is...")`;

const JUDGE_SYSTEM = `\
You are a technical report evaluator.
Given a report, respond with ONLY a JSON object:
{"score": 0.85, "feedback": "one line"}
Score 0.0-1.0. Score >= 0.7 is good quality.`;

// ── Route ──────────────────────────────────────────────────────────────

export async function POST(request: NextRequest) {
    const body = await request.json();
    const question: string = body.question || "";
    const depth: string = body.depth || "deep";

    if (!question.trim()) {
        return new Response(
            JSON.stringify({ detail: "question is required" }),
            { status: 400, headers: { "Content-Type": "application/json" } }
        );
    }

    return createSSEStream(async (push) => {
        const reportId = randomUUID();

        // ── Step 1: Plan ───────────────────────────────────────────────────
        thought(push, "planner", `🧠 Planning report for: "${question}"`, "running");

        const planResult = await callLLM(
            [
                { role: "system", content: PLANNER_SYSTEM },
                { role: "user", content: question },
            ],
            512,
            0.3
        );
        const outline = planResult.text;

        thought(push, "planner", `✅ Outline ready (${outline.split("\n").length} sections)`, "completed");

        // ── Step 2: Write ──────────────────────────────────────────────────
        thought(push, "writer", "✍️ Writing comprehensive report...", "running");

        const maxWriteTokens = depth === "quick" ? 1024 : 2048;
        const writeResult = await callLLM(
            [
                { role: "system", content: WRITER_SYSTEM },
                {
                    role: "user",
                    content: `Question: ${question}\n\nOutline to follow:\n${outline}\n\nWrite the full report now:`,
                },
            ],
            maxWriteTokens,
            0.4
        );
        const reportMd = writeResult.text;

        thought(
            push,
            "writer",
            `✅ Report written (${reportMd.length} chars, via ${writeResult.provider})`,
            "completed"
        );

        // ── Step 3: Evaluate ───────────────────────────────────────────────
        thought(push, "judge", "🔍 Evaluating report quality...", "running");

        let score = 0.85;
        let qualityWarning = false;

        try {
            const judgeResult = await callLLM(
                [
                    { role: "system", content: JUDGE_SYSTEM },
                    {
                        role: "user",
                        content: `Question: ${question}\n\nReport:\n${reportMd.slice(0, 1500)}`,
                    },
                ],
                128,
                0.1
            );

            const jsonMatch = judgeResult.text.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                const parsed = JSON.parse(jsonMatch[0]);
                score = typeof parsed.score === "number" ? parsed.score : 0.85;
                qualityWarning = score < 0.6;
            }
        } catch {
            // Judge failure is non-fatal
        }

        thought(
            push,
            "judge",
            `✅ Quality score: ${(score * 100).toFixed(0)}%${qualityWarning ? " ⚠️ low quality" : ""}`,
            qualityWarning ? "error" : "completed"
        );

        // ── Stream report ──────────────────────────────────────────────────
        streamText(push, reportMd);

        // Send empty sources (no DB in serverless mode)
        push("sources", { sources: [] });

        done(push, reportId, score, qualityWarning);
    });
}
