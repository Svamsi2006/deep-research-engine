/**
 * Module-level in-memory source store.
 * Lives for the duration of a Vercel serverless instance.
 * Shared across route handlers within the same instance via Node.js module cache.
 */

export interface SourceRecord {
    source_id: string;
    title: string;
    content: string;
    char_count: number;
    chunk_count: number;
}

// Single shared Map — Node module cache keeps this alive across requests
// within the same warm serverless instance.
export const sourceStore = new Map<string, SourceRecord>();
