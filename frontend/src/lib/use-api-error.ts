/**
 * Enhanced Error Handling Hook
 * Manages API errors with retry logic and user-friendly messages
 */

'use client'

import { useState, useCallback } from 'react'

export interface APIError {
  message: string
  code: string
  field?: string
  status?: number
}

interface ErrorState {
  error: APIError | null
  isRetrying: boolean
  retryCount: number
}

const ERROR_MESSAGES: Record<string, string> = {
  VALIDATION_ERROR: 'Please check your input and try again.',
  NOT_FOUND: 'The requested resource was not found.',
  RATE_LIMIT_EXCEEDED: 'Too many requests. Please wait a moment and try again.',
  LLM_ERROR: 'The AI model encountered an error. Please try again.',
  INTERNAL_ERROR: 'Something went wrong on our end. Please try again later.',
  NETWORK_ERROR: 'Network connection failed. Please check your connection.',
}

export function useAPIError() {
  const [state, setState] = useState<ErrorState>({
    error: null,
    isRetrying: false,
    retryCount: 0,
  })

  const setError = useCallback((error: APIError | null) => {
    setState((prev) => ({
      ...prev,
      error,
      retryCount: error && !prev.error ? prev.retryCount + 1 : 0,
    }))
  }, [])

  const clearError = useCallback(() => {
    setState((prev) => ({
      ...prev,
      error: null,
      isRetrying: false,
    }))
  }, [])

  const getErrorMessage = useCallback((error: APIError | null): string => {
    if (!error) return ''
    return ERROR_MESSAGES[error.code] || error.message
  }, [])

  const shouldRetry = useCallback((error: APIError | null): boolean => {
    if (!error) return false
    
    // Retry on rate limits and transient server errors
    return (
      error.code === 'RATE_LIMIT_EXCEEDED' ||
      error.code === 'LLM_ERROR' ||
      (error.status !== undefined && error.status >= 500)
    )
  }, [])

  const retry = useCallback(async (fn: () => Promise<any>, maxRetries = 3) => {
    let lastError: APIError | null = null
    
    for (let i = 0; i < maxRetries; i++) {
      try {
        setState((prev) => ({ ...prev, isRetrying: i > 0 }))
        const result = await fn()
        clearError()
        setState((prev) => ({ ...prev, isRetrying: false }))
        return result
      } catch (err: any) {
        lastError = {
          message: err.message || 'Unknown error',
          code: err.code || 'INTERNAL_ERROR',
          status: err.status,
        }
        
        if (!shouldRetry(lastError) || i === maxRetries - 1) {
          setError(lastError)
          setState((prev) => ({ ...prev, isRetrying: false }))
          throw lastError
        }
        
        // Exponential backoff
        const wait = Math.min(1000 * Math.pow(2, i), 5000)
        await new Promise((resolve) => setTimeout(resolve, wait))
      }
    }
    
    throw lastError
  }, [clearError, setError, shouldRetry])

  return {
    error: state.error,
    isRetrying: state.isRetrying,
    retryCount: state.retryCount,
    setError,
    clearError,
    getErrorMessage,
    shouldRetry,
    retry,
  }
}
