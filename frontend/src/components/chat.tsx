"use client";

import React, { useState, useRef, useCallback } from "react";
import {
  Paperclip,
  Link2,
  Globe,
  Zap,
  BookOpen,
  CreditCard,
  Loader2,
  StopCircle,
  FileText,
  X,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ingestSource, IngestResult } from "@/lib/sse-client";

interface SourceItem {
  id: string;
  title: string;
  type: "pdf" | "url" | "github";
  charCount: number;
  chunkCount: number;
}

interface ResearchInputProps {
  onAnswer: (question: string, sourceIds: string[]) => void;
  onReport: (
    question: string,
    sourceIds: string[],
    depth: "quick" | "deep",
    allowWebSearch: boolean
  ) => void;
  onFlashcards: () => void;
  isLoading: boolean;
  hasReport: boolean;
  onStop: () => void;
}

export default function ResearchInput({
  onAnswer,
  onReport,
  onFlashcards,
  isLoading,
  hasReport,
  onStop,
}: ResearchInputProps) {
  const [question, setQuestion] = useState("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [urls, setUrls] = useState("");
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [webSearch, setWebSearch] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── PDF upload ─────────────────────────────────────────────────────
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;

    setIngesting(true);
    for (const file of Array.from(files)) {
      if (!file.name.toLowerCase().endsWith(".pdf")) continue;
      if (file.size > 25 * 1024 * 1024) {
        alert(`${file.name} is too large (max 25MB)`);
        continue;
      }

      try {
        const base64 = await fileToBase64(file);
        const result = await ingestSource("pdf", base64, file.name);
        setSources((prev) => [
          ...prev,
          {
            id: result.source_id,
            title: result.title,
            type: "pdf",
            charCount: result.char_count,
            chunkCount: result.chunk_count,
          },
        ]);
      } catch (err) {
        alert(`Failed to ingest ${file.name}: ${err}`);
      }
    }
    setIngesting(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  // ── URL ingest ─────────────────────────────────────────────────────
  const handleAddUrls = useCallback(async () => {
    const urlList = urls
      .split(/[\n,]+/)
      .map((u) => u.trim())
      .filter(Boolean);
    if (!urlList.length) return;

    setIngesting(true);
    for (const url of urlList) {
      const isGithub = url.includes("github.com");
      try {
        const result = await ingestSource(isGithub ? "github" : "url", url);
        setSources((prev) => [
          ...prev,
          {
            id: result.source_id,
            title: result.title,
            type: isGithub ? "github" : "url",
            charCount: result.char_count,
            chunkCount: result.chunk_count,
          },
        ]);
      } catch (err) {
        alert(`Failed to ingest ${url}: ${err}`);
      }
    }
    setUrls("");
    setShowUrlInput(false);
    setIngesting(false);
  }, [urls]);

  const removeSource = (id: string) => {
    setSources((prev) => prev.filter((s) => s.id !== id));
  };

  const sourceIds = sources.map((s) => s.id);

  return (
    <div className="flex flex-col h-full">
      {/* Question */}
      <div className="p-4 space-y-3">
        <textarea
          data-tour="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a deep engineering research question..."
          rows={3}
          disabled={isLoading}
          className={cn(
            "w-full resize-none rounded-lg bg-muted border border-border px-3 py-2.5",
            "text-sm text-foreground placeholder:text-muted-foreground",
            "focus:outline-none focus:ring-1 focus:ring-ring",
          )}
        />

        {/* Attach buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            data-tour="attach-pdf"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading || ingesting}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium bg-muted/50 border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <Paperclip className="w-3.5 h-3.5" />
            Attach PDF
          </button>

          <button
            data-tour="paste-urls"
            onClick={() => setShowUrlInput(!showUrlInput)}
            disabled={isLoading || ingesting}
            className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium bg-muted/50 border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <Link2 className="w-3.5 h-3.5" />
            Paste URLs
          </button>

          <label data-tour="web-search" className="flex items-center gap-1.5 ml-auto text-xs text-muted-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={webSearch}
              onChange={(e) => setWebSearch(e.target.checked)}
              disabled={isLoading}
              className="rounded"
            />
            <Globe className="w-3 h-3" />
            Web search
          </label>
        </div>

        {/* URL input */}
        {showUrlInput && (
          <div className="flex gap-2">
            <textarea
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              placeholder="Paste URLs (one per line or comma-separated)&#10;e.g. https://arxiv.org/abs/... or https://github.com/..."
              rows={2}
              className="flex-1 resize-none rounded-lg bg-muted border border-border px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <button
              onClick={handleAddUrls}
              disabled={!urls.trim() || ingesting}
              className="rounded-lg px-3 py-1 text-xs font-medium bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Ingesting spinner */}
        {ingesting && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            Processing sources...
          </div>
        )}

        {/* Sources list */}
        {sources.length > 0 && (
          <div className="space-y-1">
            <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
              Sources ({sources.length})
            </span>
            {sources.map((s) => (
              <div
                key={s.id}
                className="flex items-center gap-2 rounded-md bg-muted/50 border border-border/50 px-2.5 py-1.5 text-xs"
              >
                <FileText className="w-3 h-3 text-blue-400 shrink-0" />
                <span className="truncate flex-1 text-foreground">{s.title}</span>
                <span className="text-muted-foreground shrink-0">
                  {s.chunkCount} chunks
                </span>
                <button
                  onClick={() => removeSource(s.id)}
                  className="p-0.5 hover:bg-red-500/20 rounded text-muted-foreground hover:text-red-400"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="px-4 pb-3 flex gap-2">
        {isLoading ? (
          <button
            onClick={onStop}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-red-500/20 border border-red-500/40 py-2 text-sm font-medium text-red-400 hover:bg-red-500/30 transition-colors"
          >
            <StopCircle className="w-4 h-4" />
            Stop
          </button>
        ) : (
          <>
            <button
              data-tour="btn-answer"
              onClick={() => onAnswer(question, sourceIds)}
              disabled={!question.trim()}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-amber-500/20 border border-amber-500/40 py-2 text-xs font-medium text-amber-400 hover:bg-amber-500/30 transition-colors disabled:opacity-40"
            >
              <Zap className="w-3.5 h-3.5" />
              Answer
            </button>
            <button
              data-tour="btn-report"
              onClick={() => onReport(question, sourceIds, "deep", webSearch)}
              disabled={!question.trim()}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-violet-500/20 border border-violet-500/40 py-2 text-xs font-medium text-violet-400 hover:bg-violet-500/30 transition-colors disabled:opacity-40"
            >
              <BookOpen className="w-3.5 h-3.5" />
              Deep Report
            </button>
            <button
              data-tour="btn-flashcards"
              onClick={onFlashcards}
              disabled={!hasReport}
              className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-cyan-500/20 border border-cyan-500/40 py-2 text-xs font-medium text-cyan-400 hover:bg-cyan-500/30 transition-colors disabled:opacity-40"
              title={hasReport ? "Generate flashcards" : "Generate a report first"}
            >
              <CreditCard className="w-3.5 h-3.5" />
              Flashcards
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// Helper
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(",")[1]); // strip data:...;base64, prefix
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
