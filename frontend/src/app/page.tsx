"use client";

import React, { useState, useCallback } from "react";
import {
  Zap,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import Chat from "@/components/chat";
import ThoughtTrace from "@/components/thought-trace";
import ReportPreview from "@/components/report-preview";
import { cn } from "@/lib/utils";
import type { ThoughtEvent, ReportChunk, DoneEvent } from "@/lib/sse-client";

export default function Home() {
  // State
  const [thoughts, setThoughts] = useState<ThoughtEvent[]>([]);
  const [reportContent, setReportContent] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [qualityWarning, setQualityWarning] = useState(false);
  const [evaluationScore, setEvaluationScore] = useState<number | null>(null);
  const [showTrace, setShowTrace] = useState(true);

  // Handlers
  const handleStart = useCallback(() => {
    setThoughts([]);
    setReportContent("");
    setIsRunning(true);
    setIsStreaming(false);
    setQualityWarning(false);
    setEvaluationScore(null);
  }, []);

  const handleThought = useCallback((event: ThoughtEvent) => {
    setThoughts((prev) => [...prev, event]);
  }, []);

  const handleReportChunk = useCallback((chunk: ReportChunk) => {
    setIsStreaming(true);
    setReportContent((prev) => prev + chunk.content);
    if (chunk.done) {
      setIsStreaming(false);
    }
  }, []);

  const handleDone = useCallback((event: DoneEvent) => {
    setIsRunning(false);
    setIsStreaming(false);
    setEvaluationScore(event.evaluation_score);
    setQualityWarning(event.quality_warning);
  }, []);

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-border px-4 py-2.5 bg-background/80 backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <Zap className="w-5 h-5 text-accent" />
          <h1 className="text-sm font-semibold tracking-tight">
            Engineering Oracle
          </h1>
          <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            v0.1
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTrace(!showTrace)}
            className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            title={showTrace ? "Hide trace" : "Show trace"}
          >
            {showTrace ? (
              <PanelLeftClose className="w-4 h-4" />
            ) : (
              <PanelLeftOpen className="w-4 h-4" />
            )}
          </button>
        </div>
      </header>

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel: Chat + Thought Trace */}
        <div
          className={cn(
            "flex flex-col border-r border-border transition-all duration-200",
            showTrace ? "w-[480px]" : "w-[380px]"
          )}
        >
          {/* Chat */}
          <div className="flex-1 min-h-0">
            <Chat
              onThought={handleThought}
              onReportChunk={handleReportChunk}
              onDone={handleDone}
              onStart={handleStart}
            />
          </div>

          {/* Thought trace (collapsible) */}
          {showTrace && (
            <div className="h-[280px] border-t border-border bg-background/50 overflow-hidden">
              <ThoughtTrace thoughts={thoughts} isRunning={isRunning} />
            </div>
          )}
        </div>

        {/* Right panel: Report Preview */}
        <div className="flex-1 min-w-0 bg-background">
          <ReportPreview
            content={reportContent}
            isStreaming={isStreaming}
            qualityWarning={qualityWarning}
            evaluationScore={evaluationScore}
          />
        </div>
      </div>
    </div>
  );
}
