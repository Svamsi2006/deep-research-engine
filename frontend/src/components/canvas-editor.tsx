"use client";

import React, { useState, useEffect } from 'react';
import { X, Download, Share2, Zap } from 'lucide-react';
import { streamFlashcards, FlashcardData, SSECallbacks } from '@/lib/sse-client';

interface CanvasEditorProps {
  reportId: string;
  onClose: () => void;
  report?: Report; // Optional: pass report directly
}

interface Report {
  id: string;
  title: string;
  content: string;
  created_at: string;
  conversation_id?: string;
}

export default function CanvasEditor({ reportId, onClose, report: providedReport }: CanvasEditorProps) {
  const [report, setReport] = useState<Report | null>(providedReport || null);
  const [isLoading, setIsLoading] = useState(!providedReport);
  const [error, setError] = useState<string | null>(null);
  const [showFlashcards, setShowFlashcards] = useState(false);
  const [flashcards, setFlashcards] = useState<FlashcardData[]>([]);
  const [isGeneratingFlashcards, setIsGeneratingFlashcards] = useState(false);

  useEffect(() => {
    if (providedReport) {
      setReport(providedReport);
      setIsLoading(false);
    } else {
      loadReport();
    }
  }, [reportId, providedReport]);

  const loadReport = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/reports/${reportId}`);
      
      if (!response.ok) {
        throw new Error('Failed to load report');
      }
      
      const data = await response.json();
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load report');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (!report) return;
    
    const blob = new Blob([report.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title.replace(/\s+/g, '_')}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleShare = async () => {
    if (!report) return;
    
    try {
      await navigator.clipboard.writeText(report.content);
      alert('Report copied to clipboard!');
    } catch (err) {
      alert('Failed to copy to clipboard');
    }
  };

  const handleGenerateFlashcards = async () => {
    if (!report || isGeneratingFlashcards) return;
    
    setIsGeneratingFlashcards(true);
    setFlashcards([]);
    setShowFlashcards(true);

    const callbacks: SSECallbacks = {
      onFlashcards: (event) => {
        setFlashcards(event.cards);
        setIsGeneratingFlashcards(false);
      },
      onError: (error) => {
        console.error('Flashcard generation error:', error);
        alert('Failed to generate flashcards: ' + error);
        setIsGeneratingFlashcards(false);
      },
      onThought: () => {},
      onReportChunk: () => {},
      onDone: () => {
        setIsGeneratingFlashcards(false);
      },
    };

    try {
      await streamFlashcards(
        report.id,
        report.content,
        report.title,
        callbacks
      );
    } catch (err) {
      console.error('Flashcard generation failed:', err);
      setIsGeneratingFlashcards(false);
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-white z-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-black">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="fixed inset-0 bg-white z-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || 'Report not found'}</p>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-white z-50 flex flex-col">
      {/* Toolbar */}
      <div className="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          {/* Left side - Document title */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-medium text-black">{report.title}</h1>
              <p className="text-xs text-black">
                {new Date(report.created_at).toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </p>
            </div>
          </div>

          {/* Right side - Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerateFlashcards}
              disabled={isGeneratingFlashcards}
              className={`px-3 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                showFlashcards 
                  ? 'bg-purple-100 text-purple-700 hover:bg-purple-200' 
                  : 'hover:bg-gray-100 text-black'
              } disabled:opacity-50`}
              title="Generate Flashcards"
            >
              <Zap className="w-4 h-4" />
              <span className="text-sm font-medium">
                {isGeneratingFlashcards ? 'Generating...' : 'Flashcards'}
              </span>
            </button>
            <div className="w-px h-6 bg-gray-300 mx-1"></div>
            <button
              onClick={handleDownload}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Download"
            >
              <Download className="w-5 h-5 text-black" />
            </button>
            <button
              onClick={handleShare}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Share"
            >
              <Share2 className="w-5 h-5 text-black" />
            </button>
            <div className="w-px h-6 

1/1

Next.js 15.5.12 (outdated)
Webpack
Runtime Error


ENOENT: no such file or directory, open 'C:\Users\vamsi\OneDrive\Desktop\deep_research_agent\frontend\.next\server\app\page.js'

Call Stack
27

Show 27 ignore-listed frame(s)
1-gray-300 mx-2"></div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Close"
            >
              <X className="w-5 h-5 text-black" />
            </button>
          </div>
        </div>
      </div>

      {/* Document Content - Split View */}
      <div className="flex-1 overflow-hidden bg-gray-50 flex">
        {/* Left side - Report Content */}
        <div className={`overflow-y-auto ${showFlashcards ? 'w-1/2 border-r border-gray-300' : 'w-full'}`}>
          <div className="max-w-4xl mx-auto px-8 py-12">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 md:p-12">
              {/* Document Header */}
              <div className="mb-8 pb-6 border-b border-gray-200">
                <h1 className="text-3xl font-bold text-black mb-3">
                  {report.title}
                </h1>
                <div className="flex items-center gap-4 text-sm text-black">
                  <span>Research Report</span>
                  <span>•</span>
                  <span>Generated by Deep Research Agent</span>
                </div>
              </div>

              {/* Document Body - Render Markdown */}
              <div className="prose prose-lg max-w-none">
                <div 
                  className="markdown-content"
                  dangerouslySetInnerHTML={{ __html: formatMarkdown(report.content) }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right side - Flashcards Panel */}
        {showFlashcards && (
          <div className="w-1/2 overflow-y-auto bg-white">
            <div className="p-8">
              <div className="mb-6 flex items-center justify-between">
                <h2 className="text-2xl font-bold text-black">Flashcards</h2>
                <button
                  onClick={() => setShowFlashcards(false)}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Hide Flashcards"
                >
                  <X className="w-5 h-5 text-black" />
                </button>
              </div>

              {isGeneratingFlashcards && (
                <div className="flex items-center justify-center py-12">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-black">Generating flashcards...</p>
                  </div>
                </div>
              )}

              {!isGeneratingFlashcards && flashcards.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-black">No flashcards generated yet.</p>
                  <p className="text-sm text-black mt-2">Click the Flashcards button to generate.</p>
                </div>
              )}

              {flashcards.length > 0 && (
                <div className="space-y-4">
                  {flashcards.map((card, index) => (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-gradient-to-br from-purple-50 to-white"
                    >
                      <div className="mb-4">
                        <div className="text-xs font-semibold text-purple-600 mb-2">QUESTION</div>
                        <p className="text-black font-medium">{card.front}</p>
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-purple-600 mb-2">ANSWER</div>
                        <p className="text-black leading-relaxed">{card.back}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Simple Markdown formatter (you can replace with a proper library like marked.js)
function formatMarkdown(content: string): string {
  let html = content
    // Headers
    .replace(/^### (.*$)/gim, '<h3 class="text-xl font-semibold mt-6 mb-3 text-black">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-2xl font-bold mt-8 mb-4 text-black">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="text-3xl font-bold mt-8 mb-4 text-black">$1</h1>')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-black">$1</strong>')
    // Italic
    .replace(/\*(.*?)\*/g, '<em class="italic">$1</em>')
    // Lists
    .replace(/^\* (.*$)/gim, '<li class="ml-4 mb-2">$1</li>')
    .replace(/^- (.*$)/gim, '<li class="ml-4 mb-2">$1</li>')
    .replace(/^\d+\. (.*$)/gim, '<li class="ml-4 mb-2">$1</li>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank" rel="noopener">$1</a>')
    // Code blocks
    .replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-100 rounded p-4 my-4 overflow-x-auto"><code>$1</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-black">$1</code>')
    // Paragraphs
    .replace(/\n\n/g, '</p><p class="mb-4 text-black leading-relaxed">')
    // Line breaks
    .replace(/\n/g, '<br/>');

  // Wrap in paragraphs
  html = '<p class="mb-4 text-black leading-relaxed">' + html + '</p>';
  
  // Wrap lists
  html = html.replace(/(<li.*?<\/li>)+/g, '<ul class="list-disc ml-6 mb-4 space-y-2">$&</ul>');
  
  return html;
}
