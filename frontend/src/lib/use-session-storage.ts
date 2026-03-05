"use client";

import { useState, useEffect } from "react";

interface StoredSession {
  id: string;
  timestamp: string;
  title: string;
  messages: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
}

const STORAGE_KEY = "deep_research_sessions";

export function useSessionStorage() {
  const [sessions, setSessions] = useState<StoredSession[]>([]);
  const [currentSession, setCurrentSession] = useState<StoredSession | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load sessions from sessionStorage on mount
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as StoredSession[];
        setSessions(parsed);
      }
    } catch (error) {
      console.error("Failed to load sessions from storage:", error);
    }
    setIsLoaded(true);
  }, []);

  // Save sessions to sessionStorage whenever they change
  useEffect(() => {
    if (isLoaded) {
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
      } catch (error) {
        console.error("Failed to save sessions to storage:", error);
      }
    }
  }, [sessions, isLoaded]);

  // Create a new session
  const createSession = (title: string = "New Session") => {
    const newSession: StoredSession = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      title,
      messages: [],
    };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSession(newSession);
    return newSession;
  };

  // Add a message to current session
  const addMessage = (role: "user" | "assistant", content: string) => {
    setSessions((prevSessions) => {
      // If no current session, create one
      if (!currentSession) {
        const newSession: StoredSession = {
          id: Date.now().toString(),
          timestamp: new Date().toISOString(),
          title: `Chat - ${new Date().toLocaleTimeString()}`,
          messages: [{ role, content }],
        };
        setCurrentSession(newSession);
        return [newSession, ...prevSessions];
      }

      // Update existing session with new message
      const updated = prevSessions.map((s) => {
        if (s.id === currentSession.id) {
          return {
            ...s,
            messages: [...s.messages, { role, content }],
          };
        }
        return s;
      });

      // Update currentSession for next render
      const updatedSession = updated.find((s) => s.id === currentSession.id);
      if (updatedSession) {
        setCurrentSession(updatedSession);
      }

      return updated;
    });
  };

  // Get last N messages for context buffer
  const getContextBuffer = (count: number = 6) => {
    if (!currentSession) return [];
    return currentSession.messages.slice(-count);
  };

  // Delete a session
  const deleteSession = (sessionId: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    if (currentSession?.id === sessionId) {
      setCurrentSession(null);
    }
  };

  // Get last N sessions
  const getLastSessions = (count: number = 6) => {
    return sessions.slice(0, count);
  };

  // Clear all sessions
  const clearAllSessions = () => {
    setSessions([]);
    setCurrentSession(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error("Failed to clear sessions:", error);
    }
  };

  return {
    sessions,
    currentSession,
    isLoaded,
    createSession,
    addMessage,
    getContextBuffer,
    deleteSession,
    getLastSessions,
    clearAllSessions,
    setCurrentSession,
  };
}
