"use client";

import React, { useState, useRef, KeyboardEvent } from "react";
import { Send, Paperclip } from "lucide-react";

interface RoundedChatInputProps {
  onSend: (message: string) => void;
  onAttach?: () => void;
  isLoading?: boolean;
  placeholder?: string;
  selectedActions?: string[];
}

export default function RoundedChatInput({
  onSend,
  onAttach,
  isLoading = false,
  placeholder = "Ask anything...",
  selectedActions = [],
}: RoundedChatInputProps) {
  const [message, setMessage] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage("");
      
      // Reset textarea height after sending
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    
    // Auto-resize textarea
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`;
    }
  };

  // Format action labels for display
  const formatActionLabel = (action: string): string => {
    const labels: Record<string, string> = {
      "deep-research": "Deep Research",
      "web-search": "Web Search",
      "analyze-pdf": "PDF Analysis",
      "paste-url": "URL Analysis",
      flashcards: "Flashcards",
    };
    return labels[action] || action;
  };

  return (
    <div className="px-4 py-4 bg-[#0D0D0D]">
      <div className="max-w-4xl mx-auto">
        {/* Selected actions indicator */}
        {selectedActions.length > 0 && (
          <div className="mb-3 flex items-center gap-2 flex-wrap">
            {selectedActions.map((action) => (
              <div
                key={action}
                className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#4F46E5]/20 border border-[#4F46E5]/40"
              >
                <div className="w-2 h-2 rounded-full bg-[#4F46E5]"></div>
                <span className="text-xs text-[#4F46E5] font-medium">
                  {formatActionLabel(action)}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Input container with rounded corners */}
        <div
          className={`
            flex items-end gap-3 px-4 py-3
            bg-[#1A1A1A] border border-[#2A2A2A]
            rounded-[28px]
            transition-all duration-200
            ${isLoading ? "opacity-50" : ""}
            focus-within:border-[#4F46E5] focus-within:shadow-lg focus-within:shadow-[#4F46E5]/20
          `}
        >
          {/* Attach button */}
          {onAttach && (
            <button
              onClick={onAttach}
              disabled={isLoading}
              className="p-2 text-[#A0A0A0] hover:text-white hover:bg-[#2A2A2A] rounded-full transition-colors disabled:opacity-50"
              aria-label="Attach file"
            >
              <Paperclip className="w-5 h-5" />
            </button>
          )}

          {/* Textarea */}
          <textarea
            ref={inputRef}
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            rows={1}
            className="
              flex-1 bg-transparent text-white
              placeholder-[#A0A0A0]
              resize-none outline-none
              min-h-[24px] max-h-[200px]
              disabled:opacity-50
            "
            style={{ 
              lineHeight: '24px',
              overflowY: 'auto',
              scrollbarWidth: 'thin',
              scrollbarColor: '#2A2A2A #1A1A1A'
            }}
          />

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={!message.trim() || isLoading}
            className={`
              p-2 rounded-full transition-all duration-200
              ${
                message.trim() && !isLoading
                  ? "bg-[#4F46E5] text-white hover:bg-[#6366F1] shadow-lg shadow-[#4F46E5]/30"
                  : "bg-[#2A2A2A] text-[#A0A0A0] cursor-not-allowed"
              }
            `}
            aria-label="Send message"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>

        {/* Helper text */}
        {!isLoading && (
          <div className="mt-2 text-xs text-center text-[#A0A0A0]">
            <kbd className="px-1.5 py-0.5 text-[10px] bg-[#1A1A1A] rounded border border-[#2A2A2A]">Enter</kbd> to send,{" "}
            <kbd className="px-1.5 py-0.5 text-[10px] bg-[#1A1A1A] rounded border border-[#2A2A2A]">Shift + Enter</kbd> for new line
          </div>
        )}
      </div>
    </div>
  );
}
