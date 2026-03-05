'use client'

import { useEffect, useState } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  extra_data: Record<string, any>
}

interface ConversationHistoryProps {
  conversationId: string | null
}

export function ConversationHistory({ conversationId }: ConversationHistoryProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch conversation history
  useEffect(() => {
    if (!conversationId) {
      setMessages([])
      return
    }

    const fetchHistory = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch(`/api/conversations/${conversationId}`)
        if (response.ok) {
          const data = await response.json()
          // Filter out system messages, only show user and assistant
          const filteredMessages = (data.messages || []).filter(
            (m: Message) => m.role !== 'system'
          )
          setMessages(filteredMessages)
        } else {
          setError('Failed to load conversation history')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error loading history')
      } finally {
        setIsLoading(false)
      }
    }

    fetchHistory()
  }, [conversationId])

  if (!conversationId) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <p>Select or create a conversation to start</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">Loading conversation...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-500">
        <p>{error}</p>
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <p>No messages in this conversation yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-3 ${
            message.role === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          <div
            className={`max-w-[70%] px-4 py-3 rounded-lg ${
              message.role === 'user'
                ? 'bg-blue-100 text-blue-900'
                : 'bg-gray-100 text-gray-900'
            }`}
          >
            <p className="text-sm whitespace-pre-wrap">{message.content.slice(0, 500)}</p>
            {message.content.length > 500 && (
              <p className="text-xs text-gray-600 mt-2 italic">
                [Message truncated - {message.content.length} chars total]
              </p>
            )}

            {/* Show metadata for assistant messages */}
            {message.role === 'assistant' && message.extra_data && (
              <div className="text-xs text-gray-600 mt-2 pt-2 border-t border-gray-300">
                {message.extra_data.tokens_used && (
                  <p>Tokens: {message.extra_data.tokens_used}</p>
                )}
                {message.extra_data.cost_usd && (
                  <p>Cost: ${message.extra_data.cost_usd.toFixed(4)}</p>
                )}
                {message.extra_data.provider && (
                  <p>Provider: {message.extra_data.provider}</p>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
