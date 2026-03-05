"use client";

import React from 'react';
import { FileText, ExternalLink } from 'lucide-react';

interface ReportPreviewCardProps {
  reportId: string;
  title: string;
  timestamp: string;
  summary?: string;
  onOpen: () => void;
}

export default function ReportPreviewCard({
  reportId,
  title,
  timestamp,
  summary,
  onOpen
}: ReportPreviewCardProps) {
  const formatTimestamp = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="my-4 border border-gray-200 rounded-xl bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden">
      {/* Card Header */}
      <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-black mb-1 line-clamp-2">
                {title}
              </h3>
              <p className="text-xs text-black">
                {formatTimestamp(timestamp)}
              </p>
            </div>
          </div>

          <button
            onClick={onOpen}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 whitespace-nowrap"
          >
            Open
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Card Body - Summary */}
      {summary && (
        <div className="p-4">
          <p className="text-sm text-black leading-relaxed line-clamp-3">
            {summary}
          </p>
        </div>
      )}

      {/* Card Footer */}
      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center gap-4 text-xs text-black">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
            Research Report
          </span>
          <span>•</span>
          <span>Deep Analysis</span>
        </div>
      </div>
    </div>
  );
}
