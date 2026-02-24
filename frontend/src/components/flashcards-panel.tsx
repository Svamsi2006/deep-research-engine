"use client";

import React, { useState, useCallback } from "react";
import { CreditCard, Download, RotateCcw, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FlashcardData } from "@/lib/sse-client";

interface FlashcardsPanelProps {
    cards: FlashcardData[];
    csv: string;
    isLoading: boolean;
}

function FlashcardItem({ card, index }: { card: FlashcardData; index: number }) {
    const [flipped, setFlipped] = useState(false);

    return (
        <div
            onClick={() => setFlipped(!flipped)}
            className={cn(
                "rounded-lg border p-4 cursor-pointer transition-all duration-200 select-none",
                flipped
                    ? "bg-emerald-500/10 border-emerald-500/30"
                    : "bg-muted/30 border-border hover:border-accent/40"
            )}
        >
            <div className="flex items-start gap-3">
                <span className="shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center">
                    {index + 1}
                </span>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">
                        {flipped ? card.back : card.front}
                    </p>
                    {card.tags.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                            {card.tags.map((tag) => (
                                <span
                                    key={tag}
                                    className="text-[10px] px-1.5 py-0.5 rounded bg-muted border border-border text-muted-foreground"
                                >
                                    {tag}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
                <div className="shrink-0 text-muted-foreground">
                    {flipped ? (
                        <ChevronUp className="w-4 h-4" />
                    ) : (
                        <ChevronDown className="w-4 h-4" />
                    )}
                </div>
            </div>
            <p className="text-[10px] text-muted-foreground/60 mt-2 text-right">
                {flipped ? "Answer" : "Click to flip"}
            </p>
        </div>
    );
}

export default function FlashcardsPanel({
    cards,
    csv,
    isLoading,
}: FlashcardsPanelProps) {
    const downloadCSV = useCallback(() => {
        if (!csv) return;
        const blob = new Blob([csv], { type: "text/tab-separated-values" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "flashcards_anki.tsv";
        a.click();
        URL.revokeObjectURL(url);
    }, [csv]);

    const downloadJSON = useCallback(() => {
        if (!cards.length) return;
        const blob = new Blob([JSON.stringify(cards, null, 2)], {
            type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "flashcards.json";
        a.click();
        URL.revokeObjectURL(url);
    }, [cards]);

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center">
                <div className="text-center space-y-2">
                    <RotateCcw className="w-6 h-6 mx-auto text-cyan-400 animate-spin" />
                    <p className="text-sm text-muted-foreground">
                        Generating flashcards...
                    </p>
                </div>
            </div>
        );
    }

    if (cards.length === 0) {
        return (
            <div className="flex h-full items-center justify-center">
                <div className="text-center space-y-2 max-w-xs">
                    <CreditCard className="w-8 h-8 mx-auto text-muted-foreground/40" />
                    <p className="text-sm text-muted-foreground">
                        Generate a report first, then click &quot;Flashcards&quot; to create
                        study cards.
                    </p>
                    <p className="text-xs text-muted-foreground/60">
                        Export as Anki CSV or JSON.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Header with export */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Flashcards ({cards.length})
                </h3>
                <div className="flex gap-2">
                    <button
                        onClick={downloadCSV}
                        className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                    >
                        <Download className="w-3 h-3" />
                        Anki CSV
                    </button>
                    <button
                        onClick={downloadJSON}
                        className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                    >
                        <Download className="w-3 h-3" />
                        JSON
                    </button>
                </div>
            </div>

            {/* Cards */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {cards.map((card, i) => (
                    <FlashcardItem key={i} card={card} index={i} />
                ))}
            </div>
        </div>
    );
}
