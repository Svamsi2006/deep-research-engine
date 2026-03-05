"use client";

import React, { useState, useRef } from 'react';
import { Send, Paperclip, Plus, Zap, BookOpen } from 'lucide-react';

interface ModernInputProps {
  onAnswerClick?: (question: string) => void;
  onReportClick?: (question: string) => void;
  onFlashcardsClick?: (question: string) => void;
  onAttachClick?: () => void;
  isLoading?: boolean;
  placeholder?: string;
}

export default function ModernInput({
  onAnswerClick,
  onReportClick,
  onFlashcardsClick,
  onAttachClick,
  isLoading = false,
  placeholder = 'Ask something incredible...',
}: ModernInputProps) {
  const [question, setQuestion] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSendAnswer = () => {
    if (question.trim() && onAnswerClick) {
      onAnswerClick(question);
      setQuestion('');
    }
  };

  const handleSendReport = () => {
    if (question.trim() && onReportClick) {
      onReportClick(question);
      setQuestion('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendAnswer();
    }
  };

  return (
    <div className="card bg-[#1A1A1A] border border-[#2A2A2A] rounded-xl p-4 m-4">
      {/* Input Box */}
      <div
        className={`flex items-end gap-3 transition-all duration-200 ${
          isFocused ? 'ring-1 ring-[#4F46E5]' : ''
        }`}
      >
        {/* Attach Button */}
        {onAttachClick && (
          <button
            onClick={onAttachClick}
            className="p-3 hover:bg-[#2A2A2A] rounded-lg transition-colors duration-200 flex-shrink-0"
            title="Attach files"
            disabled={isLoading}
          >
            <Paperclip className="w-5 h-5 text-[#A0A0A0]" />
          </button>
        )}

        {/* Input Field */}
        <div className="flex-1">
          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            className="w-full bg-transparent text-white placeholder-[#A0A0A0] focus:outline-none text-sm"
            disabled={isLoading}
          />
        </div>

        {/* Send Button */}
        <button
          onClick={handleSendAnswer}
          className="p-3 bg-[#4F46E5] hover:bg-[#6366F1] rounded-lg transition-colors duration-200 flex-shrink-0 disabled:opacity-50"
          title="Quick answer"
          disabled={isLoading || !question.trim()}
        >
          <Send className="w-5 h-5 text-white" />
        </button>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 mt-4 flex-wrap">
        <button
          onClick={handleSendAnswer}
          disabled={isLoading || !question.trim()}
          className="px-4 py-2 bg-[#4F46E5]/20 hover:bg-[#4F46E5]/30 text-[#4F46E5] rounded-lg text-sm font-medium transition-colors duration-200 flex items-center gap-2 disabled:opacity-50"
        >
          <Zap className="w-4 h-4" />
          Quick Answer
        </button>

        <button
          onClick={handleSendReport}
          disabled={isLoading || !question.trim()}
          className="px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center gap-2 disabled:opacity-50"
        >
          <BookOpen className="w-4 h-4" />
          Deep Report
        </button>

        {onFlashcardsClick && (
          <button
            onClick={() => onFlashcardsClick(question)}
            disabled={isLoading || !question.trim()}
            className="px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg text-sm font-medium transition-colors duration-200 flex items-center gap-2 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            Flashcards
          </button>
        )}
      </div>

      {/* Help text */}
      {!isFocused && (
        <p className="text-xs text-[#A0A0A0] mt-3">
          💡 Press Enter to send, Shift + Enter for new line
        </p>
      )}
    </div>
  );
}
