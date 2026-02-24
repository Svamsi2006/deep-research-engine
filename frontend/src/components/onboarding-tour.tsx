"use client";

import React, { useState, useEffect, useCallback } from "react";
import { X, ChevronRight, ChevronLeft, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface TourStep {
    target: string; // CSS selector
    title: string;
    description: string;
    position: "top" | "bottom" | "left" | "right";
}

const TOUR_STEPS: TourStep[] = [
    {
        target: "[data-tour='question']",
        title: "📝 Research Question",
        description:
            "Type your engineering question here. Be specific — e.g., 'Compare Mamba vs Transformer for production inference' rather than just 'tell me about AI'.",
        position: "right",
    },
    {
        target: "[data-tour='attach-pdf']",
        title: "📎 Attach PDFs",
        description:
            "Upload PDF papers, reports, or documentation. The system extracts text, chunks it, and makes it searchable for your research.",
        position: "right",
    },
    {
        target: "[data-tour='paste-urls']",
        title: "🔗 Paste URLs",
        description:
            "Add web URLs or GitHub links. The system scrapes content and indexes it as a research source. GitHub repos get README + key files extracted.",
        position: "right",
    },
    {
        target: "[data-tour='web-search']",
        title: "🌐 Web Search",
        description:
            "Enable this to let the AI search the web for additional sources. Off by default — the system only uses your provided documents unless you turn this on.",
        position: "right",
    },
    {
        target: "[data-tour='btn-answer']",
        title: "⚡ Answer Button",
        description:
            "Get a quick, direct answer from the AI. Best for simple questions, explanations, or when you don't need cited research. Fast and concise.",
        position: "top",
    },
    {
        target: "[data-tour='btn-report']",
        title: "📖 Deep Report Button",
        description:
            "Runs the full research pipeline: Plan → Retrieve → Write → Judge → Refine. Produces a detailed engineering report with citations from your sources.",
        position: "top",
    },
    {
        target: "[data-tour='btn-flashcards']",
        title: "🃏 Flashcards Button",
        description:
            "After generating a report, click this to create Q&A flashcards for study. Export as Anki CSV or JSON. The button activates once a report is ready.",
        position: "top",
    },
    {
        target: "[data-tour='tab-report']",
        title: "📄 Report Tab",
        description:
            "View the generated research report here. Markdown-rendered with tables, code blocks, and citations. Copy or download as .md file.",
        position: "bottom",
    },
    {
        target: "[data-tour='tab-sources']",
        title: "📚 Sources Tab",
        description:
            "See all sources cited in the report. Each source shows its title and ID so you can trace every claim back to its origin.",
        position: "bottom",
    },
    {
        target: "[data-tour='tab-flashcards']",
        title: "🃏 Flashcards Tab",
        description:
            "View generated flashcards here. Click any card to flip and reveal the answer. Export all cards for Anki or other study tools.",
        position: "bottom",
    },
    {
        target: "[data-tour='trace']",
        title: "🔍 Agent Trace",
        description:
            "Watch the AI's step-by-step progress in real-time. Each step shows what the agent is doing: planning, retrieving, writing, judging, or refining.",
        position: "right",
    },
];

const TOUR_KEY = "deep_research_tour_completed";

interface OnboardingTourProps {
    onComplete?: () => void;
}

export default function OnboardingTour({ onComplete }: OnboardingTourProps) {
    const [currentStep, setCurrentStep] = useState(0);
    const [isVisible, setIsVisible] = useState(false);
    const [tooltipPos, setTooltipPos] = useState({ top: 0, left: 0 });
    const [highlightRect, setHighlightRect] = useState<DOMRect | null>(null);

    // Show tour only for new users
    useEffect(() => {
        const completed = localStorage.getItem(TOUR_KEY);
        if (!completed) {
            // Small delay to let the page render
            const timer = setTimeout(() => setIsVisible(true), 1000);
            return () => clearTimeout(timer);
        }
    }, []);

    // Position tooltip near target element
    useEffect(() => {
        if (!isVisible) return;

        const step = TOUR_STEPS[currentStep];
        const el = document.querySelector(step.target);

        if (el) {
            const rect = el.getBoundingClientRect();
            setHighlightRect(rect);

            const tooltipW = 320;
            const tooltipH = 180;
            const gap = 12;

            let top = 0;
            let left = 0;

            switch (step.position) {
                case "right":
                    top = rect.top + rect.height / 2 - tooltipH / 2;
                    left = rect.right + gap;
                    break;
                case "left":
                    top = rect.top + rect.height / 2 - tooltipH / 2;
                    left = rect.left - tooltipW - gap;
                    break;
                case "bottom":
                    top = rect.bottom + gap;
                    left = rect.left + rect.width / 2 - tooltipW / 2;
                    break;
                case "top":
                    top = rect.top - tooltipH - gap;
                    left = rect.left + rect.width / 2 - tooltipW / 2;
                    break;
            }

            // Keep within viewport
            top = Math.max(10, Math.min(top, window.innerHeight - tooltipH - 10));
            left = Math.max(10, Math.min(left, window.innerWidth - tooltipW - 10));

            setTooltipPos({ top, left });

            // Scroll element into view
            el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }, [currentStep, isVisible]);

    const handleNext = useCallback(() => {
        if (currentStep < TOUR_STEPS.length - 1) {
            setCurrentStep((prev) => prev + 1);
        } else {
            handleComplete();
        }
    }, [currentStep]);

    const handlePrev = useCallback(() => {
        if (currentStep > 0) {
            setCurrentStep((prev) => prev - 1);
        }
    }, [currentStep]);

    const handleComplete = useCallback(() => {
        localStorage.setItem(TOUR_KEY, "true");
        setIsVisible(false);
        onComplete?.();
    }, [onComplete]);

    const handleSkip = useCallback(() => {
        localStorage.setItem(TOUR_KEY, "true");
        setIsVisible(false);
        onComplete?.();
    }, [onComplete]);

    if (!isVisible) return null;

    const step = TOUR_STEPS[currentStep];

    return (
        <>
            {/* Overlay */}
            <div className="fixed inset-0 z-[9998] bg-black/60 backdrop-blur-[2px]" />

            {/* Highlight cutout */}
            {highlightRect && (
                <div
                    className="fixed z-[9999] rounded-lg ring-2 ring-accent ring-offset-2 ring-offset-transparent pointer-events-none"
                    style={{
                        top: highlightRect.top - 4,
                        left: highlightRect.left - 4,
                        width: highlightRect.width + 8,
                        height: highlightRect.height + 8,
                    }}
                />
            )}

            {/* Tooltip */}
            <div
                className="fixed z-[10000] w-[320px] rounded-xl bg-zinc-900 border border-zinc-700 shadow-2xl p-4 animate-fade-in"
                style={{ top: tooltipPos.top, left: tooltipPos.left }}
            >
                {/* Progress bar */}
                <div className="flex gap-1 mb-3">
                    {TOUR_STEPS.map((_, i) => (
                        <div
                            key={i}
                            className={cn(
                                "h-1 flex-1 rounded-full transition-colors",
                                i <= currentStep ? "bg-accent" : "bg-zinc-700"
                            )}
                        />
                    ))}
                </div>

                {/* Content */}
                <h3 className="text-sm font-semibold text-foreground mb-1.5">
                    {step.title}
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                    {step.description}
                </p>

                {/* Navigation */}
                <div className="flex items-center justify-between">
                    <button
                        onClick={handleSkip}
                        className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                    >
                        Skip tour
                    </button>
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] text-muted-foreground">
                            {currentStep + 1} / {TOUR_STEPS.length}
                        </span>
                        {currentStep > 0 && (
                            <button
                                onClick={handlePrev}
                                className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium bg-muted text-foreground hover:bg-muted/80 transition-colors"
                            >
                                <ChevronLeft className="w-3 h-3" />
                                Back
                            </button>
                        )}
                        <button
                            onClick={handleNext}
                            className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium bg-accent text-accent-foreground hover:bg-accent/90 transition-colors"
                        >
                            {currentStep === TOUR_STEPS.length - 1 ? (
                                <>
                                    <Sparkles className="w-3 h-3" />
                                    Done!
                                </>
                            ) : (
                                <>
                                    Next
                                    <ChevronRight className="w-3 h-3" />
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}

// Export a trigger to re-start the tour
export function resetTour() {
    localStorage.removeItem(TOUR_KEY);
    window.location.reload();
}
