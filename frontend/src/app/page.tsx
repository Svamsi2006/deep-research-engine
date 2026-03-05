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
import { ConversationSidebar } from "@/components/conversation-sidebar";
import { ConversationHistory } from "@/components/message-history";
import ChatMessages from "@/components/chat-messages";
import CanvasEditor from "@/components/canvas-editor";
import ModernSidebar from "@/components/modern-sidebar";
import ModernHeader from "@/components/modern-header";
import ActionBar from "@/components/action-bar";
import RoundedChatInput from "@/components/rounded-chat-input";
import PDFUploadDialog from "@/components/pdf-upload-dialog";
import URLIngestDialog from "@/components/url-ingest-dialog";
import IngestedSourcesList, { IngestedSource } from "@/components/ingested-sources-list";
import { useSession } from "@/lib/use-session";
import { useSessionStorage } from "@/lib/use-session-storage";
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

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  thinking?: string;
  reportId?: string;
  reportTitle?: string;
  reportSummary?: string;
}

interface Report {
  id: string;
  title: string;
  content: string;
  created_at: string;
}

export default function Home() {
  // Session management
  const { user, isLoading: sessionLoading, conversationId, setConversationId, createNewConversation } = useSession()
  
  // Session storage for chat history
  const sessionStorage = useSessionStorage();

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

  // Chat and Canvas state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [canvasReportId, setCanvasReportId] = useState<string | null>(null);
  const [mode, setMode] = useState<'chat' | 'report'>('chat');
  
  // Action bar state
  const [selectedActions, setSelectedActions] = useState<Array<'deep-research' | 'web-search' | 'analyze-pdf' | 'paste-url' | 'flashcards'>>(['deep-research']);
  const [actionsExpanded, setActionsExpanded] = useState(true);

  // PDF/URL upload state
  const [showPDFDialog, setShowPDFDialog] = useState(false);
  const [showURLDialog, setShowURLDialog] = useState(false);
  const [ingestedSources, setIngestedSources] = useState<IngestedSource[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [showSourcesPanel, setShowSourcesPanel] = useState(false);

  // ── Initialize sessionStorage on mount ──────────────────────────────
  React.useEffect(() => {
    // If no current session, create one
    if (sessionStorage.isLoaded && !sessionStorage.currentSession) {
      sessionStorage.createSession(`Chat - ${new Date().toLocaleTimeString()}`);
    }
  }, [sessionStorage.isLoaded, sessionStorage]);

  // ── Source management handlers (non-message related) ────────────────────────
  const handleToggleSource = useCallback((sourceId: string) => {
    setSelectedSourceIds(prev => 
      prev.includes(sourceId) 
        ? prev.filter(id => id !== sourceId)
        : [...prev, sourceId]
    );
  }, []);

  const handleRemoveSource = useCallback((sourceId: string) => {
    setIngestedSources(prev => prev.filter(s => s.sourceId !== sourceId));
    setSelectedSourceIds(prev => prev.filter(id => id !== sourceId));
  }, []);

  const handleSelectAllSources = useCallback(() => {
    setSelectedSourceIds(ingestedSources.map(s => s.sourceId));
  }, [ingestedSources]);

  const handleClearAllSources = useCallback(() => {
    setSelectedSourceIds([]);
  }, []);

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

  // ── New Chat handler ───────────────────────────────────────────────
  const handleNewChat = useCallback(() => {
    // Clear all conversation state
    setChatMessages([]);
    setThoughts([]);
    setReportContent("");
    setSources([]);
    setFlashcards([]);
    setFlashcardsCsv("");
    setReports([]);
    setCanvasReportId(null);
    
    // Reset UI state
    setMode('chat');
    setShowIntro(true);
    setQualityWarning(false);
    setEvaluationScore(null);
    setNeedMoreSources("");
    setReportId("");
    setLastQuestion("");
    setIsRunning(false);
    setIsStreaming(false);
    setActiveTab("report");
    
    // Reset selected actions to default
    setSelectedActions(['deep-research']);
    setActionsExpanded(true);
    
    // Create new session in sessionStorage
    sessionStorage.createSession(`New Chat - ${new Date().toLocaleTimeString()}`);
    
    // Create new conversation on backend
    createNewConversation();
  }, [createNewConversation, sessionStorage]);

  // Helper to add chat messages
  const addMessage = useCallback((message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
    const newMessage: ChatMessage = {
      ...message,
      id: Date.now().toString() + Math.random(),
      timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, newMessage]);
    
    // Also store in sessionStorage (only user and assistant messages)
    if (message.role === 'user' || message.role === 'assistant') {
      sessionStorage.addMessage(message.role, message.content);
    }
    
    return newMessage;
  }, [sessionStorage]);

  // Helper to update last assistant message
  const updateLastAssistantMessage = useCallback((updates: Partial<ChatMessage>) => {
    setChatMessages(prev => {
      const lastIndex = prev.findLastIndex(m => m.role === 'assistant');
      if (lastIndex === -1) return prev;

      const newMessages = [...prev];
      newMessages[lastIndex] = { ...newMessages[lastIndex], ...updates };
      return newMessages;
    });
  }, []);

  // ── PDF/URL Ingestion handlers (after addMessage defined) ──────────────────
  const handlePDFUploadComplete = useCallback((sourceId: string, title: string, chunkCount: number) => {
    const newSource: IngestedSource = {
      sourceId,
      title,
      type: 'pdf',
      chunkCount,
      timestamp: new Date().toISOString(),
    };
    setIngestedSources(prev => [...prev, newSource]);
    setSelectedSourceIds(prev => [...prev, sourceId]);
    setShowSourcesPanel(true);
    
    // Add system message to chat
    addMessage({
      role: 'system',
      content: `✓ PDF uploaded: "${title}" (${chunkCount} chunks created)`,
    });
  }, [addMessage]);

  const handleURLIngestComplete = useCallback((sourceId: string, title: string, chunkCount: number) => {
    const newSource: IngestedSource = {
      sourceId,
      title,
      type: 'url',
      chunkCount,
      timestamp: new Date().toISOString(),
    };
    setIngestedSources(prev => [...prev, newSource]);
    setSelectedSourceIds(prev => [...prev, sourceId]);
    setShowSourcesPanel(true);
    
    // Add system message to chat
    addMessage({
      role: 'system',
      content: `✓ URL ingested: "${title}" (${chunkCount} chunks created)`,
    });
  }, [addMessage]);

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
      if (!user) return;

      handleReset();
      setLastQuestion(question);
      setMode('chat'); // Set to chat mode
      setShowIntro(false);

      // Add user message to chat
      addMessage({
        role: 'user',
        content: question,
      });

      // Add placeholder assistant message
      const assistantMsg = addMessage({
        role: 'assistant',
        content: '',
      });

      // Create new conversation if needed
      let convId: string | undefined = conversationId || undefined;
      if (!convId && user.id) {
        try {
          const response = await fetch(`/api/users/${user.id}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title: question.slice(0, 100)
            })
          });
          if (response.ok) {
            const data = await response.json();
            convId = data.id;
            if (convId) setConversationId(convId);
          }
        } catch (err) {
          console.error('Failed to create conversation:', err);
        }
      }

      const controller = new AbortController();
      abortRef.current = controller;

      let accumulatedContent = '';

      try {
        const contextBuffer = sessionStorage.getContextBuffer(6);
        await streamAnswer(
          question, 
          sourceIds, 
          {
            ...makeCallbacks(),
            onReportChunk: (chunk: { content: string; done: boolean }) => {
              setIsStreaming(true);
              accumulatedContent += chunk.content;
              setReportContent((prev) => prev + chunk.content);

              // Update assistant message with accumulated content
              updateLastAssistantMessage({ content: accumulatedContent });

              if (chunk.done) setIsStreaming(false);
            },
          }, 
          controller.signal, 
          user.id, 
          convId,
          contextBuffer.length > 0 ? contextBuffer : undefined
        );
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          const errorMsg = `**Error:** ${err.message}`;
          setReportContent(errorMsg);
          updateLastAssistantMessage({ content: errorMsg });
        }
      } finally {
        setIsRunning(false);
        setIsStreaming(false);
      }
    },
    [user, conversationId, setConversationId, handleReset, makeCallbacks, addMessage, updateLastAssistantMessage]
  );

  // ── Deep Report button ─────────────────────────────────────────────
  const handleReport = useCallback(
    async (
      question: string,
      sourceIds: string[],
      depth: "quick" | "deep",
      allowWebSearch: boolean
    ) => {
      if (!user) return;

      handleReset();
      setLastQuestion(question);
      setMode('report'); // Set to report mode
      setShowIntro(false);

      // Add user message to chat
      addMessage({
        role: 'user',
        content: question,
      });

      // Add placeholder assistant message
      addMessage({
        role: 'assistant',
        content: 'Generating deep research report...',
      });

      // Create new conversation if needed
      let convId: string | undefined = conversationId || undefined;
      if (!convId && user.id) {
        try {
          const response = await fetch(`/api/users/${user.id}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              title: question.slice(0, 100)
            })
          });
          if (response.ok) {
            const data = await response.json();
            convId = data.id;
            if (convId) setConversationId(convId);
          }
        } catch (err) {
          console.error('Failed to create conversation:', err);
        }
      }

      const controller = new AbortController();
      abortRef.current = controller;

      let accumulatedContent = '';
      let accumulatedThinking = '';

      try {
        const contextBuffer = sessionStorage.getContextBuffer(6);
        await streamReport(
          question, 
          sourceIds, 
          depth, 
          allowWebSearch, 
          {
            ...makeCallbacks(),
            onThought: (event: ThoughtEvent) => {
              setThoughts((prev) => [...prev, event]);
              accumulatedThinking += `[${event.node}] ${event.status}: ${event.message}\n`;
            },
            onReportChunk: (chunk: { content: string; done: boolean }) => {
              setIsStreaming(true);
              accumulatedContent += chunk.content;
              setReportContent((prev) => prev + chunk.content);

              if (chunk.done) setIsStreaming(false);
            },
            onDone: (event: { report_id: string; evaluation_score: number; quality_warning: boolean }) => {
              setIsRunning(false);
              setIsStreaming(false);
              setEvaluationScore(event.evaluation_score);
              setQualityWarning(event.quality_warning);
              setReportId(event.report_id);

              // Store report for canvas
              const newReport: Report = {
                id: event.report_id,
                title: question,
                content: accumulatedContent,
                created_at: new Date().toISOString(),
              };
              setReports(prev => [...prev, newReport]);

              // Update assistant message with report card
              updateLastAssistantMessage({
                content: `I've generated a comprehensive research report on "${question}".`,
                thinking: accumulatedThinking,
                reportId: event.report_id,
                reportTitle: question,
                reportSummary: accumulatedContent.slice(0, 300) + '...',
              });
            },
          }, 
          controller.signal, 
          user.id, 
          convId,
          contextBuffer.length > 0 ? contextBuffer : undefined
        );
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          const errorMsg = `**Error:** ${err.message}`;
          setReportContent(errorMsg);
          updateLastAssistantMessage({ content: errorMsg });
        }
      } finally {
        setIsRunning(false);
        setIsStreaming(false);
      }
    },
    [user, conversationId, setConversationId, handleReset, makeCallbacks, addMessage, updateLastAssistantMessage]
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

  // ── Generate flashcards for ReportPreview ───────────────────────────
  const handleGenerateFlashcardsForReport = useCallback(
    async (
      reportId: string,
      reportContent: string,
      question: string,
      callbacks: {
        onFlashcards: (event: { cards: FlashcardData[]; csv: string }) => void;
        onError: (error: string) => void;
      }
    ) => {
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamFlashcards(
          reportId,
          reportContent,
          question,
          {
            onThought: (event) => setThoughts((prev) => [...prev, event]),
            onReportChunk: () => { },
            onDone: () => { },
            onError: (err) => callbacks.onError(err),
            onFlashcards: (event) => {
              callbacks.onFlashcards(event);
            },
          },
          controller.signal
        );
      } catch (error) {
        callbacks.onError(error instanceof Error ? error.message : "Unknown error");
      }
    },
    []
  );

  const tabs: { key: OutputTab; label: string; icon: React.ElementType; count?: number; tourAttr: string }[] = [
    { key: "report", label: "Report", icon: BookOpen, tourAttr: "tab-report" },
    { key: "sources", label: "Sources", icon: FileText, count: sources.length, tourAttr: "tab-sources" },
    { key: "flashcards", label: "Flashcards", icon: CreditCard, count: flashcards.length, tourAttr: "tab-flashcards" },
  ];

  return (
    <div className="h-screen flex flex-col bg-[#0D0D0D]">
      {/* Onboarding Tour */}
      <OnboardingTour />
      <SettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />

      {/* Modern Header */}
      <ModernHeader
        title="Deep Research Engine"
        userInfo={
          user && !sessionLoading
            ? { isAnonymous: user.isAnonymous, name: user.name }
            : undefined
        }
        onSettingsClick={() => setShowSettings(true)}
        onHelpClick={resetTour}
      />

      {/* Main layout with sidebar */}
      <div className="flex-1 flex overflow-hidden">
        {/* Modern Sidebar - Conversations */}
        {user && !sessionLoading && (
          <ModernSidebar
            userId={user.id}
            conversations={[]}  // Will be populated from conversation list
            currentConversationId={conversationId}
            onSelectConversation={setConversationId}
            onNewConversation={handleNewChat}
          />
        )}

        {/* Main content area */}
        <div className="flex-1 flex flex-col overflow-hidden bg-[#0D0D0D]">
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

          {/* Main layout - Chat interface (hidden when showing intro) */}
          {(!showIntro || reportContent) && (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Chat messages area */}
              <div className="flex-1 overflow-y-auto">
                <div className="max-w-4xl mx-auto px-4 py-6">
                  {chatMessages.length > 0 ? (
                    <ChatMessages
                      messages={chatMessages}
                      onOpenReport={(reportId) => setCanvasReportId(reportId)}
                      isStreaming={isStreaming}
                    />
                  ) : (
                    <div className="text-center text-[#A0A0A0] py-12">
                      <p className="text-sm">No messages yet. Start a conversation below!</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Sources panel toggle */}
              {ingestedSources.length > 0 && (
                <div className="px-4 py-2 border-b border-[#2A2A2A] flex items-center justify-between">
                  <button
                    onClick={() => setShowSourcesPanel(!showSourcesPanel)}
                    className="text-sm text-[#4F46E5] hover:text-[#6366F1] font-medium flex items-center gap-2"
                  >
                    <FileText className="w-4 h-4" />
                    {showSourcesPanel ? 'Hide' : 'Show'} Sources ({ingestedSources.length})
                  </button>
                  {selectedSourceIds.length > 0 && (
                    <span className="text-xs text-[#A0A0A0]">
                      {selectedSourceIds.length} selected for research
                    </span>
                  )}
                </div>
              )}

              {/* Sources panel */}
              {showSourcesPanel && ingestedSources.length > 0 && (
                <div className="border-b border-[#2A2A2A] bg-[#0D0D0D]" style={{ height: '300px' }}>
                  <IngestedSourcesList
                    sources={ingestedSources}
                    selectedSourceIds={selectedSourceIds}
                    onToggleSource={handleToggleSource}
                    onRemoveSource={handleRemoveSource}
                    onSelectAll={handleSelectAllSources}
                    onClearAll={handleClearAllSources}
                  />
                </div>
              )}

              {/* Action bar - sits above input */}
              <ActionBar
                selectedActions={selectedActions}
                onSelectActions={setSelectedActions}
                onToggleExpanded={() => setActionsExpanded(!actionsExpanded)}
                isExpanded={actionsExpanded}
              />

              {/* Rounded chat input at bottom */}
              <RoundedChatInput
                onSend={(message) => {
                  // Smart action routing based on selected actions
                  // IMPORTANT: Do NOT block message sending if PDF/URL action is selected
                  // Instead, the user sends their message, and they can upload PDFs/URLs separately
                  
                  // Get source IDs to pass to research
                  const sourceIds = selectedSourceIds;
                  
                  // Route based on selected actions
                  if (selectedActions.includes('deep-research')) {
                    // Deep research mode - enable web search if also selected
                    handleReport(message, sourceIds, 'deep', selectedActions.includes('web-search'));
                  } 
                  else if (selectedActions.includes('web-search')) {
                    // Web search mode - quick answer with web augmentation
                    handleAnswer(message, sourceIds);
                  }
                  else if (selectedActions.length === 0) {
                    // No actions selected = normal LLM chat (unanswered question)
                    // Send directly to LLM without research mode
                    handleAnswer(message, sourceIds);
                  }
                  else {
                    // If only PDF/URL/flashcards selected (no research), treat as normal chat
                    handleAnswer(message, sourceIds);
                  }
                }}
                onAttachPDF={() => {
                  // Show PDF upload dialog
                  setShowPDFDialog(true);
                }}
                onAttachURL={() => {
                  // Show URL ingest dialog
                  setShowURLDialog(true);
                }}
                isLoading={isRunning}
                placeholder={
                  selectedActions.includes('deep-research') 
                    ? 'Ask a research question...'
                    : selectedActions.includes('web-search')
                    ? 'Search the web (with sources)...'
                    : selectedActions.includes('analyze-pdf')
                    ? 'Ask about PDFs (upload via paperclip icon)...'
                    : selectedActions.includes('paste-url')
                    ? 'Ask about URLs (paste URL via link icon)...'
                    : 'Ask anything...'
                }
                selectedActions={selectedActions}
              />
            </div>
          )}
        </div>
      </div>

      {/* Canvas Editor Overlay */}
      {canvasReportId && (
        <CanvasEditor
          reportId={canvasReportId}
          report={reports.find(r => r.id === canvasReportId)}
          onClose={() => setCanvasReportId(null)}
        />
      )}

      {/* PDF Upload Dialog */}
      <PDFUploadDialog
        isOpen={showPDFDialog}
        onClose={() => setShowPDFDialog(false)}
        onUploadComplete={handlePDFUploadComplete}
      />

      {/* URL Ingest Dialog */}
      <URLIngestDialog
        isOpen={showURLDialog}
        onClose={() => setShowURLDialog(false)}
        onIngestComplete={handleURLIngestComplete}
      />
    </div>
  );
}
