/**
 * Next.js API route — proxies /api/ingest to FastAPI backend (non-SSE, returns JSON).
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
    const body = await request.json();

    const upstream = await fetch(`${BACKEND_URL}/api/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!upstream.ok) {
        const text = await upstream.text();
        return new Response(text, { status: upstream.status });
    }

    const data = await upstream.json();
    return NextResponse.json(data);
}
