"use client";

import React, { useRef, useEffect } from 'react';
import { User, Bot, ChevronDown } from 'lucide-react';
import ReportPreviewCard from './report-card';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  thinking?: string;
  reportId?: string;
  reportTitle?: string;
  reportSummary?: string;
}

interface ChatMessagesProps {
  messages: Message[];
  onOpenReport?: (reportId: string) => void;
  isStreaming?: boolean;
}

export default function ChatMessages({
  messages,
  onOpenReport,
  isStreaming = false
}: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [expandedThinking, setExpandedThinking] = React.useState<Set<string>>(new Set());

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const toggleThinking = (messageId: string) => {
    setExpandedThinking(prev => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  };

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
            <Bot className="w-8 h-8 text-blue-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Start a conversation
          </h3>
          <p className="text-gray-600 max-w-md">
            Ask me anything or request a deep research report. I'll help you explore topics in depth.
          </p>
        </div>
      )}

      {messages.map((message) => (
        <div key={message.id} className="flex gap-3 items-start">
          {/* Avatar */}
          {message.role === 'user' ? (
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
              <User className="w-5 h-5 text-white" />
            </div>
          ) : (
            <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-white" />
            </div>
          )}

          {/* Message Content */}
          <div className="flex-1 min-w-0">
            {/* Message Header */}
            <div className="flex items-baseline gap-2 mb-1.5">
              <span className="text-sm font-semibold text-gray-900">
                {message.role === 'user' ? 'You' : 'Assistant'}
              </span>
              <span className="text-xs text-gray-500">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>

            {/* Message Bubble */}
            <div
              className={`rounded-2xl px-4 py-3 ${message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-900'
                }`}
            >
              {/* Thinking Toggle (only for assistant) */}
              {message.thinking && message.role === 'assistant' && (
                <button
                  onClick={() => toggleThinking(message.id)}
                  className="flex items-center gap-2 text-sm mb-3 opacity-70 hover:opacity-100 transition-opacity"
                >
                  <ChevronDown
                    className={`w-4 h-4 transition-transform ${expandedThinking.has(message.id) ? 'rotate-180' : ''
                      }`}
                  />
                  <span>{expandedThinking.has(message.id) ? 'Hide' : 'Show'} thinking</span>
                </button>
              )}

              {/* Thinking Content */}
              {expandedThinking.has(message.id) && message.thinking && (
                <div className="mb-3 p-3 bg-white/10 rounded-lg text-sm font-mono opacity-80">
                  {message.thinking}
                </div>
              )}

              {/* Main Content */}
              <div className="whitespace-pre-wrap break-words leading-relaxed">
                {message.content}
              </div>
            </div>

            {/* Report Card (if this message has a report) */}
            {message.reportId && onOpenReport && (
              <ReportPreviewCard
                reportId={message.reportId}
                title={message.reportTitle || 'Research Report'}
                timestamp={message.timestamp}
                summary={message.reportSummary}
                onOpen={() => onOpenReport(message.reportId!)}
              />
            )}
          </div>
        </div>
      ))}

      {/* Streaming Indicator */}
      {isStreaming && (
        <div className="flex gap-3 items-start">
          <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <div className="flex items-baseline gap-2 mb-1.5">
              <span className="text-sm font-semibold text-gray-900">Assistant</span>
              <span className="text-xs text-gray-500">typing...</span>
            </div>
            <div className="bg-gray-100 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
