/**
 * POST /api/ingest — Transparent pass-through to the Python backend.
 *
 * In development the Next.js rewrite in next.config.js already proxies
 * /api/* → http://localhost:8000/api/* so this route file is not even
 * reached. It exists only as a safety fallback for environments where
 * the rewrite may not apply (e.g. some edge runtimes).
 *
 * All real ingest logic (PDF parsing, URL scraping, chunking, embedding)
 * lives in the Python FastAPI backend at /api/ingest.
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: NextRequest) {
    const backendUrl = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
    const targetUrl = `${backendUrl}/api/ingest`;

    try {
        const body = await request.text();
        const response = await fetch(targetUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body,
            signal: AbortSignal.timeout(55000),
        });

        const data = await response.json();
        return NextResponse.json(data, { status: response.status });
    } catch (e) {
        return NextResponse.json(
            {
                detail: `Failed to reach backend at ${backendUrl}. Is the Python server running? Error: ${String(e)}`,
            },
            { status: 502 }
        );
    }
}
