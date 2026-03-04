"use client";

import React, { useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  Zap,
  Settings,
  FileText,
  BookOpen,
  CreditCard,
  AlertTriangle,
  Info,
  HelpCircle,
  Brain,
  Layers,
  Route,
  RefreshCw,
  Search,
  FileUp,
} from "lucide-react";
import ResearchInput from "@/components/chat";
import ReportPreview from "@/components/report-preview";
import SourcesPanel from "@/components/sources-panel";
import FlashcardsPanel from "@/components/flashcards-panel";
import SettingsDialog from "@/components/settings-dialog";
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
  const [showIntro, setShowIntro] = useState(true);
  const [qualityWarning, setQualityWarning] = useState(false);
  const [evaluationScore, setEvaluationScore] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);
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
      <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />

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
            onClick={() => setShowSettings(true)}
            className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            onClick={resetTour}
            className="rounded p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            title="Restart guided tour"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Intro Screen */}
      {showIntro && !reportContent && (
        <div className="flex-1 overflow-y-auto bg-gradient-to-br from-background via-background to-accent/5">
          <div className="max-w-6xl mx-auto px-4 py-8 md:py-12">
            {/* Hero Section */}
            <div className="text-center mb-12 md:mb-16">
              <div className="flex items-center justify-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
                  <Brain className="w-5 h-5 text-accent" />
                </div>
                <h2 className="text-3xl md:text-4xl font-bold">
                  AI-Powered Research Engine
                </h2>
              </div>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Ingest documents, search the web, and generate comprehensive cited research reports using a deterministic AI pipeline. Get answers faster with real-time streaming and automatic quality evaluation.
              </p>
              <button
                onClick={() => setShowIntro(false)}
                className="mt-6 px-6 py-2 bg-accent text-accent-foreground rounded-lg font-medium hover:opacity-90 transition-opacity"
              >
                Get Started →
              </button>
            </div>

            {/* How It Works */}
            <div className="mb-12 md:mb-16">
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Route className="w-5 h-5 text-accent" />
                The Research Pipeline
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                {[
                  { num: 1, label: "Plan", desc: "Break down question into sub-questions" },
                  { num: 2, label: "Retrieve", desc: "Search ingested documents" },
                  { num: 3, label: "Web Search", desc: "Augment with live web results" },
                  { num: 4, label: "Write", desc: "Synthesize evidence into report" },
                  { num: 5, label: "Judge & Refine", desc: "Score quality, refine if needed" },
                ].map((step) => (
                  <div key={step.num} className="relative">
                    <div className="rounded-lg border border-border bg-muted/50 p-4 text-center">
                      <div className="text-2xl font-bold text-accent mb-2">{step.num}</div>
                      <div className="text-sm font-medium mb-1">{step.label}</div>
                      <div className="text-xs text-muted-foreground">{step.desc}</div>
                    </div>
                    {step.num < 5 && (
                      <div className="absolute -right-2 top-1/2 -translate-y-1/2 hidden md:block">
                        <div className="text-muted-foreground text-lg">→</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Key Features */}
            <div className="mb-12 md:mb-16">
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Zap className="w-5 h-5 text-accent" />
                Core Features
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  { icon: FileUp, label: "Multi-Source Ingest", desc: "PDFs, URLs, GitHub repos" },
                  { icon: Search, label: "Dual Search", desc: "Local + web augmentation" },
                  { icon: Layers, label: "Deep Reports", desc: "Deterministic 5-step pipeline" },
                  { icon: BookOpen, label: "Auto Flashcards", desc: "Study cards from reports" },
                ].map((feature) => {
                  const Icon = feature.icon;
                  return (
                    <div key={feature.label} className="rounded-lg border border-border bg-muted/30 p-4">
                      <Icon className="w-5 h-5 text-accent mb-2" />
                      <div className="text-sm font-medium mb-1">{feature.label}</div>
                      <div className="text-xs text-muted-foreground">{feature.desc}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Architecture */}
            <div className="mb-12 md:mb-16">
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Layers className="w-5 h-5 text-accent" />
                Architecture Stack
              </h3>
              <div className="rounded-lg border border-border bg-muted/30 p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <h4 className="font-semibold text-sm mb-3">Frontend</h4>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>• Next.js 15 (React 19)</li>
                      <li>• Real-time SSE streaming</li>
                      <li>• Tailwind CSS + Lucide icons</li>
                      <li>• Vercel deployment ready</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm mb-3">Backend</h4>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>• FastAPI + Python 3.11+</li>
                      <li>• SQLite + SQLAlchemy async</li>
                      <li>• Pydantic v2 validation</li>
                      <li>• Railway deployment ready</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm mb-3">LLM & Search</h4>
                    <ul className="text-xs text-muted-foreground space-y-1">
                      <li>• 7 LLM providers (OpenRouter, Groq, OpenAI, etc.)</li>
                      <li>• DuckDuckGo + Tavily web search</li>
                      <li>• Circuit breaker + auto-failover</li>
                      <li>• Free-tier models available</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            {/* Models */}
            <div className="mb-12 md:mb-16">
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Brain className="w-5 h-5 text-accent" />
                LLM Models Used
              </h3>
              <div className="rounded-lg border border-border bg-muted/30 p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="font-medium text-accent mb-2">Primary (OpenRouter)</div>
                    <p className="text-muted-foreground">Meta Llama 3.3 70B Instruct (free tier)</p>
                  </div>
                  <div>
                    <div className="font-medium text-accent mb-2">Fallback (Groq)</div>
                    <p className="text-muted-foreground">Llama 3.3 70B Versatile (fast inference)</p>
                  </div>
                  <div>
                    <div className="font-medium text-accent mb-2">Embeddings</div>
                    <p className="text-muted-foreground">sentence-transformers → Cohere → OpenAI fallback</p>
                  </div>
                  <div>
                    <div className="font-medium text-accent mb-2">Other Providers</div>
                    <p className="text-muted-foreground">OpenAI, Gemini, DeepSeek, Grok (switchable)</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Getting Started */}
            <div className="text-center bg-muted/50 rounded-lg border border-border p-8">
              <h3 className="text-lg font-bold mb-3">Ready to Start?</h3>
              <p className="text-sm text-muted-foreground mb-6">
                Ingest your first document or ask a question about the web. The AI will research and present findings in real-time.
              </p>
              <button
                onClick={() => setShowIntro(false)}
                className="px-8 py-2.5 bg-accent text-accent-foreground rounded-lg font-medium hover:opacity-90 transition-opacity"
              >
                Begin Research →
              </button>
            </div>

            <div className="text-center mt-8 text-xs text-muted-foreground">
              <p>
                Learn more on the <Link href="/about" className="text-accent hover:underline">Architecture & How It Works</Link> page
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main layout (hidden when showing intro) */}
      {(!showIntro || reportContent) && (
      <div className="flex-1 flex flex-col md:flex-row overflow-y-auto md:overflow-hidden">
        {/* Left panel: Input + Steps */}
        <div
          className={cn(
            "flex flex-col border-b md:border-b-0 md:border-r border-border transition-all duration-200 shrink-0",
            "md:w-[380px]"
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

          {/* Agent trace removed per UX request */}
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
                isRunning={isRunning}
                thoughts={thoughts}
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
      )}
    </div>
  );
}
