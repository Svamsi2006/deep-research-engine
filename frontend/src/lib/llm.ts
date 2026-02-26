/**
 * LLM Gateway — runs entirely on Vercel serverless.
 * Tries OpenRouter (free models) first, falls back to Groq.
 * Reads API keys from server-side env vars (set in Vercel Dashboard).
 */

import OpenAI from "openai";

export interface LLMMessage {
    role: "system" | "user" | "assistant";
    content: string;
}

export interface LLMResult {
    text: string;
    model: string;
    provider: "openrouter" | "groq";
}

const OPENROUTER_KEY = process.env.OPENROUTER_API_KEY || "";
const GROQ_KEY = process.env.GROQ_API_KEY || "";
const OPENROUTER_MODEL = process.env.OPENROUTER_MODEL || "deepseek/deepseek-chat-v3-0324:free";
const GROQ_MODEL = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";

async function callOpenRouter(
    messages: LLMMessage[],
    maxTokens: number,
    temperature: number
): Promise<LLMResult> {
    const client = new OpenAI({
        baseURL: "https://openrouter.ai/api/v1",
        apiKey: OPENROUTER_KEY,
        defaultHeaders: {
            "HTTP-Referer": "https://deep-research-engine.vercel.app",
            "X-Title": "Deep Research Engine",
        },
    });

    const res = await client.chat.completions.create({
        model: OPENROUTER_MODEL,
        messages,
        max_tokens: maxTokens,
        temperature,
    });

    return {
        text: res.choices[0]?.message?.content ?? "",
        model: res.model || OPENROUTER_MODEL,
        provider: "openrouter",
    };
}

async function callGroq(
    messages: LLMMessage[],
    maxTokens: number,
    temperature: number
): Promise<LLMResult> {
    const client = new OpenAI({
        baseURL: "https://api.groq.com/openai/v1",
        apiKey: GROQ_KEY,
    });

    const res = await client.chat.completions.create({
        model: GROQ_MODEL,
        messages,
        max_tokens: maxTokens,
        temperature,
    });

    return {
        text: res.choices[0]?.message?.content ?? "",
        model: GROQ_MODEL,
        provider: "groq",
    };
}

/**
 * Call an LLM with automatic failover: OpenRouter → Groq.
 * Throws only if both providers fail.
 */
export async function callLLM(
    messages: LLMMessage[],
    maxTokens = 2048,
    temperature = 0.35
): Promise<LLMResult> {
    const errors: string[] = [];

    if (OPENROUTER_KEY) {
        for (let attempt = 0; attempt < 2; attempt++) {
            try {
                return await callOpenRouter(messages, maxTokens, temperature);
            } catch (e: unknown) {
                const msg = String(e);
                errors.push(`OpenRouter attempt ${attempt + 1}: ${msg}`);
                const retryable = ["429", "500", "502", "503", "timeout"].some((c) =>
                    msg.includes(c)
                );
                if (!retryable) break;
                if (attempt === 0) await sleep(800);
            }
        }
    }

    if (GROQ_KEY) {
        try {
            return await callGroq(messages, maxTokens, temperature);
        } catch (e: unknown) {
            errors.push(`Groq: ${e}`);
        }
    }

    throw new Error(
        errors.length
            ? `All LLM providers failed:\n${errors.join("\n")}`
            : "No LLM API keys configured. Add OPENROUTER_API_KEY or GROQ_API_KEY in Vercel environment variables."
    );
}

function sleep(ms: number) {
    return new Promise((r) => setTimeout(r, ms));
}
