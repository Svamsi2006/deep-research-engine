"use client";

import React, { useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  Zap,
  PanelLeftClose,
  PanelLeftOpen,
  FileText,
  BookOpen,
  CreditCard,
  AlertTriangle,
  Info,
  HelpCircle,
} from "lucide-react";
import ResearchInput from "@/components/chat";
import ThoughtTrace from "@/components/thought-trace";
import ReportPreview from "@/components/report-preview";
import SourcesPanel from "@/components/sources-panel";
import FlashcardsPanel from "@/components/flashcards-panel";
import OnboardingTour, { resetTour } from "@/components/onboarding-tour";
import { cn } from "@/lib/utils";
import {
  streamAnswer,
  streamReport,
  streamFlashcards,
  ThoughtEvent,
  SourceInfo,
  FlashcardData,
} from "@/lib/sse-client";

type OutputTab = "report" | "sources" | "flashcards";

export default function Home() {
  // State
  const [thoughts, setThoughts] = useState<ThoughtEvent[]>([]);
  const [reportContent, setReportContent] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [qualityWarning, setQualityWarning] = useState(false);
  const [evaluationScore, setEvaluationScore] = useState<number | null>(null);
  const [showTrace, setShowTrace] = useState(true);
  const [activeTab, setActiveTab] = useState<OutputTab>("report");
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [flashcards, setFlashcards] = useState<FlashcardData[]>([]);
  const [flashcardsCsv, setFlashcardsCsv] = useState("");
  const [flashcardsLoading, setFlashcardsLoading] = useState(false);
  const [needMoreSources, setNeedMoreSources] = useState("");
  const [reportId, setReportId] = useState("");
  const [lastQuestion, setLastQuestion] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  // ── Reset for new query ────────────────────────────────────────────
  const handleReset = useCallback(() => {
    setThoughts([]);
    setReportContent("");
    setIsRunning(true);
    setIsStreaming(false);
    setQualityWarning(false);
    setEvaluationScore(null);
    setSources([]);
    setFlashcards([]);
    setFlashcardsCsv("");
    setNeedMoreSources("");
    setActiveTab("report");
  }, []);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsRunning(false);
    setIsStreaming(false);
  }, []);

  // ── Shared SSE callbacks ───────────────────────────────────────────
  const makeCallbacks = useCallback(() => {
    return {
      onThought: (event: ThoughtEvent) => {
        setThoughts((prev) => [...prev, event]);
      },
      onReportChunk: (chunk: { content: string; done: boolean }) => {
        setIsStreaming(true);
        setReportContent((prev) => prev + chunk.content);
        if (chunk.done) setIsStreaming(false);
      },
      onDone: (event: { report_id: string; evaluation_score: number; quality_warning: boolean }) => {
        // FIX: Always stop loading when done event arrives
        setIsRunning(false);
        setIsStreaming(false);
        setEvaluationScore(event.evaluation_score);
        setQualityWarning(event.quality_warning);
        setReportId(event.report_id);
      },
      onError: (error: string) => {
        setIsRunning(false);
        setIsStreaming(false);
        setReportContent((prev) => prev + `\n\n**Error:** ${error}`);
      },
      onSources: (srcs: SourceInfo[]) => {
        setSources(srcs);
      },
      onNeedMoreSources: (event: { message: string }) => {
        setNeedMoreSources(event.message);
        setIsRunning(false); // FIX: Stop loading on need_more_sources
      },
    };
  }, []);

  // ── Answer button ──────────────────────────────────────────────────
  const handleAnswer = useCallback(
    async (question: string, sourceIds: string[]) => {
      handleReset();
      setLastQuestion(question);
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamAnswer(question, sourceIds, makeCallbacks(), controller.signal);
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setReportContent(`**Error:** ${err.message}`);
        }
      } finally {
        setIsRunning(false); // FIX: Always stop on stream end
        setIsStreaming(false);
      }
    },
    [handleReset, makeCallbacks]
  );

  // ── Deep Report button ─────────────────────────────────────────────
  const handleReport = useCallback(
    async (
      question: string,
      sourceIds: string[],
      depth: "quick" | "deep",
      allowWebSearch: boolean
    ) => {
      handleReset();
      setLastQuestion(question);
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamReport(question, sourceIds, depth, allowWebSearch, makeCallbacks(), controller.signal);
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setReportContent(`**Error:** ${err.message}`);
        }
      } finally {
        setIsRunning(false); // FIX: Always stop on stream end
        setIsStreaming(false);
      }
    },
    [handleReset, makeCallbacks]
  );

  // ── Flashcards button ──────────────────────────────────────────────
  const handleFlashcards = useCallback(async () => {
    if (!reportContent) return;
    setFlashcardsLoading(true);
    setActiveTab("flashcards");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamFlashcards(
        reportId,
        reportContent,
        lastQuestion,
        {
          onThought: (event) => setThoughts((prev) => [...prev, event]),
          onReportChunk: () => { },
          onDone: () => setFlashcardsLoading(false),
          onError: (err) => {
            setFlashcardsLoading(false);
            alert(`Flashcard error: ${err}`);
          },
          onFlashcards: (event) => {
            setFlashcards(event.cards);
            setFlashcardsCsv(event.csv);
          },
        },
        controller.signal
      );
    } catch {
      setFlashcardsLoading(false);
    }
  }, [reportContent, reportId, lastQuestion]);

  const tabs: { key: OutputTab; label: string; icon: React.ElementType; count?: number; tourAttr: string }[] = [
    { key: "report", label: "Report", icon: BookOpen, tourAttr: "tab-report" },
    { key: "sources", label: "Sources", icon: FileText, count: sources.length, tourAttr: "tab-sources" },
    { key: "flashcards", label: "Flashcards", icon: CreditCard, count: flashcards.length, tourAttr: "tab-flashcards" },
  ];

  return (
    <div className="h-screen flex flex-col">
      {/* Onboarding Tour */}
      <OnboardingTour />

      {/* Top bar */}
      <header className="flex items-center justify-between border-b border-border px-4 py-2.5 bg-background/80 backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <Zap className="w-5 h-5 text-accent" />
          <h1 className="text-sm font-semibold tracking-tight">
            Deep Research Engine
          </h1>
          <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
            v0.2
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/about"
            className="flex items-center gap-1 rounded px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            title="About this platform"
          >
            <Info className="w-3.5 h-3.5" />
            About
          </Link>
          <button
            onClick={resetTour}
            className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            title="Restart guided tour"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
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
      <div className="flex-1 flex flex-col md:flex-row overflow-y-auto md:overflow-hidden">
        {/* Left panel: Input + Steps */}
        <div
          className={cn(
            "flex flex-col border-b md:border-b-0 md:border-r border-border transition-all duration-200 shrink-0",
            showTrace ? "md:w-[480px]" : "md:w-[380px]"
          )}
        >
          {/* Research Input */}
          <div className="flex-1 min-h-[300px] md:min-h-0 overflow-y-auto">
            <ResearchInput
              onAnswer={handleAnswer}
              onReport={handleReport}
              onFlashcards={handleFlashcards}
              isLoading={isRunning}
              hasReport={!!reportContent && !isRunning}
              onStop={handleStop}
            />
          </div>

          {/* Need more sources warning */}
          {needMoreSources && (
            <div className="mx-3 mb-2 flex items-start gap-2 rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-2 text-xs text-amber-400">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{needMoreSources}</span>
            </div>
          )}

          {/* Steps timeline */}
          {showTrace && (
            <div className="h-[280px] border-t border-border bg-background/50 overflow-hidden" data-tour="trace">
              <ThoughtTrace thoughts={thoughts} isRunning={isRunning} />
            </div>
          )}
        </div>

        {/* Right panel: Tabs */}
        <div className="flex-1 min-w-0 bg-background flex flex-col min-h-[600px] md:min-h-0">
          {/* Tab bar */}
          <div className="flex items-center border-b border-border px-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  data-tour={tab.tourAttr}
                  className={cn(
                    "flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors border-b-2 -mb-[1px]",
                    activeTab === tab.key
                      ? "text-accent border-accent"
                      : "text-muted-foreground border-transparent hover:text-foreground hover:border-border"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                  {tab.count !== undefined && tab.count > 0 && (
                    <span className="ml-1 text-[10px] bg-accent/20 text-accent px-1.5 py-0.5 rounded-full">
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}

            {/* Score badge */}
            {evaluationScore !== null && (
              <span
                className={cn(
                  "ml-auto text-[10px] font-mono px-2 py-0.5 rounded-full",
                  evaluationScore >= 0.7
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-amber-500/20 text-amber-400"
                )}
              >
                {(evaluationScore * 100).toFixed(0)}% quality
              </span>
            )}
          </div>

          {/* Tab content */}
          <div className="flex-1 min-h-0">
            {activeTab === "report" && (
              <ReportPreview
                content={reportContent}
                isStreaming={isStreaming}
                qualityWarning={qualityWarning}
                evaluationScore={evaluationScore}
              />
            )}
            {activeTab === "sources" && <SourcesPanel sources={sources} />}
            {activeTab === "flashcards" && (
              <FlashcardsPanel
                cards={flashcards}
                csv={flashcardsCsv}
                isLoading={flashcardsLoading}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
