/**
 * SSE client for the Deep Research Platform.
 * Supports /api/answer, /api/report, /api/flashcards, and /api/ingest.
 *
 * All requests use RELATIVE paths (e.g. /api/answer) so they are
 * proxied through the Next.js API routes on the Vercel deployment.
 * Never use NEXT_PUBLIC_API_URL here — that would bypass the proxy
 * and send requests directly from the browser to the Render backend,
 * which breaks on the deployed site (localhost:8000 doesn't exist there).
 */

export interface ThoughtEvent {
  node: string;
  message: string;
  status: "running" | "completed" | "error" | "pending";
  timestamp: string;
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

export interface SourceInfo {
  source_id: string;
  title: string;
}

export interface FlashcardData {
  front: string;
  back: string;
  tags: string[];
  source_citations: string[];
}

export interface FlashcardsEvent {
  cards: FlashcardData[];
  csv: string;
  count: number;
}

export interface NeedMoreSourcesEvent {
  message: string;
}

export interface SSECallbacks {
  onThought: (event: ThoughtEvent) => void;
  onReportChunk: (chunk: ReportChunk) => void;
  onDone: (event: DoneEvent) => void;
  onError: (error: string) => void;
  onSources?: (sources: SourceInfo[]) => void;
  onFlashcards?: (event: FlashcardsEvent) => void;
  onNeedMoreSources?: (event: NeedMoreSourcesEvent) => void;
}

async function streamSSE(
  url: string,
  body: Record<string, unknown>,
  callbacks: SSECallbacks,
  signal?: AbortSignal
): Promise<void> {
  // Use url as-is (relative path like /api/answer) — goes through Vercel proxy
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

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
              case "sources":
                callbacks.onSources?.(parsed.sources as SourceInfo[]);
                break;
              case "flashcards":
                callbacks.onFlashcards?.(parsed as FlashcardsEvent);
                break;
              case "need_more_sources":
                callbacks.onNeedMoreSources?.(parsed as NeedMoreSourcesEvent);
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

// ── Public API ────────────────────────────────────────────────────────

export function streamAnswer(
  question: string,
  sourceIds: string[],
  callbacks: SSECallbacks,
  signal?: AbortSignal
) {
  return streamSSE("/api/answer", { question, source_ids: sourceIds, allow_web_search: false }, callbacks, signal);
}

export function streamReport(
  question: string,
  sourceIds: string[],
  depth: "quick" | "deep",
  allowWebSearch: boolean,
  callbacks: SSECallbacks,
  signal?: AbortSignal
) {
  return streamSSE(
    "/api/report",
    { question, source_ids: sourceIds, depth, allow_web_search: allowWebSearch },
    callbacks,
    signal
  );
}

export function streamFlashcards(
  reportId: string,
  reportMd: string,
  question: string,
  callbacks: SSECallbacks,
  signal?: AbortSignal
) {
  return streamSSE(
    "/api/flashcards",
    { report_id: reportId, report_md: reportMd, question },
    callbacks,
    signal
  );
}

// ── Ingest (non-SSE) ──────────────────────────────────────────────────

export interface IngestResult {
  source_id: string;
  title: string;
  char_count: number;
  chunk_count: number;
}

export async function ingestSource(
  sourceType: "pdf" | "url" | "github",
  payload: string,
  fileName?: string
): Promise<IngestResult> {
  // Use relative path — goes through Vercel /api/ingest proxy
  const response = await fetch("/api/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_type: sourceType,
      payload,
      file_name: fileName,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Ingest failed (${response.status}): ${text}`);
  }

  return response.json();
}
