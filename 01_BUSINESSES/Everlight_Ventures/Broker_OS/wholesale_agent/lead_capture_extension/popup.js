// Everlight Lead Capture -- popup logic
// Scrapes the active property listing, scores distress signals, flags non-TN
// (capture-only outside Tennessee per the TN-only pipeline law), and lets you
// copy / save / send the lead to the pipeline via the notify-lead edge fn.
// All page-derived values are rendered via textContent (no innerHTML) -- the
// scraped listing is untrusted input, so this stays XSS-safe.

const SUPA_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co'
const ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww'
const NOTIFY_FN = SUPA_URL + '/functions/v1/notify-lead'

const DISTRESS = ['as-is', 'as is', 'motivated', 'must sell', 'fixer', 'tlc', 'handyman',
  'cash only', 'cash buyer', 'investor', 'foreclosure', 'pre-foreclosure', 'short sale',
  'estate sale', 'probate', 'tenant occupied', 'vacant', 'needs work', 'needs tlc', 'rehab',
  'distressed', 'bring offers', 'priced to sell', "won't last", 'below market', 'quick close',
  'seller financing', 'handyman special', 'investment opportunity', 'sold as-is']

// Injected into the page context to scrape listing data.
function extractListing() {
  const text = document.body.innerText || ''
  const pick = (re) => { const m = text.match(re); return m ? m[0].trim() : null }
  let ld = {}
  try {
    document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
      try {
        const j = JSON.parse(s.textContent); const arr = Array.isArray(j) ? j : [j]
        arr.forEach(o => { if (!o) return; if (o.address) ld.address = o.address; if (o.offers) ld.offers = o.offers })
      } catch (e) {}
    })
  } catch (e) {}
  const meta = (n) => { const el = document.querySelector(`meta[property="${n}"],meta[name="${n}"]`); return el ? el.content : null }
  let addr = ''
  if (ld.address && typeof ld.address === 'object') {
    const a = ld.address
    addr = [a.streetAddress, a.addressLocality, a.addressRegion, a.postalCode].filter(Boolean).join(', ')
  }
  if (!addr) addr = (meta('og:title') || (document.querySelector('h1') || {}).innerText || document.title || '').trim()
  let price = null
  if (ld.offers && ld.offers.price) price = '$' + Number(ld.offers.price).toLocaleString()
  if (!price) price = pick(/\$[\d,]{4,}/)
  const beds = pick(/(\d+(\.\d+)?)\s*(?:bd|beds?|bedrooms?)/i)
  const baths = pick(/(\d+(\.\d+)?)\s*(?:ba|baths?|bathrooms?)/i)
  const sqft = pick(/([\d,]{3,})\s*(?:sq\.?\s?ft|sqft|square feet)/i)
  const stMatch = addr.match(/,\s*([A-Z]{2})\s*\d{5}/) || addr.match(/\b([A-Z]{2})\s+\d{5}/)
  const state = stMatch ? stMatch[1] : (/tennessee/i.test(addr) ? 'TN' : '')
  return {
    address: addr, price, beds, baths, sqft, state, url: location.href,
    descriptionSample: (meta('description') || '').slice(0, 300),
    bodyText: text.slice(0, 7000),
  }
}

let LEAD = null

function distressScore(t) {
  const low = (t || '').toLowerCase()
  const hits = DISTRESS.filter(k => low.includes(k))
  return { hits, score: Math.min(100, hits.length * 14) }
}

function el(tag, cls, txt) {
  const e = document.createElement(tag)
  if (cls) e.className = cls
  if (txt != null) e.textContent = txt
  return e
}
function setMsg(targetId, txt) {
  const t = document.getElementById(targetId); t.textContent = ''; t.appendChild(el('p', 'muted', txt))
}
function status(s) { document.getElementById('status').textContent = s }

function render(data) {
  if (!data) { setMsg('fields', 'No data on this page.'); return }
  const ds = distressScore((data.bodyText || '') + ' ' + (data.descriptionSample || ''))
  data.distress_hits = ds.hits
  data.distress_score = ds.score
  data.captured_at = new Date().toISOString()
  delete data.bodyText
  LEAD = data

  const fields = document.getElementById('fields'); fields.textContent = ''
  const row = (k, v) => { const d = el('div', 'row'); d.appendChild(el('span', null, k)); d.appendChild(el('span', null, v || '-')); return d }
  fields.appendChild(row('Address', data.address))
  fields.appendChild(row('Price', data.price))
  fields.appendChild(row('Beds', data.beds))
  fields.appendChild(row('Baths', data.baths))
  fields.appendChild(row('SqFt', data.sqft))
  fields.appendChild(row('State', data.state))

  const sc = document.getElementById('score'); sc.style.display = 'block'; sc.textContent = ''
  const color = ds.score >= 42 ? '#00e676' : ds.score >= 14 ? '#ff6b35' : '#8b8b9e'
  sc.style.background = color + '22'; sc.style.color = color
  sc.appendChild(document.createTextNode('Distress signal: '))
  sc.appendChild(el('b', null, `${ds.score}/100`))
  sc.appendChild(document.createTextNode(ds.hits.length ? ' · ' + ds.hits.slice(0, 4).join(', ') : ' · none detected'))

  const flag = document.getElementById('flag')
  if (data.state && data.state !== 'TN') {
    flag.style.display = 'block'; flag.style.background = 'rgba(255,107,53,.15)'; flag.style.color = '#ff6b35'
    flag.textContent = `Note: ${data.state} property. TN is the only active outreach state -- capture-only.`
  } else if (data.state === 'TN') {
    flag.style.display = 'block'; flag.style.background = 'rgba(0,230,118,.12)'; flag.style.color = '#00e676'
    flag.textContent = 'Tennessee -- active pipeline state.'
  }
}

async function init() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    const [res] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: extractListing })
    render(res.result)
  } catch (e) {
    setMsg('fields', 'Open a property listing (Zillow / Redfin / Realtor) and click the icon again.')
  }
}

document.getElementById('copy').onclick = () => {
  if (!LEAD) return
  navigator.clipboard.writeText(JSON.stringify(LEAD, null, 2)); status('Copied to clipboard.')
}
document.getElementById('download').onclick = () => {
  if (!LEAD) return
  const blob = new Blob([JSON.stringify(LEAD, null, 2)], { type: 'application/json' })
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
  a.download = 'lead_' + Date.now() + '.json'; a.click(); status('Saved JSON.')
}
document.getElementById('send').onclick = async () => {
  if (!LEAD) return
  status('Sending...')
  try {
    const r = await fetch(NOTIFY_FN, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + ANON, 'apikey': ANON },
      body: JSON.stringify({
        source: 'wholesale_capture',
        name: LEAD.address || 'Captured property',
        email: '', phone: '',
        message: `${LEAD.price || ''} | ${LEAD.beds || '?'}bd/${LEAD.baths || '?'}ba | distress ${LEAD.distress_score} | ${LEAD.url}`,
        metadata: LEAD,
      }),
    })
    status(r.ok ? 'Sent to pipeline. Check your email.' : 'Send failed (' + r.status + ') -- use Save JSON.')
  } catch (e) { status('Send failed -- use Save JSON.') }
}

init()
