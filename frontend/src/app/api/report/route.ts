/**
 * Next.js API route — proxies /api/report to FastAPI backend.
 */

import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 120; // Deep report can take time

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
    const body = await request.json();

    const upstream = await fetch(`${BACKEND_URL}/api/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!upstream.ok) {
        const text = await upstream.text();
        return new Response(text, { status: upstream.status });
    }

    return new Response(upstream.body, {
        status: 200,
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
        },
    });
}
