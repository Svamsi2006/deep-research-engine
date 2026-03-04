"use client";

import React from "react";
import { ExternalLink, FileText } from "lucide-react";
import type { SourceInfo } from "@/lib/sse-client";

interface SourcesPanelProps {
    sources: SourceInfo[];
}

export default function SourcesPanel({ sources }: SourcesPanelProps) {
    if (sources.length === 0) {
        return (
            <div className="flex h-full items-center justify-center">
                <div className="text-center space-y-2 max-w-xs">
                    <FileText className="w-8 h-8 mx-auto text-muted-foreground/40" />
                    <p className="text-sm text-muted-foreground">
                        Sources used in the report will appear here.
                    </p>
                    <p className="text-xs text-muted-foreground/60">
                        Each citation in the report links back to its source.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-4 space-y-2 overflow-y-auto h-full">
            <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
                Sources Used ({sources.length})
            </h3>
            {sources.map((src, i) => (
                <div
                    key={src.source_id || src.title || String(i)}
                    className="flex items-start gap-3 rounded-lg border border-border bg-muted/30 p-3"
                >
                    <span className="shrink-0 w-6 h-6 rounded-full bg-accent/20 text-accent text-xs font-bold flex items-center justify-center">
                        {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-foreground truncate">
                            {src.title}
                        </p>
                        <p className="text-xs text-muted-foreground font-mono mt-0.5 mb-2 break-all">
                            {src.url ? (
                                <a href={src.url} target="_blank" rel="noreferrer" className="underline hover:text-foreground">
                                    {src.url}
                                </a>
                            ) : (
                                <>ID: {(src.source_id || "").slice(0, 24)}</>
                            )}
                        </p>
                        {src.snippets && src.snippets.length > 0 && (
                            <div className="space-y-2 mt-2">
                                {src.snippets.map((snippet, idx) => (
                                    <div
                                        key={idx}
                                        className="bg-background/50 rounded p-2 text-[11px] text-muted-foreground leading-relaxed border border-border/50 italic"
                                    >
                                        &quot;{snippet.length > 300 ? snippet.slice(0, 300) + '...' : snippet}&quot;
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
                </div>
            ))}
        </div>
    );
}
