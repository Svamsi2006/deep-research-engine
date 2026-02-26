/**
 * SSE streaming helper for Next.js route handlers.
 * Wraps any async function in a proper text/event-stream ReadableStream response.
 */

const encoder = new TextEncoder();

export type SSEPush = (event: string, data: Record<string, unknown>) => void;

function sseChunk(event: string, data: Record<string, unknown>): Uint8Array {
    return encoder.encode(
        `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
    );
}

/** Thought event helper. */
export function thought(
    push: SSEPush,
    node: string,
    message: string,
    status: "running" | "completed" | "error" = "running"
) {
    push("thought", {
        node,
        message,
        status,
        timestamp: new Date().toISOString(),
    });
}

/** Done event helper. */
export function done(
    push: SSEPush,
    reportId: string,
    score = 1.0,
    qualityWarning = false
) {
    push("done", {
        report_id: reportId,
        evaluation_score: score,
        retry_count: 0,
        quality_warning: qualityWarning,
    });
}

/** Stream text as chunked SSE report events. */
export function streamText(push: SSEPush, text: string, chunkSize = 150) {
    for (let i = 0; i < text.length; i += chunkSize) {
        push("report", {
            content: text.slice(i, i + chunkSize),
            done: i + chunkSize >= text.length,
        });
    }
}

/**
 * Wraps an async function in an SSE response.
 * Any uncaught error is forwarded as an `error` SSE event.
 */
export function createSSEStream(
    fn: (push: SSEPush) => Promise<void>
): Response {
    const stream = new ReadableStream({
        async start(controller) {
            const push: SSEPush = (event, data) => {
                controller.enqueue(sseChunk(event, data));
            };

            try {
                await fn(push);
            } catch (e: unknown) {
                push("error", { message: String(e), node: "server" });
            } finally {
                controller.close();
            }
        },
    });

    return new Response(stream, {
        status: 200,
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
        },
    });
}
