/**
 * POST /api/answer — Quick answer via direct LLM call on Vercel.
 * No backend needed. Reads OPENROUTER_API_KEY / GROQ_API_KEY from env.
 */

import { NextRequest } from "next/server";
import { callLLM } from "@/lib/llm";
import { createSSEStream, thought, done, streamText } from "@/lib/sse";
import { randomUUID } from "crypto";

export const runtime = "nodejs";
export const maxDuration = 60;

const SYSTEM_PROMPT = `\
You are Engineering Oracle, a senior systems architect and ML engineer.
Provide helpful, technically accurate, and concise answers.
Use Markdown: headers, code blocks, bullet points, tables.
If the question needs deep multi-source research, suggest using "Deep Report" mode.`;

export async function POST(request: NextRequest) {
    const body = await request.json();
    const question: string = body.question || "";

    if (!question.trim()) {
        return new Response(
            JSON.stringify({ detail: "question is required" }),
            { status: 400, headers: { "Content-Type": "application/json" } }
        );
    }

    return createSSEStream(async (push) => {
        const reportId = randomUUID();

        thought(push, "answer", "⚡ Generating quick answer...", "running");

        const result = await callLLM(
            [
                { role: "system", content: SYSTEM_PROMPT },
                { role: "user", content: question },
            ],
            2048,
            0.5
        );

        thought(
            push,
            "answer",
            `✅ Response ready (${result.text.length} chars, via ${result.provider}/${result.model})`,
            "completed"
        );

        streamText(push, result.text);
        done(push, reportId);
    });
}
