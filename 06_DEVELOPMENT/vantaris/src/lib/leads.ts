/**
 * Unified lead capture for all Everlight Ventures forms.
 *
 * Submits to Supabase `leads` table via REST (anon key, RLS allows INSERT).
 * Also fires a notification email via the Resend edge function.
 *
 * Usage:
 *   await submitLead({ source: 'wholesale', email: 'buyer@example.com', name: 'John' })
 */

const SUPABASE_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co'
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww'

// Django broker_ops backend on Oracle E5 -- public PropertyLead intake.
// Used for wholesale source only; other sources stay Supabase-only.
const DJANGO_BASE = 'http://129.159.38.250:8504'

export type LeadSource = 'wholesale' | 'onyx' | 'hivemind' | 'alley-kingz' | 'logistics' | 'consulting' | 'list-tool'

export interface LeadData {
  source: LeadSource
  email: string
  name?: string
  phone?: string
  message?: string
  metadata?: Record<string, unknown>
}

export async function submitLead(data: LeadData): Promise<{ ok: boolean; error?: string }> {
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/leads`, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify({
        source: data.source,
        email: data.email,
        name: data.name || null,
        phone: data.phone || null,
        message: data.message || null,
        metadata: data.metadata || {},
      }),
    })

    if (!res.ok) {
      const body = await res.text()
      console.error('[leads] Supabase insert failed:', res.status, body)
      return { ok: false, error: `Failed to submit (${res.status})` }
    }

    // Fire notification email (best-effort, don't block on it)
    notifyNewLead(data).catch(() => {})

    // Wholesale leads also flow into the Django wholesale pipeline so they
    // appear in /reports/pipeline_index/ and trigger the Slack alert. Best
    // effort -- if Django is down the Supabase row + email still went through.
    if (data.source === 'wholesale') {
      pushToWholesalePipeline(data).catch(() => {})
    }

    return { ok: true }
  } catch (err) {
    console.error('[leads] Submit error:', err)
    return { ok: false, error: 'Network error. Please try again.' }
  }
}

async function notifyNewLead(data: LeadData): Promise<void> {
  await fetch(`${SUPABASE_URL}/functions/v1/notify-lead`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })
}

async function pushToWholesalePipeline(data: LeadData): Promise<void> {
  const md = data.metadata || {}
  const address = (md.address as string | undefined) || ''
  const state = (md.state as string | undefined) || ''
  const preforeclosure = Boolean(md.preforeclosure)

  await fetch(`${DJANGO_BASE}/broker/api/public/property-lead/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: data.name || '',
      email: data.email,
      phone: data.phone || '',
      address,
      state,
      situation: data.message || '',
      preforeclosure,
    }),
  })
}
