/**
 * Next.js API route — proxies all /api/* requests to the FastAPI backend.
 * Supports: /api/answer, /api/report, /api/flashcards, /api/ingest
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 120; // 2 min timeout for deep report pipeline

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

export async function POST(request: NextRequest) {
  const body = await request.json();

  // Extract the path from the URL (e.g., /api/chat -> /api/chat)
  const url = new URL(request.url);
  const path = url.pathname; // /api/chat, /api/answer, etc.

  const upstream = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return new Response(text, { status: upstream.status });
  }

  // Check if response is SSE (streaming)
  const contentType = upstream.headers.get("content-type") || "";

  if (contentType.includes("text/event-stream")) {
    return new Response(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
      },
    });
  }

  // Non-SSE response (e.g., /api/ingest returns JSON)
  const data = await upstream.json();
  return NextResponse.json(data);
}
