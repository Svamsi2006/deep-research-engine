import React from "react";
import Link from "next/link";
import {
    Zap,
    BookOpen,
    CreditCard,
    Paperclip,
    Link2,
    Globe,
    ArrowLeft,
    GitBranch,
    Shield,
    Server,
    Brain,
    FileText,
    Search,
    CheckCircle,
    RefreshCw,
    Database,
    Code,
} from "lucide-react";

export default function AboutPage() {
    return (
        <div className="min-h-screen bg-background text-foreground">
            {/* Header */}
            <header className="border-b border-border px-6 py-4 bg-background/80 backdrop-blur-sm sticky top-0 z-10">
                <div className="max-w-4xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Zap className="w-5 h-5 text-accent" />
                        <h1 className="text-lg font-semibold">Deep Research Engine</h1>
                        <span className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                            v0.2
                        </span>
                    </div>
                    <Link
                        href="/"
                        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-accent transition-colors"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back to App
                    </Link>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-6 py-10 space-y-12">
                {/* Hero */}
                <section className="text-center space-y-4">
                    <h2 className="text-3xl font-bold bg-gradient-to-r from-accent via-violet-400 to-cyan-400 bg-clip-text text-transparent">
                        AI-Powered Deep Research for Engineers
                    </h2>
                    <p className="text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                        Upload PDFs, paste URLs, link GitHub repos — and get a detailed,
                        cited engineering report with verifiable sources. Not a summary.
                        A real research document with evidence-backed claims.
                    </p>
                </section>

                {/* What It Does */}
                <section className="space-y-6">
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                        <Brain className="w-5 h-5 text-violet-400" />
                        What Does It Do?
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {[
                            {
                                icon: FileText,
                                title: "Ingest Sources",
                                desc: "Upload PDFs, paste web URLs, or link GitHub repositories. The system extracts, chunks, and indexes all content.",
                                color: "text-blue-400",
                                bg: "bg-blue-500/10 border-blue-500/20",
                            },
                            {
                                icon: BookOpen,
                                title: "Deep Reports",
                                desc: "A 5-step pipeline: Plan → Retrieve → Write → Judge → Refine. Every claim is cited. Insufficient evidence is flagged.",
                                color: "text-violet-400",
                                bg: "bg-violet-500/10 border-violet-500/20",
                            },
                            {
                                icon: CreditCard,
                                title: "Flashcards",
                                desc: "Auto-generate Q&A flashcards from any report. Export as Anki-compatible CSV or JSON for study.",
                                color: "text-cyan-400",
                                bg: "bg-cyan-500/10 border-cyan-500/20",
                            },
                        ].map((item) => (
                            <div
                                key={item.title}
                                className={`rounded-xl border p-5 space-y-3 ${item.bg}`}
                            >
                                <item.icon className={`w-6 h-6 ${item.color}`} />
                                <h4 className="font-semibold text-sm">{item.title}</h4>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    {item.desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </section>

                {/* How To Use */}
                <section className="space-y-6">
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                        <Search className="w-5 h-5 text-amber-400" />
                        How To Use
                    </h3>
                    <div className="space-y-4">
                        {[
                            {
                                step: "1",
                                icon: Paperclip,
                                title: "Add Your Sources",
                                desc: "Click 'Attach PDF' to upload research papers, or 'Paste URLs' to add web pages and GitHub repos. Each source gets chunked and indexed.",
                            },
                            {
                                step: "2",
                                icon: BookOpen,
                                title: "Ask Your Question",
                                desc: "Type a specific engineering question. The more specific, the better the report. Example: 'Compare Mamba vs Transformer for real-time inference on edge devices'.",
                            },
                            {
                                step: "3",
                                icon: Zap,
                                title: "Choose Your Mode",
                                desc: "'Answer' for quick responses. 'Deep Report' for the full research pipeline with citations. 'Flashcards' to generate study cards from a completed report.",
                            },
                            {
                                step: "4",
                                icon: CheckCircle,
                                title: "Review & Export",
                                desc: "Read the report in the Report tab. Check Sources tab for all citations. Export flashcards as Anki CSV. Download the report as Markdown.",
                            },
                        ].map((item) => (
                            <div
                                key={item.step}
                                className="flex gap-4 items-start rounded-xl border border-border bg-muted/20 p-4"
                            >
                                <div className="shrink-0 w-8 h-8 rounded-full bg-accent/20 text-accent font-bold text-sm flex items-center justify-center">
                                    {item.step}
                                </div>
                                <div className="space-y-1">
                                    <h4 className="text-sm font-semibold flex items-center gap-2">
                                        <item.icon className="w-4 h-4 text-muted-foreground" />
                                        {item.title}
                                    </h4>
                                    <p className="text-xs text-muted-foreground leading-relaxed">
                                        {item.desc}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Pipeline */}
                <section className="space-y-6">
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                        <GitBranch className="w-5 h-5 text-emerald-400" />
                        Research Pipeline
                    </h3>
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs border border-border rounded-lg overflow-hidden">
                            <thead>
                                <tr className="bg-muted/50">
                                    <th className="text-left px-4 py-2.5 font-semibold">Step</th>
                                    <th className="text-left px-4 py-2.5 font-semibold">Uses AI?</th>
                                    <th className="text-left px-4 py-2.5 font-semibold">What It Does</th>
                                </tr>
                            </thead>
                            <tbody>
                                {[
                                    ["📋 Planner", "✅ Yes", "Breaks your question into sub-questions + must-check items (baselines, failure modes, gotchas)"],
                                    ["🔍 Retrieval", "❌ No", "BM25 keyword search — finds the top-k most relevant chunks per sub-question from your sources"],
                                    ["✍️ Writer", "✅ Yes", "Writes the full report with [source:chunk] citations. Follows a strict format with trade-off tables"],
                                    ["🔍 Judge", "✅ Yes", "Checks for missing citations, contradictions, shallow sections. Scores quality 0-100%"],
                                    ["🔧 Refiner", "✅ If needed", "Only runs if Judge score < 70%. Regenerates flagged sections, then re-judges"],
                                ].map((row, i) => (
                                    <tr key={i} className="border-t border-border hover:bg-muted/30">
                                        <td className="px-4 py-2.5 font-medium">{row[0]}</td>
                                        <td className="px-4 py-2.5">{row[1]}</td>
                                        <td className="px-4 py-2.5 text-muted-foreground">{row[2]}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>

                {/* Tools & Tech */}
                <section className="space-y-6">
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                        <Code className="w-5 h-5 text-pink-400" />
                        Technology Stack
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {[
                            { name: "Next.js 15", desc: "React frontend framework", icon: Globe },
                            { name: "FastAPI", desc: "Python async backend", icon: Server },
                            { name: "OpenRouter", desc: "Free LLM models (primary)", icon: Brain },
                            { name: "Groq", desc: "Fast LLM fallback", icon: Zap },
                            { name: "BM25", desc: "Keyword search (pure Python)", icon: Search },
                            { name: "SQLite", desc: "Local database", icon: Database },
                            { name: "PyMuPDF", desc: "PDF text extraction", icon: FileText },
                            { name: "Tavily", desc: "Optional web search API", icon: Globe },
                            { name: "SSE", desc: "Real-time streaming events", icon: RefreshCw },
                        ].map((tech) => (
                            <div
                                key={tech.name}
                                className="flex items-center gap-3 rounded-lg border border-border bg-muted/20 px-3 py-2.5"
                            >
                                <tech.icon className="w-4 h-4 text-muted-foreground shrink-0" />
                                <div>
                                    <p className="text-xs font-medium">{tech.name}</p>
                                    <p className="text-[10px] text-muted-foreground">{tech.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* LLM Strategy */}
                <section className="space-y-4">
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                        <Shield className="w-5 h-5 text-amber-400" />
                        LLM Strategy: Free-First + Fallback
                    </h3>
                    <div className="rounded-xl border border-border bg-muted/20 p-5 space-y-3 text-xs text-muted-foreground leading-relaxed">
                        <p>
                            <strong className="text-foreground">Primary: OpenRouter</strong> —
                            uses <code className="text-accent">openrouter/free</code> which
                            auto-selects the best available free model (Llama 3.3, Gemini
                            Flash, DeepSeek, etc). Zero cost.
                        </p>
                        <p>
                            <strong className="text-foreground">Fallback: Groq</strong> — if
                            OpenRouter returns 429 (rate limit) or 5xx (server error), the
                            system automatically retries once, then falls back to Groq with{" "}
                            <code className="text-accent">llama-3.3-70b-versatile</code>.
                        </p>
                        <p>
                            This gives you <strong className="text-foreground">free-first</strong>{" "}
                            behavior while keeping the platform reliable when free pools are
                            saturated.
                        </p>
                    </div>
                </section>

                {/* Footer */}
                <footer className="border-t border-border pt-6 pb-10 text-center space-y-2">
                    <p className="text-xs text-muted-foreground">
                        Deep Research Engine v0.2 — Built with ❤️ for engineers who need
                        real research, not summaries.
                    </p>
                    <Link
                        href="/"
                        className="inline-flex items-center gap-1.5 text-sm text-accent hover:text-accent/80 transition-colors"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Start Researching
                    </Link>
                </footer>
            </main>
        </div>
    );
}
