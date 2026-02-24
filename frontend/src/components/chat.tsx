"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { Send, Loader2, StopCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  streamChat,
  ThoughtEvent,
  ReportChunk,
  DoneEvent,
} from "@/lib/sse-client";

interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

interface ChatProps {
  onThought: (event: ThoughtEvent) => void;
  onReportChunk: (chunk: ReportChunk) => void;
  onDone: (event: DoneEvent) => void;
  onStart: () => void;
}

export default function Chat({
  onThought,
  onReportChunk,
  onDone,
  onStart,
}: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const query = input.trim();
      if (!query || isLoading) return;

      setInput("");
      setIsLoading(true);
      onStart();

      // Add user message
      const userMsg: ChatMessage = {
        role: "user",
        content: query,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // Add loading message
      const loadingMsg: ChatMessage = {
        role: "system",
        content: "Running research pipeline...",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, loadingMsg]);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat(
          query,
          {
            onThought,
            onReportChunk,
            onDone: (event) => {
              setMessages((prev) => {
                const filtered = prev.filter((m) => m.role !== "system");
                return [
                  ...filtered,
                  {
                    role: "assistant",
                    content: `Research complete! Score: ${(event.evaluation_score * 100).toFixed(1)}%${event.quality_warning ? " ⚠️" : ""}. Check the report panel →`,
                    timestamp: new Date(),
                  },
                ];
              });
              onDone(event);
              setIsLoading(false);
            },
            onError: (error) => {
              setMessages((prev) => {
                const filtered = prev.filter((m) => m.role !== "system");
                return [
                  ...filtered,
                  {
                    role: "assistant",
                    content: `Error: ${error}`,
                    timestamp: new Date(),
                  },
                ];
              });
              setIsLoading(false);
            },
          },
          controller.signal
        );
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          setMessages((prev) => {
            const filtered = prev.filter((m) => m.role !== "system");
            return [
              ...filtered,
              {
                role: "assistant",
                content: "Research cancelled.",
                timestamp: new Date(),
              },
            ];
          });
        }
        setIsLoading(false);
      }
    },
    [input, isLoading, onThought, onReportChunk, onDone, onStart]
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
      }
    },
    [handleSubmit]
  );

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <div className="text-center space-y-3 max-w-md">
              <div className="text-4xl">🔬</div>
              <h2 className="text-lg font-semibold text-foreground">
                Engineering Oracle
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Ask any engineering research question. The multi-agent pipeline
                will search, scrape, analyze, and synthesize a comprehensive
                report.
              </p>
              <div className="text-xs text-muted-foreground space-y-1 pt-2">
                <p className="font-medium text-foreground/70">Try:</p>
                <p>&quot;Compare Mamba vs Transformer for production&quot;</p>
                <p>&quot;RLHF vs DPO training approaches 2025&quot;</p>
                <p>&quot;Rust vs Go for microservices performance&quot;</p>
              </div>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "animate-fade-in rounded-lg px-4 py-2.5 text-sm max-w-[85%]",
              msg.role === "user" &&
                "ml-auto bg-accent/20 text-accent-foreground border border-accent/30",
              msg.role === "assistant" && "bg-muted text-foreground border border-border",
              msg.role === "system" &&
                "bg-muted/50 text-muted-foreground border border-border/50 italic text-xs"
            )}
          >
            {msg.role === "system" && (
              <Loader2 className="inline-block w-3 h-3 mr-1.5 animate-spin" />
            )}
            {msg.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-border p-3 flex gap-2 items-end"
      >
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a research question..."
          rows={1}
          className={cn(
            "flex-1 resize-none rounded-lg bg-muted border border-border px-3 py-2.5",
            "text-sm text-foreground placeholder:text-muted-foreground",
            "focus:outline-none focus:ring-1 focus:ring-ring",
            "min-h-[40px] max-h-[120px]"
          )}
          disabled={isLoading}
        />
        {isLoading ? (
          <button
            type="button"
            onClick={handleStop}
            className="rounded-lg bg-red-500/20 border border-red-500/40 p-2.5 text-red-400 hover:bg-red-500/30 transition-colors"
          >
            <StopCircle className="w-4 h-4" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className={cn(
              "rounded-lg p-2.5 transition-colors",
              input.trim()
                ? "bg-accent text-accent-foreground hover:bg-accent/90"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            <Send className="w-4 h-4" />
          </button>
        )}
      </form>
    </div>
  );
}
