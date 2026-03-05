"use client";

import React, { useState } from 'react';
import { Plus, ChevronLeft, Trash2 } from 'lucide-react';

interface Conversation {
  id: string;
  title: string;
  created_at?: string;
}

interface ModernSidebarProps {
  userId: string;
  conversations: Conversation[];
  currentConversationId?: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation?: (id: string) => void;
}

export default function ModernSidebar({
  userId,
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
}: ModernSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    if (diffMins < 10080) return `${Math.floor(diffMins / 1440)}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div
      className={`sidebar bg-[#111111] border-r border-[#2A2A2A] flex flex-col h-screen transition-all duration-300 ease-in-out ${
        isCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Header with Logo and Collapse Button */}
      <div className="flex items-center justify-between p-4 border-b border-[#2A2A2A]">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-[#4F46E5] to-[#7C3AED] rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">⚡</span>
            </div>
            <span className="text-sm font-semibold text-white">Research</span>
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 hover:bg-[#1A1A1A] rounded-lg transition-colors duration-200"
          title={isCollapsed ? 'Expand' : 'Collapse'}
        >
          <ChevronLeft
            className={`w-5 h-5 text-[#A0A0A0] transition-transform duration-300 ${
              isCollapsed ? 'rotate-180' : ''
            }`}
          />
        </button>
      </div>

      {/* New Conversation Button */}
      <button
        onClick={onNewConversation}
        className={`m-3 bg-[#4F46E5] hover:bg-[#6366F1] text-white rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 h-11 ${
          isCollapsed ? 'px-3' : 'px-4'
        }`}
      >
        <Plus className="w-5 h-5" />
        {!isCollapsed && <span>New Chat</span>}
      </button>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-2 py-3">
        {conversations.length === 0 && !isCollapsed && (
          <div className="text-center py-8">
            <p className="text-xs text-[#A0A0A0]">No conversations yet</p>
          </div>
        )}

        <div className="space-y-1">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className="group"
              onMouseEnter={() => setHoveredId(conv.id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              <button
                onClick={() => onSelectConversation(conv.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-all duration-200 flex items-center justify-between ${
                  currentConversationId === conv.id
                    ? 'bg-[#2A2A2A] border-l-3 border-l-[#4F46E5] text-white'
                    : 'text-[#A0A0A0] hover:bg-[#1A1A1A] hover:text-white'
                }`}
              >
                <span
                  className={`truncate text-sm ${
                    isCollapsed ? 'hidden' : ''
                  }`}
                  title={conv.title}
                >
                  {conv.title}
                </span>
                {isCollapsed && (
                  <div className="w-8 h-8 bg-[#1A1A1A] rounded flex items-center justify-center">
                    <span className="text-xs font-bold text-[#4F46E5]">💬</span>
                  </div>
                )}
              </button>

              {/* Delete Button (shown on hover) */}
              {hoveredId === conv.id && !isCollapsed && onDeleteConversation && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-red-500/20 rounded transition-colors"
                  title="Delete conversation"
                >
                  <Trash2 className="w-4 h-4 text-red-400 opacity-0 group-hover:opacity-100" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      {!isCollapsed && (
        <div className="border-t border-[#2A2A2A] p-4 text-xs text-[#A0A0A0]">
          <p>Deep Research Agent</p>
          <p className="text-[10px] mt-1">v0.3 • Dark Mode</p>
        </div>
      )}
    </div>
  );
}
