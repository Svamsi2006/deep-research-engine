"use client";

import React, { useState, useCallback } from "react";
import { X, Upload, FileText, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface PDFUploadDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: (sourceId: string, title: string, chunkCount: number) => void;
}

export default function PDFUploadDialog({ isOpen, onClose, onUploadComplete }: PDFUploadDialogProps) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const uploadPDF = useCallback(async (file: File) => {
    if (!file.type.includes('pdf')) {
      setError('Please upload a PDF file');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(false);

    try {
      // Convert file to base64
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve, reject) => {
        reader.onload = () => {
          const base64 = reader.result as string;
          // Remove data URL prefix (data:application/pdf;base64,)
          const base64Content = base64.split(',')[1];
          resolve(base64Content);
        };
        reader.onerror = reject;
      });

      reader.readAsDataURL(file);
      const base64Content = await base64Promise;

      // Send to backend
      const response = await fetch('/api/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_type: 'pdf',
          payload: base64Content,
          file_name: file.name,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setSuccess(true);
      onUploadComplete(data.source_id, data.title, data.chunk_count);

      // Close dialog after 1.5 seconds
      setTimeout(() => {
        onClose();
        setSuccess(false);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [onClose, onUploadComplete]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadPDF(e.dataTransfer.files[0]);
    }
  }, [uploadPDF]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadPDF(e.target.files[0]);
    }
  }, [uploadPDF]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-[#0D0D0D] border border-[#2A2A2A] rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#2A2A2A]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#4F46E5]/10">
              <FileText className="w-5 h-5 text-[#4F46E5]" />
            </div>
            <h2 className="text-lg font-semibold text-white">Upload PDF</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[#1A1A1A] transition-colors"
            disabled={uploading}
          >
            <X className="w-5 h-5 text-[#A0A0A0]" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`
              relative border-2 border-dashed rounded-xl p-8
              transition-all duration-200 cursor-pointer
              ${dragActive 
                ? 'border-[#4F46E5] bg-[#4F46E5]/5' 
                : 'border-[#2A2A2A] hover:border-[#3A3A3A] hover:bg-[#1A1A1A]/50'
              }
              ${uploading ? 'pointer-events-none opacity-60' : ''}
            `}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileInput}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={uploading}
            />

            <div className="flex flex-col items-center text-center">
              {uploading ? (
                <>
                  <Loader2 className="w-12 h-12 text-[#4F46E5] animate-spin mb-4" />
                  <p className="text-white font-medium mb-2">Uploading PDF...</p>
                  <p className="text-sm text-[#A0A0A0]">Processing and creating chunks</p>
                </>
              ) : success ? (
                <>
                  <CheckCircle2 className="w-12 h-12 text-green-500 mb-4" />
                  <p className="text-white font-medium mb-2">Upload Complete!</p>
                  <p className="text-sm text-[#A0A0A0]">PDF has been processed successfully</p>
                </>
              ) : (
                <>
                  <Upload className="w-12 h-12 text-[#4F46E5] mb-4" />
                  <p className="text-white font-medium mb-2">Drop your PDF here</p>
                  <p className="text-sm text-[#A0A0A0] mb-4">or click to browse</p>
                  <div className="flex items-center gap-2 px-4 py-2 bg-[#4F46E5] text-white rounded-lg text-sm font-medium hover:bg-[#4338CA] transition-colors">
                    <FileText className="w-4 h-4" />
                    Select PDF File
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-400">Upload Failed</p>
                <p className="text-xs text-red-300/80 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Info */}
          {!uploading && !success && (
            <div className="mt-4 p-4 bg-[#1A1A1A] rounded-lg">
              <p className="text-xs text-[#A0A0A0]">
                <span className="font-medium text-white">Note:</span> The PDF will be processed and split into chunks for analysis. Make sure your PDF contains searchable text (not scanned images).
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
