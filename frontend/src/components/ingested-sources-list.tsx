"use client";

import React from "react";
import { FileText, Link as LinkIcon, X, CheckCircle2, ChevronRight } from "lucide-react";

export interface IngestedSource {
  sourceId: string;
  title: string;
  type: 'pdf' | 'url';
  chunkCount: number;
  timestamp: string;
}

interface IngestedSourcesListProps {
  sources: IngestedSource[];
  selectedSourceIds: string[];
  onToggleSource: (sourceId: string) => void;
  onRemoveSource: (sourceId: string) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
}

export default function IngestedSourcesList({
  sources,
  selectedSourceIds,
  onToggleSource,
  onRemoveSource,
  onSelectAll,
  onClearAll,
}: IngestedSourcesListProps) {
  if (sources.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="inline-flex p-4 rounded-full bg-[#1A1A1A] mb-4">
          <FileText className="w-8 h-8 text-[#A0A0A0]" />
        </div>
        <p className="text-sm text-[#A0A0A0] mb-2">No sources ingested yet</p>
        <p className="text-xs text-[#666]">Upload PDFs or paste URLs to get started</p>
      </div>
    );
  }

  const allSelected = sources.length > 0 && selectedSourceIds.length === sources.length;
  const someSelected = selectedSourceIds.length > 0 && selectedSourceIds.length < sources.length;

  return (
    <div className="flex flex-col h-full">
      {/* Header with bulk actions */}
      <div className="px-4 py-3 border-b border-[#2A2A2A] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">
            Sources ({sources.length})
          </span>
          {selectedSourceIds.length > 0 && (
            <span className="text-xs text-[#4F46E5] bg-[#4F46E5]/10 px-2 py-0.5 rounded-full">
              {selectedSourceIds.length} selected
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {sources.length > 0 && (
            <button
              onClick={allSelected ? onClearAll : onSelectAll}
              className="text-xs text-[#4F46E5] hover:text-[#6366F1] transition-colors font-medium"
            >
              {allSelected ? 'Deselect All' : 'Select All'}
            </button>
          )}
        </div>
      </div>

      {/* Sources list */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-2">
          {sources.map((source) => {
            const isSelected = selectedSourceIds.includes(source.sourceId);
            const Icon = source.type === 'pdf' ? FileText : LinkIcon;

            return (
              <div
                key={source.sourceId}
                className={`
                  group relative p-4 rounded-lg border transition-all duration-200 cursor-pointer
                  ${isSelected 
                    ? 'bg-[#4F46E5]/10 border-[#4F46E5]/30' 
                    : 'bg-[#1A1A1A] border-[#2A2A2A] hover:bg-[#1A1A1A]/80 hover:border-[#3A3A3A]'
                  }
                `}
                onClick={() => onToggleSource(source.sourceId)}
              >
                {/* Remove button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveSource(source.sourceId);
                  }}
                  className="absolute top-2 right-2 p-1.5 rounded-md bg-[#0D0D0D]/80 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 transition-all"
                  title="Remove source"
                >
                  <X className="w-4 h-4 text-[#A0A0A0] hover:text-red-400" />
                </button>

                {/* Selection indicator */}
                {isSelected && (
                  <div className="absolute top-3 right-3">
                    <CheckCircle2 className="w-5 h-5 text-[#4F46E5]" />
                  </div>
                )}

                {/* Source info */}
                <div className="flex items-start gap-3 pr-8">
                  <div className={`
                    p-2 rounded-lg flex-shrink-0
                    ${isSelected ? 'bg-[#4F46E5]/20' : 'bg-[#2A2A2A]'}
                  `}>
                    <Icon className={`w-5 h-5 ${isSelected ? 'text-[#4F46E5]' : 'text-[#A0A0A0]'}`} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <h3 className={`text-sm font-medium truncate mb-1 ${isSelected ? 'text-white' : 'text-[#E0E0E0]'}`}>
                      {source.title}
                    </h3>
                    
                    <div className="flex items-center gap-3 text-xs text-[#A0A0A0]">
                      <span className="flex items-center gap-1">
                        <span className={isSelected ? 'text-[#4F46E5]' : 'text-[#666]'}>
                          {source.chunkCount} chunks
                        </span>
                      </span>
                      <span>•</span>
                      <span>
                        {new Date(source.timestamp).toLocaleString(undefined, { 
                          month: 'short', 
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    </div>
                  </div>

                  <ChevronRight className={`
                    w-4 h-4 flex-shrink-0 transition-transform
                    ${isSelected ? 'text-[#4F46E5] rotate-90' : 'text-[#666]'}
                  `} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer hint */}
      {selectedSourceIds.length > 0 && (
        <div className="px-4 py-3 border-t border-[#2A2A2A] bg-[#0D0D0D]">
          <p className="text-xs text-[#A0A0A0]">
            <span className="font-medium text-[#4F46E5]">{selectedSourceIds.length}</span> source{selectedSourceIds.length !== 1 ? 's' : ''} will be used for your research
          </p>
        </div>
      )}
    </div>
  );
}
