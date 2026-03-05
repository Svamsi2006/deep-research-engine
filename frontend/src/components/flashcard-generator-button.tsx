"use client";

import React, { useState } from "react";
import { BookOpen, X } from "lucide-react";
import FlashcardsPanel from "./flashcards-panel";
import type { FlashcardData } from "@/lib/sse-client";

interface FlashcardGeneratorButtonProps {
  reportContent: string;
  reportId: string;
  question: string;
  onGenerateFlashcards: (
    reportId: string,
    reportContent: string,
    question: string,
    callbacks: {
      onFlashcards: (event: { cards: FlashcardData[]; csv: string }) => void;
      onError: (error: string) => void;
    }
  ) => Promise<void>;
}

export default function FlashcardGeneratorButton({
  reportContent,
  reportId,
  question,
  onGenerateFlashcards,
}: FlashcardGeneratorButtonProps) {
  const [showFlashcards, setShowFlashcards] = useState(false);
  const [flashcards, setFlashcards] = useState<FlashcardData[]>([]);
  const [flashcardsCsv, setFlashcardsCsv] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerateFlashcards = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setShowFlashcards(true);

    try {
      await onGenerateFlashcards(reportId, reportContent, question, {
        onFlashcards: (event) => {
          setFlashcards(event.cards);
          setFlashcardsCsv(event.csv);
        },
        onError: (error) => {
          alert(`Failed to generate flashcards: ${error}`);
          setIsLoading(false);
        },
      });
    } catch (error) {
      alert(`Error: ${error instanceof Error ? error.message : "Unknown error"}`);
      setIsLoading(false);
    } finally {
      setIsLoading(false);
    }
  };

  if (showFlashcards) {
    return (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
        <div className="bg-[#1A1A1A] rounded-lg border border-[#2A2A2A] w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#2A2A2A]">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-[#4F46E5]" />
              Flashcards
            </h3>
            <button
              onClick={() => setShowFlashcards(false)}
              className="p-1 hover:bg-[#2A2A2A] rounded transition-colors"
            >
              <X className="w-5 h-5 text-[#A0A0A0]" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            <FlashcardsPanel
              cards={flashcards}
              csv={flashcardsCsv}
              isLoading={isLoading}
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={handleGenerateFlashcards}
      disabled={isLoading || !reportContent}
      className={`
        flex items-center gap-2 px-4 py-2 rounded-lg
        font-medium transition-all duration-200
        ${
          isLoading || !reportContent
            ? "bg-[#2A2A2A] text-[#A0A0A0] cursor-not-allowed"
            : "bg-[#4F46E5] text-white hover:bg-[#6366F1] shadow-lg shadow-[#4F46E5]/30"
        }
      `}
    >
      <BookOpen className="w-4 h-4" />
      Generate Flashcards
    </button>
  );
}
