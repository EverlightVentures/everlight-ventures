'use client'

import { useState } from 'react'
import { submitLead, type LeadSource } from '@/lib/leads'

interface UseLeadFormOptions {
  source: LeadSource
  onSuccess?: () => void
}

export function useLeadForm({ source, onSuccess }: UseLeadFormOptions) {
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(fields: {
    email: string
    name?: string
    phone?: string
    message?: string
    metadata?: Record<string, unknown>
  }) {
    setLoading(true)
    setError(null)

    const result = await submitLead({ source, ...fields })

    setLoading(false)

    if (result.ok) {
      setSubmitted(true)
      onSuccess?.()
    } else {
      setError(result.error || 'Something went wrong.')
    }
  }

  return { loading, submitted, error, handleSubmit }
}
