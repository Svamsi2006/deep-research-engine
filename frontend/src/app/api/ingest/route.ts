/**
 * POST /api/ingest — Ingest URL/text/GitHub sources entirely on Vercel.
 * Fetches URL content server-side, chunks it, stores in module-level Map.
 * Returns a source_id usable in the same serverless instance session.
 * No Render backend needed.
 */

import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "crypto";
import { sourceStore, type SourceRecord } from "@/lib/source-store";

export const runtime = "nodejs";
export const maxDuration = 60;

// sourceStore is imported from @/lib/source-store
// (module-level Map, lives for the duration of the warm serverless instance)

// ---------------------------------------------------------------------------
// Text extraction helpers
// ---------------------------------------------------------------------------

function stripHtml(html: string): string {
    return html
        .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, " ")
        .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/&nbsp;/g, " ")
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/\s{2,}/g, " ")
        .trim();
}

function extractTitle(html: string, fallback: string): string {
    const match = html.match(/<title[^>]*>([^<]+)<\/title>/i);
    return match ? match[1].trim() : fallback;
}

function chunkText(text: string, chunkSize = 600): string[] {
    const chunks: string[] = [];
    const words = text.split(/\s+/);
    let current = "";
    for (const word of words) {
        if ((current + " " + word).trim().length > chunkSize) {
            if (current.trim()) chunks.push(current.trim());
            current = word;
        } else {
            current = (current + " " + word).trim();
        }
    }
    if (current.trim()) chunks.push(current.trim());
    return chunks;
}

async function fetchUrl(url: string): Promise<{ title: string; content: string }> {
    const response = await fetch(url, {
        headers: {
            "User-Agent":
                "Mozilla/5.0 (compatible; DeepResearchBot/1.0; +https://deep-research-engine.vercel.app)",
            Accept: "text/html,application/xhtml+xml,text/plain",
        },
        signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch URL (${response.status}): ${url}`);
    }

    const contentType = response.headers.get("content-type") || "";
    const rawText = await response.text();

    if (contentType.includes("text/html")) {
        return {
            title: extractTitle(rawText, new URL(url).hostname),
            content: stripHtml(rawText),
        };
    }

    // Plain text / markdown / JSON
    return {
        title: new URL(url).pathname.split("/").pop() || url,
        content: rawText,
    };
}

async function fetchGitHub(url: string): Promise<{ title: string; content: string }> {
    // Convert github.com URL to raw content URL
    // e.g. https://github.com/owner/repo/blob/main/README.md
    //   → https://raw.githubusercontent.com/owner/repo/main/README.md
    const rawUrl = url
        .replace("https://github.com/", "https://raw.githubusercontent.com/")
        .replace("/blob/", "/");

    const response = await fetch(rawUrl, {
        signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
        // Fallback: try the normal URL as plain page
        return fetchUrl(url);
    }

    const content = await response.text();
    const title = url.split("/").pop() || "GitHub file";
    return { title, content };
}

async function decodePdf(base64: string, fileName: string): Promise<{ title: string; content: string }> {
    // Basic PDF text extraction: look for text streams between BT/ET markers.
    // This is a lightweight fallback — for full PDF parsing, use a dedicated service.
    try {
        const buffer = Buffer.from(base64, "base64");
        const pdfText = buffer.toString("latin1");

        // Extract text between BT and ET markers (basic PDF text extraction)
        const textChunks: string[] = [];
        const btEtRegex = /BT([\s\S]*?)ET/g;
        let match: RegExpExecArray | null;
        while ((match = btEtRegex.exec(pdfText)) !== null) {
            // Extract strings in parentheses or hex strings
            const block = match[1];
            const strMatches = block.match(/\(([^)]*)\)/g) || [];
            const text = strMatches
                .map((s) => s.slice(1, -1))
                .join(" ")
                .replace(/\\n/g, "\n")
                .replace(/\\r/g, "")
                .trim();
            if (text.length > 2) textChunks.push(text);
        }

        const content = textChunks.join(" ").replace(/\s{2,}/g, " ").trim();

        if (content.length < 50) {
            // Could not extract meaningful text
            return {
                title: fileName,
                content: `[PDF: ${fileName}] — Could not extract text from this PDF. Please copy the text content and paste it as a URL or plain text source.`,
            };
        }

        return { title: fileName.replace(/\.pdf$/i, ""), content };
    } catch {
        return {
            title: fileName,
            content: `[PDF: ${fileName}] — Text extraction failed. Use the URL source type instead.`,
        };
    }
}

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------

export async function POST(request: NextRequest) {
    const body = await request.json();
    const sourceType: string = body.source_type || "url";
    const payload: string = body.payload || "";
    const fileName: string = body.file_name || "document.pdf";

    if (!payload.trim()) {
        return NextResponse.json({ detail: "payload is required" }, { status: 400 });
    }

    try {
        let title = "";
        let content = "";

        if (sourceType === "url") {
            const fetched = await fetchUrl(payload);
            title = fetched.title;
            content = fetched.content;
        } else if (sourceType === "github") {
            const fetched = await fetchGitHub(payload);
            title = fetched.title;
            content = fetched.content;
        } else if (sourceType === "pdf") {
            const fetched = await decodePdf(payload, fileName);
            title = fetched.title;
            content = fetched.content;
        } else {
            return NextResponse.json(
                { detail: `Unknown source_type: ${sourceType}` },
                { status: 400 }
            );
        }

        if (!content.trim()) {
            return NextResponse.json({ detail: "Could not extract content from source." }, { status: 422 });
        }

        // Limit content to 50k chars to keep memory sane
        content = content.slice(0, 50000);

        const chunks = chunkText(content, 600);
        const sourceId = randomUUID();

        const record: SourceRecord = {
            source_id: sourceId,
            title: title.slice(0, 200),
            content,
            char_count: content.length,
            chunk_count: chunks.length,
        };

        sourceStore.set(sourceId, record);

        return NextResponse.json({
            source_id: sourceId,
            title: record.title,
            char_count: record.char_count,
            chunk_count: record.chunk_count,
        });
    } catch (e: unknown) {
        return NextResponse.json(
            { detail: `Ingest failed: ${String(e)}` },
            { status: 500 }
        );
    }
}
