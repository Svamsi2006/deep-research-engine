"use client";

import React, { useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Download, FileText, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ReportPreviewProps {
  content: string;
  isStreaming: boolean;
  qualityWarning: boolean;
  evaluationScore: number | null;
}

export default function ReportPreview({
  content,
  isStreaming,
  qualityWarning,
  evaluationScore,
}: ReportPreviewProps) {
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(content);
  }, [content]);

  const handleDownload = useCallback(() => {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `oracle-report-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [content]);

  if (!content && !isStreaming) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-center space-y-3 max-w-sm">
          <FileText className="w-10 h-10 text-muted-foreground/40 mx-auto" />
          <p className="text-sm text-muted-foreground">
            The generated research report will appear here with tables, code
            snippets, and citations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium">Report</span>
          {evaluationScore !== null && (
            <span
              className={cn(
                "text-[10px] font-mono px-1.5 py-0.5 rounded-full",
                evaluationScore >= 0.8
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-amber-500/20 text-amber-400"
              )}
            >
              {(evaluationScore * 100).toFixed(0)}% relevance
            </span>
          )}
          {isStreaming && (
            <span className="text-[10px] text-muted-foreground animate-pulse">
              streaming...
            </span>
          )}
        </div>
        <div className="flex gap-1">
          <button
            onClick={handleCopy}
            className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            title="Copy Markdown"
          >
            <Copy className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleDownload}
            className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            title="Download .md"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Quality warning */}
      {qualityWarning && (
        <div className="mx-4 mt-3 mb-1 flex items-start gap-2 rounded-lg bg-amber-500/10 border border-amber-500/30 p-3 text-xs text-amber-300">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Quality threshold was not met after maximum retries. Some claims in
            this report may lack sufficient supporting evidence.
          </span>
        </div>
      )}

      {/* Markdown content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="markdown-body max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-accent animate-pulse ml-0.5 align-baseline" />
        )}
      </div>
    </div>
  );
}
