"use client";

import React, { useState, useCallback } from "react";
import { X, Link as LinkIcon, Loader2, CheckCircle2, AlertCircle, Globe } from "lucide-react";

interface URLIngestDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onIngestComplete: (sourceId: string, title: string, chunkCount: number) => void;
}

export default function URLIngestDialog({ isOpen, onClose, onIngestComplete }: URLIngestDialogProps) {
  const [url, setUrl] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const isValidUrl = useCallback((urlString: string) => {
    try {
      const url = new URL(urlString);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
    }
  }, []);

  const handleIngest = useCallback(async () => {
    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    if (!isValidUrl(url)) {
      setError('Please enter a valid URL (must start with http:// or https://)');
      return;
    }

    setIngesting(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await fetch('/api/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_type: 'url',
          payload: url.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ingestion failed');
      }

      const data = await response.json();
      setSuccess(true);
      onIngestComplete(data.source_id, data.title, data.chunk_count);

      // Close dialog after 1.5 seconds
      setTimeout(() => {
        onClose();
        setSuccess(false);
        setUrl("");
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ingestion failed');
    } finally {
      setIngesting(false);
    }
  }, [url, isValidUrl, onClose, onIngestComplete]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !ingesting) {
      handleIngest();
    }
  }, [handleIngest, ingesting]);

  const handleClose = useCallback(() => {
    if (!ingesting) {
      onClose();
      setUrl("");
      setError(null);
      setSuccess(false);
    }
  }, [ingesting, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0D0D0D] border border-[#2A2A2A] rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2A2A2A]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#4F46E5]/10">
              <LinkIcon className="w-5 h-5 text-[#4F46E5]" />
            </div>
            <h2 className="text-lg font-semibold text-white">Paste URL</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-lg hover:bg-[#1A1A1A] transition-colors"
            disabled={ingesting}
          >
            <X className="w-5 h-5 text-[#A0A0A0]" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {ingesting ? (
            <div className="flex flex-col items-center text-center py-8">
              <Loader2 className="w-12 h-12 text-[#4F46E5] animate-spin mb-4" />
              <p className="text-white font-medium mb-2">Processing URL...</p>
              <p className="text-sm text-[#A0A0A0]">Scraping content and creating chunks</p>
            </div>
          ) : success ? (
            <div className="flex flex-col items-center text-center py-8">
              <CheckCircle2 className="w-12 h-12 text-green-500 mb-4" />
              <p className="text-white font-medium mb-2">URL Processed!</p>
              <p className="text-sm text-[#A0A0A0]">Content has been ingested successfully</p>
            </div>
          ) : (
            <>
              {/* URL Input */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-white">
                  Enter URL to analyze
                </label>
                <div className="relative">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2">
                    <Globe className="w-5 h-5 text-[#A0A0A0]" />
                  </div>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="https://example.com/article"
                    className="w-full pl-12 pr-4 py-3 bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg text-white placeholder-[#666] focus:outline-none focus:border-[#4F46E5] focus:ring-2 focus:ring-[#4F46E5]/20 transition-all"
                    autoFocus
                  />
                </div>
              </div>

              {/* Error message */}
              {error && (
                <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-400">Ingestion Failed</p>
                    <p className="text-xs text-red-300/80 mt-1">{error}</p>
                  </div>
                </div>
              )}

              {/* Info */}
              <div className="mt-4 p-4 bg-[#1A1A1A] rounded-lg">
                <p className="text-xs text-[#A0A0A0]">
                  <span className="font-medium text-white">Note:</span> The web page will be scraped and processed into chunks for analysis. Works best with article-style content.
                </p>
              </div>

              {/* Actions */}
              <div className="mt-6 flex gap-3">
                <button
                  onClick={handleClose}
                  className="flex-1 px-4 py-2.5 bg-[#1A1A1A] text-white rounded-lg font-medium hover:bg-[#2A2A2A] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleIngest}
                  disabled={!url.trim()}
                  className="flex-1 px-4 py-2.5 bg-[#4F46E5] text-white rounded-lg font-medium hover:bg-[#4338CA] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  <LinkIcon className="w-4 h-4" />
                  Ingest URL
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
