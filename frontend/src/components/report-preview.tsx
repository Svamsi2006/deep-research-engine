"use client";

import React, { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Copy,
  Download,
  FileText,
  AlertTriangle,
  Search,
  Brain,
  Globe,
  Sparkles,
  BookOpen,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ThoughtEvent } from "@/lib/sse-client";

/* ── Pipeline stage definitions ─────────────────────────────────────── */
const PIPELINE_STAGES = [
  { key: "plan", label: "Planning research", icon: Brain },
  { key: "retriev", label: "Retrieving sources", icon: Search },
  { key: "web_search", label: "Searching the web", icon: Globe },
  { key: "writ", label: "Writing report", icon: Sparkles },
  { key: "judg", label: "Evaluating quality", icon: CheckCircle2 },
  { key: "refin", label: "Refining report", icon: BookOpen },
] as const;

function stageStatus(
  stageKey: string,
  thoughts: ThoughtEvent[]
): "pending" | "running" | "completed" | "error" {
  const matching = thoughts.filter(
    (t) => t.node?.toLowerCase().includes(stageKey)
  );
  if (matching.length === 0) return "pending";
  const last = matching[matching.length - 1];
  if (last.status === "completed") return "completed";
  if (last.status === "error") return "error";
  return "running";
}

/* ── Loading animation component ────────────────────────────────────── */
function ResearchLoadingAnimation({
  thoughts,
}: {
  thoughts: ThoughtEvent[];
}) {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const id = setInterval(() => setDots((d) => (d.length >= 3 ? "" : d + ".")), 500);
    return () => clearInterval(id);
  }, []);

  // Find the current active stage message
  const activeThought = [...thoughts].reverse().find(
    (t) => t.status === "running" || t.status === "completed"
  );

  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="w-full max-w-md space-y-8">
        {/* Central animation */}
        <div className="flex flex-col items-center gap-5">
          {/* Animated rings */}
          <div className="relative w-20 h-20">
            <div className="absolute inset-0 rounded-full border-2 border-accent/20 animate-ping" />
            <div className="absolute inset-2 rounded-full border-2 border-accent/30 animate-pulse" />
            <div
              className="absolute inset-0 rounded-full border-t-2 border-accent"
              style={{ animation: "spin 1.5s linear infinite" }}
            />
            <div
              className="absolute inset-3 rounded-full border-t-2 border-accent/60"
              style={{ animation: "spin 2s linear infinite reverse" }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <Brain className="w-6 h-6 text-accent animate-pulse" />
            </div>
          </div>

          <div className="text-center space-y-1">
            <p className="text-sm font-medium text-foreground">
              Generating deep research report{dots}
            </p>
            {activeThought && (
              <p className="text-xs text-muted-foreground animate-pulse truncate max-w-xs">
                {activeThought.message}
              </p>
            )}
          </div>
        </div>

        {/* Pipeline step tracker */}
        <div className="space-y-2">
          {PIPELINE_STAGES.map((stage) => {
            const status = stageStatus(stage.key, thoughts);
            const Icon = stage.icon;
            return (
              <div
                key={stage.key}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-xs transition-all duration-300",
                  status === "running" && "bg-accent/10 border border-accent/30",
                  status === "completed" && "bg-emerald-500/5",
                  status === "error" && "bg-red-500/10 border border-red-500/30",
                  status === "pending" && "opacity-40"
                )}
              >
                <div
                  className={cn(
                    "flex items-center justify-center w-6 h-6 rounded-full transition-colors",
                    status === "running" && "bg-accent/20 text-accent",
                    status === "completed" && "bg-emerald-500/20 text-emerald-400",
                    status === "error" && "bg-red-500/20 text-red-400",
                    status === "pending" && "bg-muted text-muted-foreground"
                  )}
                >
                  {status === "completed" ? (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  ) : status === "running" ? (
                    <Icon className="w-3.5 h-3.5 animate-pulse" />
                  ) : (
                    <Icon className="w-3.5 h-3.5" />
                  )}
                </div>
                <span
                  className={cn(
                    "font-medium",
                    status === "running" && "text-accent",
                    status === "completed" && "text-emerald-400",
                    status === "error" && "text-red-400",
                    status === "pending" && "text-muted-foreground"
                  )}
                >
                  {stage.label}
                </span>
                {status === "running" && (
                  <div className="ml-auto flex gap-0.5">
                    <span className="w-1 h-1 rounded-full bg-accent animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1 h-1 rounded-full bg-accent animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1 h-1 rounded-full bg-accent animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                )}
                {status === "error" && (
                  <span className="ml-auto text-[10px] text-red-400">failed</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────────── */

interface ReportPreviewProps {
  content: string;
  isStreaming: boolean;
  isRunning: boolean;
  thoughts: ThoughtEvent[];
  qualityWarning: boolean;
  evaluationScore: number | null;
}

export default function ReportPreview({
  content,
  isStreaming,
  isRunning,
  thoughts,
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

  // Show loading animation when running but no content yet
  if (!content && isRunning) {
    return <ResearchLoadingAnimation thoughts={thoughts} />;
  }

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
