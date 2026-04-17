// Supabase Edge Function: notify-lead
// Sends email notification via Resend when a new lead is submitted.

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY') || ''
const NOTIFY_EMAIL = 'hello@everlightventures.io'

const SOURCE_LABELS: Record<string, string> = {
  wholesale: 'Wholesale Buyer Signup',
  onyx: 'Onyx POS Trial',
  hivemind: 'Hive Mind AI Waitlist',
  'alley-kingz': 'Alley Kingz Waitlist',
  logistics: 'Logistics Quote Request',
  consulting: 'AI Consulting Inquiry',
  'list-tool': 'Tool Directory Submission',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, content-type' } })
  }

  try {
    const data = await req.json()
    const label = SOURCE_LABELS[data.source] || data.source
    const meta = data.metadata ? Object.entries(data.metadata).map(([k, v]) => `<li><strong>${k}:</strong> ${v}</li>`).join('') : ''

    const html = `
      <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0a14; color: #ccc; padding: 32px; border-radius: 12px;">
        <h2 style="color: #c9a84c; font-family: Cinzel, serif; margin-bottom: 4px;">New Lead: ${label}</h2>
        <hr style="border-color: #222;" />
        <p><strong>Name:</strong> ${data.name || 'Not provided'}</p>
        <p><strong>Email:</strong> ${data.email}</p>
        ${data.phone ? `<p><strong>Phone:</strong> ${data.phone}</p>` : ''}
        ${data.message ? `<p><strong>Message:</strong> ${data.message}</p>` : ''}
        ${meta ? `<ul>${meta}</ul>` : ''}
        <hr style="border-color: #222;" />
        <p style="font-size: 11px; color: #666;">Submitted via everlightventures.io/${data.source}</p>
      </div>
    `

    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${RESEND_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: 'Everlight Leads <noreply@everlightventures.io>',
        to: [NOTIFY_EMAIL],
        subject: `[Lead] ${label} - ${data.email}`,
        html,
      }),
    })

    const result = await res.json()
    return new Response(JSON.stringify({ ok: true, id: result.id }), { headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } })
  } catch (err) {
    return new Response(JSON.stringify({ ok: false, error: String(err) }), { status: 500, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } })
  }
})
