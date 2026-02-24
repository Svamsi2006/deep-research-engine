/**
 * SSE client for connecting to the Engineering Oracle backend.
 */

export interface ThoughtEvent {
  node: string;
  message: string;
  status: "running" | "completed" | "error";
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface ReportChunk {
  content: string;
  done: boolean;
}

export interface DoneEvent {
  report_id: string;
  evaluation_score: number;
  retry_count: number;
  quality_warning: boolean;
}

export interface SSECallbacks {
  onThought: (event: ThoughtEvent) => void;
  onReportChunk: (chunk: ReportChunk) => void;
  onDone: (event: DoneEvent) => void;
  onError: (error: string) => void;
}

export async function streamChat(
  query: string,
  callbacks: SSECallbacks,
  signal?: AbortSignal
): Promise<void> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "";

  const response = await fetch(`${apiUrl}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, stream: true }),
    signal,
  });

  if (!response.ok) {
    const text = await response.text();
    callbacks.onError(`API error ${response.status}: ${text}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events from buffer
      const lines = buffer.split("\n");
      buffer = lines.pop() || ""; // Keep incomplete line in buffer

      let currentEvent = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ") && currentEvent) {
          const data = line.slice(6);
          try {
            const parsed = JSON.parse(data);

            switch (currentEvent) {
              case "thought":
                callbacks.onThought(parsed as ThoughtEvent);
                break;
              case "report":
                callbacks.onReportChunk(parsed as ReportChunk);
                break;
              case "done":
                callbacks.onDone(parsed as DoneEvent);
                break;
              case "error":
                callbacks.onError(parsed.message || "Unknown error");
                break;
            }
          } catch {
            // Skip malformed JSON
          }
          currentEvent = "";
        } else if (line === "") {
          currentEvent = "";
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
