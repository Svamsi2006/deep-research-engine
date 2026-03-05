/**
 * Session Management Hook
 * Manages user identity and conversation state
 */

'use client'

import { useEffect, useState, useCallback } from 'react'

interface SessionUser {
  id: string
  name: string
  isAnonymous: boolean
}

interface UseSessionReturn {
  user: SessionUser | null
  isLoading: boolean
  conversationId: string | null
  setConversationId: (id: string | null) => void
  createNewConversation: () => void
  error: string | null
}

const SESSION_STORAGE_USER_ID = 'deep_research_user_id'
const SESSION_STORAGE_CONV_ID = 'deep_research_conversation_id'

export function useSession(): UseSessionReturn {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initialize session on mount
  useEffect(() => {
    const initializeSession = async () => {
      try {
        // Check for existing user
        const storedUserId = localStorage.getItem(SESSION_STORAGE_USER_ID)
        const storedConvId = localStorage.getItem(SESSION_STORAGE_CONV_ID)

        if (storedUserId) {
          // Verify user still exists
          const response = await fetch(`/api/users/${storedUserId}`)
          if (response.ok) {
            const userData = await response.json()
            setUser(userData)
            if (storedConvId) {
              setConversationId(storedConvId)
            }
            setIsLoading(false)
            return
          }
        }

        // Create anonymous user
        const response = await fetch('/api/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: 'Anonymous',
            is_anonymous: true,
          }),
        })

        if (response.ok) {
          const newUser = await response.json()
          setUser(newUser)
          localStorage.setItem(SESSION_STORAGE_USER_ID, newUser.id)
          setIsLoading(false)
        } else {
          setError('Failed to initialize session')
          setIsLoading(false)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Session initialization failed')
        setIsLoading(false)
      }
    }

    initializeSession()
  }, [])

  const handleSetConversationId = useCallback((id: string | null) => {
    setConversationId(id)
    if (id) {
      localStorage.setItem(SESSION_STORAGE_CONV_ID, id)
    } else {
      localStorage.removeItem(SESSION_STORAGE_CONV_ID)
    }
  }, [])

  const handleCreateNewConversation = useCallback(() => {
    handleSetConversationId(null)
  }, [handleSetConversationId])

  return {
    user,
    isLoading,
    conversationId,
    setConversationId: handleSetConversationId,
    createNewConversation: handleCreateNewConversation,
    error,
  }
}
