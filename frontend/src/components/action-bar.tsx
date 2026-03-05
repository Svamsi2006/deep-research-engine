"use client";

import React from "react";
import { Search, FileText, Link as LinkIcon, BookOpen, Globe, Plus } from "lucide-react";

type ActionType = "deep-research" | "web-search" | "analyze-pdf" | "paste-url" | "flashcards";

interface ActionBarProps {
  selectedActions: ActionType[];
  onSelectActions: (actions: ActionType[]) => void;
  onToggleExpanded?: () => void;
  isExpanded?: boolean;
}

export default function ActionBar({
  selectedActions,
  onSelectActions,
  onToggleExpanded,
  isExpanded = true,
}: ActionBarProps) {
  const actions = [
    {
      id: "deep-research" as ActionType,
      label: "Deep Research",
      icon: Search,
      description: "Comprehensive research with citations",
    },
    {
      id: "web-search" as ActionType,
      label: "Web Search",
      icon: Globe,
      description: "Quick web search results",
    },
    {
      id: "analyze-pdf" as ActionType,
      label: "Analyze PDF",
      icon: FileText,
      description: "Extract insights from PDFs",
    },
    {
      id: "paste-url" as ActionType,
      label: "Paste URL",
      icon: LinkIcon,
      description: "Analyze web pages",
    },
    {
      id: "flashcards" as ActionType,
      label: "Flash Cards",
      icon: BookOpen,
      description: "Generate study flashcards",
    },
  ];

  return (
    <div className="flex items-center gap-2 px-4 py-3 bg-[#0D0D0D] border-b border-[#2A2A2A]">
      {/* Plus icon to toggle actions */}
      <button
        onClick={onToggleExpanded}
        className="p-2 rounded-lg hover:bg-[#1A1A1A] transition-colors"
        aria-label="Toggle actions"
      >
        <Plus
          className={`w-5 h-5 text-[#A0A0A0] transition-transform duration-200 ${
            isExpanded ? "rotate-45" : ""
          }`}
        />
      </button>

      {/* Action buttons */}
      {isExpanded && (
        <div className="flex items-center gap-2 flex-1 overflow-x-auto scrollbar-hide">
          {actions.map((action) => {
            const Icon = action.icon;
            const isSelected = selectedActions.includes(action.id);

            const toggleAction = () => {
              if (isSelected) {
                onSelectActions(selectedActions.filter(a => a !== action.id));
              } else {
                onSelectActions([...selectedActions, action.id]);
              }
            };

            return (
              <button
                key={action.id}
                onClick={toggleAction}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-full
                  text-sm font-medium whitespace-nowrap
                  transition-all duration-200
                  ${
                    isSelected
                      ? "bg-[#4F46E5] text-white shadow-lg shadow-[#4F46E5]/30"
                      : "bg-[#1A1A1A] text-[#A0A0A0] hover:bg-[#2A2A2A] hover:text-white"
                  }
                `}
                title={action.description}
              >
                <Icon className="w-4 h-4" />
                <span>{action.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
