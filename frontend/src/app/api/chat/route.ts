/**
 * Next.js API route — proxies POST /api/chat to the FastAPI backend.
 * Streams the SSE response back to the browser so the rewrite is no
 * longer needed and Vercel deployments work without CORS issues.
 */

export const runtime = "edge"; // use edge runtime for streaming support

const BACKEND_URL =
  process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: Request) {
  const body = await request.json();

  const upstream = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return new Response(text, { status: upstream.status });
  }

  // Forward the SSE stream as-is
  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
