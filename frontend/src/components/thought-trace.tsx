"use client";

import React from "react";
import {
  Search,
  Download,
  FileText,
  Brain,
  CheckCircle,
  FileOutput,
  AlertCircle,
  Loader2,
  GitBranch,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ThoughtEvent } from "@/lib/sse-client";

const NODE_CONFIG: Record<
  string,
  { icon: React.ElementType; label: string; color: string }
> = {
  system: {
    icon: Loader2,
    label: "System",
    color: "text-zinc-400",
  },
  discovery: {
    icon: Search,
    label: "Discovery",
    color: "text-blue-400",
  },
  harvest: {
    icon: Download,
    label: "Harvest",
    color: "text-purple-400",
  },
  clean: {
    icon: FileText,
    label: "Clean",
    color: "text-amber-400",
  },
  reasoning: {
    icon: Brain,
    label: "Reasoning",
    color: "text-pink-400",
  },
  evaluation: {
    icon: CheckCircle,
    label: "Evaluation",
    color: "text-cyan-400",
  },
  synthesis: {
    icon: FileOutput,
    label: "Synthesis",
    color: "text-emerald-400",
  },
};

interface ThoughtTraceProps {
  thoughts: ThoughtEvent[];
  isRunning: boolean;
}

export default function ThoughtTrace({ thoughts, isRunning }: ThoughtTraceProps) {
  if (thoughts.length === 0 && !isRunning) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <p className="text-xs text-muted-foreground">
          Agent activity will appear here during research.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-3 space-y-1">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-semibold mb-2 px-1">
        Agent Trace
      </div>
      {thoughts.map((thought, i) => {
        const config = NODE_CONFIG[thought.node] || NODE_CONFIG.system;
        const Icon = config.icon;
        const isActive = thought.status === "running";
        const isError = thought.status === "error";

        return (
          <div
            key={i}
            className={cn(
              "flex items-start gap-2 px-2 py-1.5 rounded-md text-xs animate-fade-in",
              isActive && "bg-muted/50",
              isError && "bg-red-500/10"
            )}
          >
            {/* Timeline dot & line */}
            <div className="flex flex-col items-center mt-0.5">
              <div
                className={cn(
                  "rounded-full p-1",
                  isActive && "animate-pulse",
                  isError
                    ? "bg-red-500/20 text-red-400"
                    : thought.status === "completed"
                      ? "bg-emerald-500/20 text-emerald-400"
                      : `bg-zinc-800 ${config.color}`
                )}
              >
                {isError ? (
                  <AlertCircle className="w-3 h-3" />
                ) : isActive ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : thought.status === "completed" ? (
                  <CheckCircle className="w-3 h-3" />
                ) : (
                  <Icon className="w-3 h-3" />
                )}
              </div>
              {i < thoughts.length - 1 && (
                <div className="w-px h-full min-h-[8px] bg-border/50 mt-0.5" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <span
                className={cn(
                  "font-medium",
                  isError ? "text-red-400" : config.color
                )}
              >
                {config.label}
              </span>
              <p className="text-muted-foreground leading-snug mt-0.5 break-words">
                {thought.message}
              </p>
            </div>
          </div>
        );
      })}

      {isRunning && (
        <div className="flex items-center gap-2 px-2 py-1.5 text-xs text-muted-foreground">
          <Loader2 className="w-3 h-3 animate-spin" />
          Processing...
        </div>
      )}
    </div>
  );
}
