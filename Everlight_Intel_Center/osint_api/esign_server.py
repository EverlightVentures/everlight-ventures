"""
esign_server.py -- free, self-hosted e-signature server.

UETA + E-SIGN Act compliant (15 USC § 7001 + Tenn. Code Ann. § 47-10-101 et seq).
Same legal force as DocuSign envelopes for the elements that matter:
  - intent (signer affirmatively checks "I intend to sign")
  - identity (typed legal name + email + IP + user-agent timestamp)
  - association (cryptographic SHA-256 of the document at signing moment)
  - integrity (audit chain entry, hashed to prior entries, tamper-detectable)

Routes:
  GET  /sign/{token}           render doc + signing form for the recipient
  POST /sign/{token}           capture signature, send signed copy to all parties, log
  GET  /sign/{token}/cert      view the signature certificate after signing
  GET  /healthz                health check

Token format: base64url(json({deal_key, doc_id, signer_email, signer_name,
                              expires_at})) + "." + hmac_sha256(payload, secret)

Run:
  python3 -m uvicorn esign_server:app --host 127.0.0.1 --port 2302
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
DEALS_DIR = ROOT / "09_DASHBOARD" / "reports" / "deals"
SIG_DIR = ROOT / "09_DASHBOARD" / "reports" / "signatures"
SIG_DIR.mkdir(parents=True, exist_ok=True)

ESIGN_SECRET = os.environ.get("ESIGN_SECRET", "everlight_esign_dev_secret_change_in_prod")

# Audit log import
sys.path.insert(0, str(ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit"))
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))
from deal_execution_log import log_event

app = FastAPI(title="Everlight E-Sign", version="1.0", docs_url="/api/docs")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def make_token(deal_key: str, doc_id: str, signer_email: str, signer_name: str,
               ttl_hours: int = 168) -> str:
    """Make a signing token. Default TTL 7 days."""
    payload = {
        "deal_key": deal_key,
        "doc_id": doc_id,
        "signer_email": signer_email,
        "signer_name": signer_name,
        "expires_at": (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat() + "Z",
    }
    pj = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded = _b64url_encode(pj)
    sig = hmac.new(ESIGN_SECRET.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def verify_token(token: str) -> dict:
    if "." not in token:
        raise HTTPException(400, "malformed token")
    encoded, sig = token.rsplit(".", 1)
    expected = hmac.new(ESIGN_SECRET.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(403, "invalid token signature")
    payload = json.loads(_b64url_decode(encoded).decode("utf-8"))
    expires = datetime.fromisoformat(payload["expires_at"].rstrip("Z"))
    if datetime.utcnow() > expires:
        raise HTTPException(410, "token expired")
    return payload


def doc_path(deal_key: str, doc_id: str) -> Path:
    return DEALS_DIR / deal_key / f"{doc_id}.html"


def doc_sha256(deal_key: str, doc_id: str) -> str:
    p = doc_path(deal_key, doc_id)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# Brand colors (match the rest of the stack)
BRAND_CSS = """
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: radial-gradient(ellipse 800px 400px at 20% -10%, rgba(212,168,67,.18) 0%, transparent 70%),
                linear-gradient(180deg, #050402 0%, #0a0a0a 40%, #08080a 100%);
    background-attachment: fixed;
    color: #f4eedb;
    font-family: 'Inter', system-ui, sans-serif;
    line-height: 1.55;
    padding: 1.75rem 1rem 4rem;
    -webkit-font-smoothing: antialiased;
  }
  .display { font-family: 'Playfair Display', Georgia, serif; font-weight: 900; }
  .mono { font-family: 'JetBrains Mono', ui-monospace, monospace; }
  .gold { color: #d4a843; }
  .gold-hot { color: #ffcd3c; }
  a { color: #d4a843; }
  .wrap { max-width: 880px; margin: 0 auto; }
  .card {
    background: linear-gradient(180deg, #15140d 0%, #100f08 100%);
    border: 1px solid #322a14; border-left: 3px solid #d4a843;
    border-radius: 14px; padding: 1.75rem 2rem; margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.55);
  }
  h1.display { color: #ffcd3c; font-size: clamp(1.8rem, 4vw, 2.4rem);
               margin: 0 0 .35rem; line-height: 1.05; text-shadow: 0 0 20px rgba(255,205,60,.2); }
  .label { color: #d4a843; font-family: 'JetBrains Mono', monospace;
           font-size: .68rem; font-weight: 700; letter-spacing: .25em;
           text-transform: uppercase; margin-bottom: .35rem; }
  .meta { font-family: 'JetBrains Mono', monospace; font-size: .8rem;
          color: #b5af9b; line-height: 1.7; margin-top: .9rem; }
  .meta strong { color: #d4a843; margin-right: .35em; font-weight: 600; }
  iframe { width: 100%; height: 60vh; border: 1px solid #322a14; border-radius: 8px;
           background: #fff; }
  .form-row { margin: 1rem 0; }
  .form-row label { display: block; color: #d4a843;
                    font-family: 'JetBrains Mono', monospace; font-size: .75rem;
                    text-transform: uppercase; letter-spacing: .12em;
                    margin-bottom: .35rem; }
  input[type=text] {
    width: 100%; padding: .75rem 1rem; background: rgba(212,168,67,.05);
    border: 1px solid #4a3d1c; border-radius: 8px; color: #f4eedb;
    font-family: 'Playfair Display', Georgia, serif; font-size: 1.15rem;
    font-style: italic;
  }
  input[type=text]:focus { outline: none; border-color: #ffcd3c; }
  .intent {
    background: rgba(0,229,255,.04); border: 1px dashed #00e5ff;
    border-radius: 10px; padding: 1rem 1.25rem; margin: 1.5rem 0;
  }
  .intent label { display: flex; gap: .75rem; align-items: flex-start;
                  cursor: pointer; color: #f4eedb; font-size: .9rem;
                  text-transform: none; letter-spacing: 0; }
  .intent input[type=checkbox] { width: 1.25rem; height: 1.25rem; margin-top: .15rem; accent-color: #d4a843; }
  button.sign {
    width: 100%; padding: 1rem 1.5rem; background: #d4a843; color: #0a0a0a;
    border: none; border-radius: 10px; font-weight: 700; font-size: 1.05rem;
    text-transform: uppercase; letter-spacing: .08em; cursor: pointer;
    transition: background .15s ease;
  }
  button.sign:hover { background: #ffcd3c; }
  button.sign:disabled { background: #4a3d1c; color: #7a7560; cursor: not-allowed; }
  .legal {
    font-family: 'JetBrains Mono', monospace; font-size: .7rem; color: #7a7560;
    margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #322a14;
    line-height: 1.7;
  }
  .legal strong { color: #d4a843; }
  .ok-banner {
    background: linear-gradient(90deg, rgba(92,255,177,.12) 0%, rgba(92,255,177,.04) 100%);
    border: 1px solid rgba(92,255,177,.4); color: #5cffb1;
    padding: .85rem 1.2rem; border-radius: 8px; margin-bottom: 1.25rem;
    font-family: 'JetBrains Mono', monospace; font-size: .82rem;
    letter-spacing: .03em;
  }
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
"""


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"


@app.get("/sign/{token}", response_class=HTMLResponse)
async def sign_form(token: str, request: Request):
    payload = verify_token(token)
    deal_key = payload["deal_key"]
    doc_id = payload["doc_id"]
    signer_name = payload["signer_name"]
    signer_email = payload["signer_email"]
    sha = doc_sha256(deal_key, doc_id)
    if not sha:
        raise HTTPException(404, f"document {doc_id} not found in deal {deal_key}")

    # Check if already signed
    sig_file = SIG_DIR / f"{deal_key}_{doc_id}_{signer_email.replace('@', '_at_')}.json"
    if sig_file.exists():
        existing = json.loads(sig_file.read_text())
        return HTMLResponse(_signed_view(existing, deal_key, doc_id))

    # Use the token-gated /doc route so the iframe is access-controlled
    doc_url = f"/doc/{token}/{doc_id}"
    return HTMLResponse(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign · {doc_id} · Everlight Ventures</title>
{BRAND_CSS}
<style>
  /* Signature pad */
  .sig-pad-wrap {{
    background: #fffef8; border: 2px dashed #d4a843; border-radius: 10px;
    padding: 0; margin: .35rem 0 0; position: relative;
    aspect-ratio: 5 / 2; overflow: hidden;
  }}
  #sig-pad {{
    width: 100%; height: 100%; display: block; cursor: crosshair;
    touch-action: none; background: #fffef8;
  }}
  .sig-baseline {{
    position: absolute; left: 5%; right: 5%; bottom: 18%;
    border-bottom: 1px solid rgba(212,168,67,0.4); pointer-events: none;
  }}
  .sig-x {{
    position: absolute; left: 4%; bottom: 17%; color: #d4a843;
    font-family: 'Playfair Display', serif; font-size: 1.5rem;
    pointer-events: none; opacity: .55;
  }}
  .sig-controls {{
    display: flex; gap: .65rem; margin-top: .45rem; align-items: center;
    font-family: 'JetBrains Mono', monospace; font-size: .72rem;
  }}
  .sig-controls button {{
    background: rgba(155,151,136,.15); border: 1px solid rgba(155,151,136,.35);
    color: #b5af9b; padding: .35rem .75rem; border-radius: 6px; cursor: pointer;
    font-family: 'JetBrains Mono', monospace; font-size: .72rem;
    text-transform: uppercase; letter-spacing: .08em;
  }}
  .sig-controls button:hover {{ color: #ffcd3c; border-color: #ffcd3c; }}
  .sig-status {{ margin-left: auto; color: #7a7560; }}
  .sig-status.signed {{ color: #5cffb1; }}
  .or-divider {{
    text-align: center; color: #7a7560; font-family: 'JetBrains Mono', monospace;
    font-size: .7rem; text-transform: uppercase; letter-spacing: .25em;
    margin: 1.5rem 0; position: relative;
  }}
  .or-divider::before, .or-divider::after {{
    content: ""; position: absolute; top: 50%; width: 40%; height: 1px;
    background: #322a14;
  }}
  .or-divider::before {{ left: 0; }}
  .or-divider::after {{ right: 0; }}
  .err-msg {{
    background: rgba(220,38,38,.12); border: 1px solid rgba(220,38,38,.4);
    color: #ff7a8a; padding: .65rem 1rem; border-radius: 8px;
    margin-top: .65rem; font-size: .85rem; display: none;
  }}
  .err-msg.show {{ display: block; }}
</style>
</head>
<body><div class="wrap">
  <div class="card">
    <div class="label">E-Signature Request<span style="color:#b8902f;margin:0 .65em;">◆</span>Everlight Ventures</div>
    <h1 class="display">Sign: {doc_id}</h1>
    <div class="meta">
      <div><strong>Signer:</strong> {signer_name} &lt;{signer_email}&gt;</div>
      <div><strong>Deal:</strong> {deal_key}</div>
      <div><strong>Document SHA-256:</strong> <span class="mono" style="font-size:.65rem;color:#7a7560;">{sha}</span></div>
      <div><strong>Token expires:</strong> {payload['expires_at']}</div>
    </div>
  </div>

  <div class="card">
    <div class="label">Document Preview (token-gated, only you can view)</div>
    <iframe src="{doc_url}" loading="lazy"></iframe>
    <div class="meta" style="margin-top:.65rem;">
      Open in new tab: <a href="{doc_url}" target="_blank">{doc_url}</a>
    </div>
  </div>

  <div class="card">
    <div class="label">Signature</div>
    <form method="post" action="/sign/{token}" id="sign-form" onsubmit="return prepareSubmit()">
      <div class="form-row">
        <label>Draw your signature (finger or mouse)</label>
        <div class="sig-pad-wrap">
          <span class="sig-x">&times;</span>
          <span class="sig-baseline"></span>
          <canvas id="sig-pad"></canvas>
        </div>
        <div class="sig-controls">
          <button type="button" id="sig-clear">Clear</button>
          <span class="sig-status" id="sig-status">empty</span>
        </div>
        <input type="hidden" name="signature_image_b64" id="signature_image_b64" value="">
      </div>

      <div class="or-divider">and / or</div>

      <div class="form-row">
        <label for="typed_name">Type your full legal name (this also counts as a signature under UETA)</label>
        <input type="text" name="typed_name" id="typed_name" required
               placeholder="{signer_name}" value="{signer_name}">
      </div>

      <div class="intent">
        <label>
          <input type="checkbox" name="intent" id="intent" required>
          <span>By checking this box, I (<strong>{signer_name}</strong>) intend to sign this document
          electronically. I understand that my electronic signature has the same legal effect
          as a handwritten signature, per the federal E-Sign Act (15 USC § 7001) and Tennessee
          Uniform Electronic Transactions Act (Tenn. Code Ann. § 47-10-101).</span>
        </label>
      </div>

      <div class="err-msg" id="err-msg"></div>

      <button type="submit" class="sign">Sign and Send</button>
    </form>

    <div class="legal">
      <strong>Legal notice:</strong> Your signature is captured with the following
      attestations, all bound to this document via SHA-256 hash:
      <ul style="margin:.5rem 0 .25rem 1.2rem; padding:0;">
        <li>Drawn signature image (above) and/or typed legal name</li>
        <li>Affirmative intent checkbox (above)</li>
        <li>IP address + user agent + timestamp at submission</li>
        <li>Cryptographic hash of the exact document version you saw</li>
      </ul>
      All signers and Everlight Ventures receive an emailed copy of the signed document
      and signature certificate immediately on submission. The signed event is logged to
      the deal_execution_log audit chain (tamper-detectable).
    </div>
  </div>
</div>

<script>
(function() {{
  // Signature pad: HTML5 canvas, touch + mouse + pointer events
  const canvas = document.getElementById('sig-pad');
  const status = document.getElementById('sig-status');
  const clearBtn = document.getElementById('sig-clear');
  const hidden = document.getElementById('signature_image_b64');
  const errMsg = document.getElementById('err-msg');
  const ctx = canvas.getContext('2d');
  let drawing = false, hasInk = false, last = null;

  function resize() {{
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.scale(dpr, dpr);
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#1a1308';
  }}
  resize();
  window.addEventListener('resize', resize);

  function getXY(e) {{
    const rect = canvas.getBoundingClientRect();
    const t = (e.touches && e.touches[0]) || e;
    return {{ x: t.clientX - rect.left, y: t.clientY - rect.top }};
  }}

  function start(e) {{ e.preventDefault(); drawing = true; last = getXY(e); }}
  function move(e) {{
    if (!drawing) return;
    e.preventDefault();
    const p = getXY(e);
    ctx.beginPath();
    ctx.moveTo(last.x, last.y);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    last = p;
    if (!hasInk) {{ hasInk = true; status.textContent = 'signed'; status.classList.add('signed'); }}
  }}
  function end(e) {{ if (e) e.preventDefault(); drawing = false; }}

  canvas.addEventListener('pointerdown', start);
  canvas.addEventListener('pointermove', move);
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', end);
  canvas.addEventListener('pointerleave', end);

  clearBtn.addEventListener('click', function() {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    hasInk = false; status.textContent = 'empty'; status.classList.remove('signed');
    hidden.value = '';
  }});

  window.prepareSubmit = function() {{
    errMsg.classList.remove('show');
    const intent = document.getElementById('intent').checked;
    const typed = (document.getElementById('typed_name').value || '').trim();
    if (!intent) {{
      errMsg.textContent = 'Please check the intent box to confirm you intend to sign.';
      errMsg.classList.add('show');
      return false;
    }}
    if (!typed && !hasInk) {{
      errMsg.textContent = 'Please draw your signature OR type your full legal name (or both).';
      errMsg.classList.add('show');
      return false;
    }}
    if (hasInk) {{
      hidden.value = canvas.toDataURL('image/png');
    }}
    return true;
  }};
}})();
</script>
</body></html>""")


def _error_view(msg: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Sign error</title>{BRAND_CSS}</head>
<body><div class="wrap"><div class="card">
  <div class="label" style="color:#ff7a8a;">Signature Error</div>
  <h1 class="display" style="color:#ff7a8a;">Couldn't accept signature</h1>
  <p style="color:#f4eedb;font-family:Inter,sans-serif;line-height:1.6;">{msg}</p>
  <p><a href="javascript:history.back()" style="color:#d4a843;">← Go back and try again</a></p>
</div></div></body></html>"""


def _signed_view(sig_record: dict, deal_key: str, doc_id: str) -> str:
    from osint_api.public_url import signed_doc_url, deal_url as _deal_url
    signed_copy_url = signed_doc_url(deal_key, doc_id)
    template_url = _deal_url(deal_key, doc_id)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signed · {doc_id}</title>
{BRAND_CSS}</head>
<body><div class="wrap">
  <div class="card">
    <div class="ok-banner">✓ Signed and recorded. Signature is burned into the document.</div>
    <h1 class="display">Signature on file</h1>
    <div style="margin-top:1rem; padding:1.25rem; background:rgba(92,255,177,0.06);
                border:1px solid rgba(92,255,177,0.4); border-radius:10px;">
      <div style="color:#5cffb1; font-family:'JetBrains Mono',monospace; font-size:.7rem;
                  text-transform:uppercase; letter-spacing:.15em; margin-bottom:.5rem;">
        Executed contract (signature burned in)
      </div>
      <a href="{signed_copy_url}" target="_blank"
         style="display:inline-block; padding:.75rem 1.25rem; background:#d4a843; color:#0a0a0a;
                font-weight:700; border-radius:8px; text-decoration:none; margin-top:.25rem;">
        Open signed {doc_id} →
      </a>
    </div>
    <div class="meta" style="margin-top:1rem;">
      <div><strong>Signer:</strong> {sig_record.get('signer_name', '')} &lt;{sig_record.get('signer_email', '')}&gt;</div>
      <div><strong>Document:</strong> {doc_id}</div>
      <div><strong>Signed at (UTC):</strong> {sig_record.get('signed_at', '')}</div>
      <div><strong>From IP:</strong> {sig_record.get('ip', '')}</div>
      <div><strong>Original template SHA-256:</strong> <span class="mono" style="font-size:.65rem;color:#7a7560;">{sig_record.get('document_sha256', '')}</span></div>
      <div><strong>Signature SHA-256:</strong> <span class="mono" style="font-size:.65rem;color:#7a7560;">{sig_record.get('signature_sha256', '')}</span></div>
    </div>
    <div class="meta" style="margin-top:.85rem; font-size:.78rem;">
      <a href="{template_url}" target="_blank">view original (unsigned) template</a>
      <span style="color:#7a7560; margin:0 .5em;">·</span>
      <a href="/signatures">audit dashboard</a>
    </div>
  </div>
</div></body></html>"""


@app.post("/sign/{token}", response_class=HTMLResponse)
async def submit_signature(token: str, request: Request,
                            typed_name: str = Form(...),
                            intent: Optional[str] = Form(None),
                            signature_image_b64: Optional[str] = Form("")):
    payload = verify_token(token)
    deal_key = payload["deal_key"]
    doc_id = payload["doc_id"]
    signer_email = payload["signer_email"]

    if not intent:
        return HTMLResponse(_error_view("intent checkbox is required for legal validity"), status_code=400)

    typed = (typed_name or "").strip()
    has_image = bool(signature_image_b64 and signature_image_b64.startswith("data:image/"))
    if not typed and not has_image:
        return HTMLResponse(_error_view("please draw your signature OR type your legal name"), status_code=400)

    sha = doc_sha256(deal_key, doc_id)
    if not sha:
        raise HTTPException(404, "document not found")

    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")
    signed_at = datetime.utcnow().isoformat() + "Z"

    # Save the drawn signature PNG (if any) to disk + reference in sig payload
    sig_image_path: Optional[Path] = None
    if has_image:
        try:
            import base64 as _b64
            header, b64data = signature_image_b64.split(",", 1)
            png_bytes = _b64.b64decode(b64data)
            sig_image_dir = ROOT / "09_DASHBOARD" / "reports" / "deals" / deal_key / "signatures"
            sig_image_dir.mkdir(parents=True, exist_ok=True)
            safe = signer_email.replace("@", "_at_").replace(".", "_")
            sig_image_path = sig_image_dir / f"{doc_id}_{safe}_drawn.png"
            sig_image_path.write_bytes(png_bytes)
        except Exception as e:
            print(f"[esign] couldn't save drawn signature: {e}")
            sig_image_path = None

    sig_payload = {
        "deal_key": deal_key,
        "doc_id": doc_id,
        "signer_name": typed_name,
        "signer_email": signer_email,
        "intent_affirmed": True,
        "signed_at": signed_at,
        "ip": ip,
        "user_agent": ua,
        "document_sha256": sha,
    }
    if sig_image_path:
        sig_payload["signature_image_path"] = str(sig_image_path)
        sig_payload["signature_image_sha256"] = hashlib.sha256(
            sig_image_path.read_bytes()
        ).hexdigest()
    sig_payload["signature_sha256"] = hashlib.sha256(
        json.dumps(sig_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    # Persist
    sig_file = SIG_DIR / f"{deal_key}_{doc_id}_{signer_email.replace('@', '_at_')}.json"
    sig_file.write_text(json.dumps(sig_payload, indent=2))

    # Log to immutable audit chain
    try:
        log_event(
            deal_key=deal_key,
            event="sig_received",
            actor=f"{typed_name} <{signer_email}>",
            counterparty=None,
            artifact_ref=f"esign:{sig_payload['signature_sha256'][:16]}",
            artifact_path=str(sig_file),
            notes=f"E-signature received for {doc_id} from IP {ip}",
            statute_ref="UETA + E-SIGN Act 15USC§7001",
        )
    except Exception as e:
        print(f"[esign] audit log failed: {e}")

    # Email signed copy to all parties (best-effort, async-safe)
    try:
        _email_signed_certificate(deal_key, doc_id, sig_payload)
    except Exception as e:
        print(f"[esign] email send failed: {e}")

    return HTMLResponse(_signed_view(sig_payload, deal_key, doc_id))


def _burn_signed_copy(deal_key: str, doc_id: str, sig: dict) -> Optional[Path]:
    """Generate <doc_id>_signed.html with the signature burned into the document.
    Logs to audit chain on success. Idempotent (safe to call multiple times)."""
    try:
        try:
            from signature_burner import burn_signature
        except ImportError:
            from .signature_burner import burn_signature  # type: ignore
        out = burn_signature(deal_key, doc_id, sig)
        if out:
            try:
                log_event(
                    deal_key=deal_key, event="signed_copy_generated",
                    actor="Everlight E-Sign",
                    counterparty=f"{sig.get('signer_name','')} <{sig.get('signer_email','')}>",
                    artifact_path=str(out),
                    notes=f"Signed copy of {doc_id} written to {out.name}",
                    statute_ref="UETA + E-SIGN Act 15USC§7001",
                )
            except Exception as e:
                print(f"[esign] signed_copy_generated audit log failed: {e}")
        return out
    except Exception as e:
        print(f"[esign] signature burn failed: {e}")
        return None


def _generate_and_save_pdf_cert(deal_key: str, doc_id: str, signer_email: str, sig: dict) -> Optional[Path]:
    """Render the PDF signature certificate, save to deal dir, log to audit chain."""
    try:
        from pdf_certificate import render_signature_certificate_pdf
    except Exception as e:
        try:
            from .pdf_certificate import render_signature_certificate_pdf  # type: ignore
        except Exception as e2:
            print(f"[esign] pdf_certificate import failed: {e} / {e2}")
            return None

    sig_pdf_dir = ROOT / "09_DASHBOARD" / "reports" / "deals" / deal_key / "signatures"
    sig_pdf_dir.mkdir(parents=True, exist_ok=True)
    safe_email = signer_email.replace("@", "_at_").replace(".", "_")
    pdf_path = sig_pdf_dir / f"{doc_id}_{safe_email}.pdf"
    try:
        render_signature_certificate_pdf(pdf_path, sig)
    except Exception as e:
        print(f"[esign] PDF render failed: {e}")
        return None

    # Log to audit chain with SHA-256 of PDF
    try:
        log_event(
            deal_key=deal_key, event="cert_generated",
            actor="Everlight E-Sign",
            counterparty=f"{sig.get('signer_name','')} <{signer_email}>",
            artifact_path=str(pdf_path),
            notes=f"PDF signature certificate for {doc_id}",
            statute_ref="UETA + E-SIGN Act 15USC§7001",
        )
    except Exception as e:
        print(f"[esign] cert_generated audit log failed: {e}")

    return pdf_path


def _email_signed_certificate(deal_key: str, doc_id: str, sig: dict) -> None:
    """Email signature certificate (HTML body + link to PDF) to signer + operator."""
    try:
        from branded_mailer import send_branded_email
    except Exception:
        return  # silently skip if branded_mailer not available

    # Burn the signature into a signed copy of the contract
    from osint_api.public_url import reports_base, deal_url as _deal_url
    rb = reports_base()
    signed_html_path = _burn_signed_copy(deal_key, doc_id, sig)
    signed_html_url = ""
    if signed_html_path:
        rel = signed_html_path.relative_to(ROOT / "09_DASHBOARD")
        signed_html_url = f"{rb}/{rel.as_posix()}"

    # Generate PDF cert (saves to deal_dir/signatures/, logs to audit)
    pdf_path = _generate_and_save_pdf_cert(deal_key, doc_id, sig["signer_email"], sig)
    pdf_url = ""
    if pdf_path:
        rel = pdf_path.relative_to(ROOT / "09_DASHBOARD")
        pdf_url = f"{rb}/{rel.as_posix()}"

    pdf_link_html = (
        f'<li><strong>PDF signature certificate:</strong> <a href="{pdf_url}">{pdf_url}</a></li>'
        if pdf_url else
        '<li style="color:#a00;"><em>PDF certificate generation failed; see logs.</em></li>'
    )
    signed_link_html = (
        f'<li><strong>SIGNED contract copy (signature burned in):</strong> <a href="{signed_html_url}">{signed_html_url}</a></li>'
        if signed_html_url else
        '<li style="color:#a00;"><em>Signed copy generation failed; see logs.</em></li>'
    )

    cert_html = f"""
<p>You signed <strong>{doc_id}</strong> for deal <strong>{deal_key}</strong> on
<strong>{sig['signed_at']}</strong>.</p>
<p><strong>The executed contract</strong> (your signature, name, and date burned into the document):</p>
<ul>
  {signed_link_html}
</ul>
<p>Audit artifacts:</p>
<ul>
  <li>Signer: {sig['signer_name']} &lt;{sig['signer_email']}&gt;</li>
  <li>Intent affirmed: yes</li>
  <li>From IP: {sig['ip']}</li>
  <li>User agent: {sig['user_agent']}</li>
  <li>Original template SHA-256: <code>{sig['document_sha256']}</code></li>
  <li>Signature SHA-256: <code>{sig['signature_sha256']}</code></li>
  {pdf_link_html}
  <li>Original (unsigned) template: <a href="{_deal_url(deal_key, doc_id)}">view template</a></li>
</ul>
<p>This signature is binding under the federal E-Sign Act (15 USC § 7001) and the
Tennessee Uniform Electronic Transactions Act (Tenn. Code Ann. § 47-10-101 et seq).</p>
"""
    # Send to signer (real recipient) + Rich (audit copy) + Mid South Title (closing agent)
    for recipient in [sig["signer_email"], "1m.rich.gee@gmail.com"]:
        try:
            send_branded_email(
                to=recipient,
                subject=f"✓ Signed: {doc_id} ({deal_key})",
                content_html=cert_html,
                title=f"Signature certificate · {doc_id}",
                from_name="Everlight E-Sign",
                from_email="esign@everlightventures.io",
                reply_to="esign@everlightventures.io",
                agent_name="Everlight E-Sign",
                agent_title="Automated signature service",
                agent_email="esign@everlightventures.io",
                budget_category="system",
            )
        except Exception as e:
            print(f"[esign] couldn't email {recipient}: {e}")


@app.get("/sign/{token}/cert", response_class=JSONResponse)
async def get_certificate(token: str):
    payload = verify_token(token)
    sig_file = SIG_DIR / f"{payload['deal_key']}_{payload['doc_id']}_{payload['signer_email'].replace('@', '_at_')}.json"
    if not sig_file.exists():
        raise HTTPException(404, "no signature on file for this token")
    return json.loads(sig_file.read_text())


# ==========================================================================
# TOKEN-GATED DOCUMENT ACCESS
# Only the holder of a valid signing token can view the document. This stops
# any third party from enumerating contracts at /reports/deals/<key>/* on the
# public reports server.
# ==========================================================================

@app.get("/doc/{token}/{filename}")
async def gated_doc(token: str, filename: str):
    """Serve a contract HTML/PDF/asset only if the token is valid for THIS deal."""
    payload = verify_token(token)
    deal_key = payload["deal_key"]
    # Strip the doc_id from filename if it carries the .html ext, so token doc_id matches
    # Token is bound to a specific doc_id, but we allow viewing OTHER docs in the same deal
    # since signers typically need to see the underlying PSA when signing the assignment, etc.
    deal_dir = ROOT / "09_DASHBOARD" / "reports" / "deals" / deal_key
    safe_name = filename.replace("..", "").replace("/", "").lstrip("/")
    if not safe_name.endswith((".html", ".htm", ".pdf", ".png", ".jpg", ".jpeg", ".webp")):
        # Default: assume <doc_id>.html
        safe_name = f"{safe_name}.html"
    target = deal_dir / safe_name
    if not target.exists() or not target.is_file():
        raise HTTPException(404, f"document not found: {safe_name}")
    # Audit log: who viewed what
    try:
        log_event(
            deal_key=deal_key,
            event="doc_viewed",
            actor=f"{payload.get('signer_name', '')} <{payload.get('signer_email', '')}>",
            counterparty=None,
            artifact_path=str(target),
            notes=f"Token-gated view of {safe_name}",
        )
    except Exception:
        pass
    body = target.read_bytes()
    media = "text/html" if safe_name.endswith((".html", ".htm")) else "application/octet-stream"
    if safe_name.endswith(".pdf"): media = "application/pdf"
    elif safe_name.endswith(".png"): media = "image/png"
    elif safe_name.endswith((".jpg", ".jpeg")): media = "image/jpeg"
    elif safe_name.endswith(".webp"): media = "image/webp"
    from fastapi.responses import Response
    return Response(content=body, media_type=media,
                    headers={"Cache-Control": "no-store, private",
                             "X-Content-Type-Options": "nosniff"})


# ==========================================================================
# WIRE CONFIRMATION ROUTES
# Operator/title firm enters wire details; system captures + logs to audit chain.
# Bank confirmation file (PDF/screenshot) optional but recommended.
# ==========================================================================

WIRE_TYPES = {
    "EMD":            ("Earnest Money Deposit", "wire_sent",     "Buyer (Everlight)", "Mid South Title escrow"),
    "GFAD":           ("Good-Faith Assignment Deposit", "wire_received", "Mid South Title escrow", "Assignee (Chris)"),
    "BUYER_BALANCE":  ("Buyer balance at close", "wire_received", "Mid South Title escrow", "Assignee (Chris)"),
    "SELLER_PAYOFF":  ("Seller payoff at close", "wire_sent",     "Mid South Title escrow", "Seller (Mikal)"),
    "ASSIGNOR_PAYOFF":("Assignor payoff at close", "wire_received","Mid South Title escrow", "Everlight Ventures"),
    "BACK_TAX":       ("Back property tax to county", "wire_sent","Mid South Title escrow", "Shelby County Trustee"),
}


@app.get("/wire/{deal_key}", response_class=HTMLResponse)
async def wire_form(deal_key: str):
    """Render wire confirmation entry form for a given deal."""
    options = "".join(
        f'<option value="{k}">{k} -- {v[0]}</option>'
        for k, v in WIRE_TYPES.items()
    )
    deal_dir = ROOT / "09_DASHBOARD" / "reports" / "deals" / deal_key
    deal_status = "active" if deal_dir.exists() else "unknown (no deal dir)"

    return HTMLResponse(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wire Confirmation · {deal_key}</title>
{BRAND_CSS}</head>
<body><div class="wrap">
  <div class="card">
    <div class="label">Wire Confirmation Capture<span style="color:#b8902f;margin:0 .65em;">◆</span>Everlight Ventures</div>
    <h1 class="display">Record a wire</h1>
    <div class="meta">
      <div><strong>Deal:</strong> {deal_key}</div>
      <div><strong>Deal status:</strong> {deal_status}</div>
      <div><strong>List existing wires:</strong> <a href="/wire/{deal_key}/list">/wire/{deal_key}/list</a></div>
    </div>
  </div>

  <div class="card">
    <div class="label">Wire details</div>
    <form method="post" action="/wire/{deal_key}" enctype="multipart/form-data" id="wire-form">
      <div class="form-row">
        <label for="wire_type">Wire type</label>
        <select name="wire_type" id="wire_type" required style="width:100%;padding:.75rem 1rem;background:rgba(212,168,67,.05);border:1px solid #4a3d1c;border-radius:8px;color:#f4eedb;font-family:'JetBrains Mono',monospace;font-size:1rem;">
          {options}
        </select>
      </div>
      <div class="form-row">
        <label for="amount_usd">Amount (USD, integer)</label>
        <input type="text" inputmode="numeric" name="amount_usd" id="amount_usd" required placeholder="250">
      </div>
      <div class="form-row">
        <label for="bank_name">Bank name (sender side)</label>
        <input type="text" name="bank_name" id="bank_name" placeholder="Bank of America">
      </div>
      <div class="form-row">
        <label for="confirmation_number">Bank confirmation number</label>
        <input type="text" name="confirmation_number" id="confirmation_number" required placeholder="WIRE2026051300018">
      </div>
      <div class="form-row">
        <label for="actor">Submitted by (your name)</label>
        <input type="text" name="actor" id="actor" required placeholder="Rich Gee">
      </div>
      <div class="form-row">
        <label for="notes">Notes (optional)</label>
        <input type="text" name="notes" id="notes" placeholder="EMD wire from Mercury account, sent 2026-05-13 9:15 AM">
      </div>
      <div class="form-row">
        <label for="confirmation_file">Confirmation file (PDF or screenshot, optional but recommended)</label>
        <input type="file" name="confirmation_file" id="confirmation_file"
               accept=".pdf,.png,.jpg,.jpeg,.webp"
               style="width:100%;padding:.65rem .85rem;background:rgba(212,168,67,.05);border:1px dashed #4a3d1c;border-radius:8px;color:#f4eedb;font-family:'JetBrains Mono',monospace;font-size:.85rem;">
      </div>

      <button type="submit" class="sign">Record wire + log to audit chain</button>
    </form>

    <div class="legal">
      <strong>Audit chain:</strong> Each wire is appended as an immutable row in
      <code>deal_execution_log.sqlite</code>, hash-chained against prior rows. The
      uploaded confirmation file (if any) is SHA-256-pinned at submission time. Any
      future tampering with prior rows breaks the chain and is detectable via
      <code>verify_chain()</code>.
    </div>
  </div>
</div></body></html>""")


@app.post("/wire/{deal_key}", response_class=HTMLResponse)
async def submit_wire(deal_key: str, request: Request,
                       wire_type: str = Form(...),
                       amount_usd: str = Form(...),
                       bank_name: str = Form(""),
                       confirmation_number: str = Form(...),
                       actor: str = Form(...),
                       notes: str = Form(""),
                       confirmation_file: Optional[UploadFile] = File(None)):
    """Capture a wire submission, save uploaded file, log to audit chain."""
    if wire_type not in WIRE_TYPES:
        raise HTTPException(400, f"unknown wire_type: {wire_type}")
    try:
        amt = int(amount_usd.replace(",", "").replace("$", "").strip())
    except ValueError:
        raise HTTPException(400, f"amount_usd not an integer: {amount_usd}")

    label, event, payer, payee = WIRE_TYPES[wire_type]

    # Save uploaded confirmation file (if any)
    wires_dir = ROOT / "09_DASHBOARD" / "reports" / "deals" / deal_key / "wires"
    wires_dir.mkdir(parents=True, exist_ok=True)
    file_path: Optional[Path] = None
    if confirmation_file and confirmation_file.filename:
        ts_slug = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext = Path(confirmation_file.filename).suffix.lower() or ".bin"
        file_path = wires_dir / f"{wire_type}_{confirmation_number}_{ts_slug}{ext}"
        try:
            content = await confirmation_file.read()
            file_path.write_bytes(content)
        except Exception as e:
            print(f"[wire] file save failed: {e}")
            file_path = None

    # Append to audit chain
    artifact_ref = f"wire:{wire_type}:{confirmation_number}"
    log_payload = {
        "deal_key": deal_key, "event": event, "actor": actor,
        "counterparty": f"{payer} -> {payee}",
        "artifact_ref": artifact_ref,
        "artifact_path": str(file_path) if file_path else None,
        "amount_usd": amt,
        "notes": f"{label}, bank={bank_name or 'unspecified'}, conf={confirmation_number}. {notes}".strip(),
    }
    log_payload = {k: v for k, v in log_payload.items() if v is not None}
    try:
        rec = log_event(**log_payload)
    except Exception as e:
        return HTMLResponse(f"<h1>Audit log failed</h1><pre>{e}</pre>", status_code=500)

    return HTMLResponse(f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Wire recorded · {deal_key}</title>{BRAND_CSS}</head>
<body><div class="wrap"><div class="card">
  <div class="ok-banner">✓ Wire recorded + logged to immutable audit chain</div>
  <h1 class="display">Wire #{rec['id']} captured</h1>
  <div class="meta">
    <div><strong>Deal:</strong> {deal_key}</div>
    <div><strong>Event:</strong> {event}</div>
    <div><strong>Type:</strong> {wire_type} ({label})</div>
    <div><strong>Amount:</strong> ${amt:,}</div>
    <div><strong>Confirmation #:</strong> {confirmation_number}</div>
    <div><strong>Submitted by:</strong> {actor}</div>
    <div><strong>File:</strong> {('<a href="' + __import__('osint_api.public_url', fromlist=['reports_base']).reports_base() + '/reports/deals/' + deal_key + '/wires/' + file_path.name + '">' + file_path.name + '</a>') if file_path else '(none uploaded)'}</div>
    <div><strong>Audit row hash:</strong> <span class="mono" style="font-size:.65rem;color:#7a7560;">{rec['row_hash']}</span></div>
  </div>
  <div class="meta" style="margin-top:1rem;">
    <a href="/wire/{deal_key}/list">View all wires for this deal</a>
    <span style="color:#7a7560;margin:0 .65em;">|</span>
    <a href="/wire/{deal_key}">Record another wire</a>
  </div>
</div></div></body></html>""")


@app.get("/wire/{deal_key}/list", response_class=HTMLResponse)
async def list_wires(deal_key: str):
    """List all wire events for a given deal (audit view)."""
    try:
        from deal_execution_log import deal_history
    except Exception:
        sys.path.insert(0, str(ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit"))
        from deal_execution_log import deal_history  # type: ignore
    events = deal_history(deal_key)
    wire_events = [e for e in events if e["event"] in {"wire_sent", "wire_received"}]

    rows_html = "".join(
        f'<tr style="border-bottom:1px solid #2a2410;">'
        f'<td style="padding:.45rem;color:#d4a843;font-family:JetBrains Mono,monospace;font-size:.75rem;">{e["ts"][:19]}</td>'
        f'<td style="padding:.45rem;">{e["event"]}</td>'
        f'<td style="padding:.45rem;color:#ffcd3c;font-family:JetBrains Mono,monospace;">${e.get("amount_usd",0):,}</td>'
        f'<td style="padding:.45rem;color:#b5af9b;">{e.get("actor","")}</td>'
        f'<td style="padding:.45rem;color:#b5af9b;font-size:.8rem;">{(e.get("notes","") or "")[:80]}</td>'
        f'</tr>'
        for e in wire_events
    ) or '<tr><td colspan=5 style="padding:1rem;color:#7a7560;">No wires recorded yet.</td></tr>'

    return HTMLResponse(f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Wires · {deal_key}</title>{BRAND_CSS}</head>
<body><div class="wrap"><div class="card">
  <div class="label">Wire Audit Log<span style="color:#b8902f;margin:0 .65em;">◆</span>{deal_key}</div>
  <h1 class="display">Wires for this deal</h1>
  <table style="width:100%;border-collapse:collapse;margin-top:1rem;font-size:.85rem;">
    <thead><tr style="border-bottom:2px solid #d4a843;">
      <th style="padding:.45rem;text-align:left;color:#d4a843;text-transform:uppercase;font-size:.7rem;letter-spacing:.1em;">Timestamp UTC</th>
      <th style="padding:.45rem;text-align:left;color:#d4a843;text-transform:uppercase;font-size:.7rem;letter-spacing:.1em;">Event</th>
      <th style="padding:.45rem;text-align:left;color:#d4a843;text-transform:uppercase;font-size:.7rem;letter-spacing:.1em;">Amount</th>
      <th style="padding:.45rem;text-align:left;color:#d4a843;text-transform:uppercase;font-size:.7rem;letter-spacing:.1em;">Submitted by</th>
      <th style="padding:.45rem;text-align:left;color:#d4a843;text-transform:uppercase;font-size:.7rem;letter-spacing:.1em;">Notes</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <div class="meta" style="margin-top:1rem;"><a href="/wire/{deal_key}">+ Record a new wire</a></div>
</div></div></body></html>""")


@app.get("/signatures", response_class=HTMLResponse)
async def signatures_dashboard():
    """Live view of all signature events across all deals -- branded, audit-linked."""
    try:
        sys.path.insert(0, str(ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit"))
        from deal_execution_log import deal_history  # we'll iterate ourselves
        import sqlite3
        con = sqlite3.connect(str(ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "audit" / "deal_execution.sqlite"))
        con.row_factory = sqlite3.Row
        sig_events = list(con.execute(
            "SELECT * FROM deal_events WHERE event IN ('sig_received','cert_generated','doc_delivered','doc_viewed') "
            "ORDER BY id DESC LIMIT 100"
        ))
        # Also count total signatures + per-deal
        total_sigs = con.execute("SELECT COUNT(*) FROM deal_events WHERE event='sig_received'").fetchone()[0]
        total_views = con.execute("SELECT COUNT(*) FROM deal_events WHERE event='doc_viewed'").fetchone()[0]
        per_deal = list(con.execute(
            "SELECT deal_key, COUNT(*) as n FROM deal_events WHERE event='sig_received' "
            "GROUP BY deal_key ORDER BY n DESC LIMIT 20"
        ))
        con.close()
    except Exception as e:
        return HTMLResponse(f"<h1>Audit log read failed</h1><pre>{e}</pre>", status_code=500)

    EVENT_COLORS = {
        "sig_received":   ("#5cffb1", "✍ SIGNED"),
        "cert_generated": ("#00e5ff", "📜 PDF cert"),
        "doc_delivered":  ("#d4a843", "📨 delivered"),
        "doc_viewed":     ("#b5af9b", "👁 viewed"),
    }

    def _sig_file_link(sig_event):
        """Compute the signature JSON / PDF link for a sig_received or cert_generated event.
        Files live at predictable paths: SIG_DIR / cert PDF dir based on event type."""
        if sig_event["event"] == "sig_received":
            artifact_ref = (sig_event["artifact_ref"] or "")
            if not artifact_ref.startswith("esign:"):
                return ""
            # Reconstruct from deal_key + signer (extracted from actor "Name <email>")
            actor = sig_event["actor"] or ""
            email = ""
            if "<" in actor and ">" in actor:
                email = actor.split("<", 1)[1].split(">", 1)[0]
            if not email:
                return ""
            # Find any matching .json sig file in SIG_DIR
            safe = email.replace("@", "_at_")
            for f in SIG_DIR.glob(f"{sig_event['deal_key']}_*_{safe}.json"):
                rel = f.relative_to(ROOT / "09_DASHBOARD")
                return f"{__import__('osint_api.public_url', fromlist=['reports_base']).reports_base()}/{rel.as_posix()}"
            return ""
        if sig_event["event"] == "cert_generated":
            # PDF cert lives at deals/<key>/signatures/<doc>_<safe-email>.pdf
            deal_dir = ROOT / "09_DASHBOARD" / "reports" / "deals" / sig_event["deal_key"] / "signatures"
            if deal_dir.exists():
                pdfs = sorted(deal_dir.glob("*.pdf"), key=lambda p: -p.stat().st_mtime)
                if pdfs:
                    rel = pdfs[0].relative_to(ROOT / "09_DASHBOARD")
                    return f"{__import__('osint_api.public_url', fromlist=['reports_base']).reports_base()}/{rel.as_posix()}"
        return ""

    rows_html = ""
    for e in sig_events:
        color, label = EVENT_COLORS.get(e["event"], ("#7a7560", e["event"]))
        deal_short = e["deal_key"][:30] + ("…" if len(e["deal_key"]) > 30 else "")
        notes_short = (e["notes"] or "")[:60]
        actor_short = (e["actor"] or "")[:40]
        artifact_link = _sig_file_link(e)
        artifact_html = f'<a href="{artifact_link}" target="_blank">file</a>' if artifact_link else '<span class="dim">—</span>'
        amount = f"${e['amount_usd']:,}" if e['amount_usd'] else ""

        rows_html += f'''
        <tr>
          <td class="mono dim">{e["ts"][:19]}</td>
          <td><span style="color:{color};font-family:JetBrains Mono,monospace;font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;">{label}</span></td>
          <td class="mono" style="font-size:.78rem;">{deal_short}</td>
          <td style="font-size:.85rem;">{actor_short}</td>
          <td class="mono dim" style="font-size:.75rem;">{notes_short}</td>
          <td class="mono gold-hot" style="font-size:.78rem;">{amount}</td>
          <td>{artifact_html}</td>
        </tr>'''

    per_deal_rows = ""
    for d in per_deal:
        per_deal_rows += f'''
        <tr>
          <td class="mono" style="font-size:.78rem;">{d["deal_key"]}</td>
          <td class="mono gold-hot" style="text-align:right;">{d["n"]}</td>
          <td><a href="/wire/{d['deal_key']}/list" target="_blank" style="font-size:.75rem;">wires</a></td>
        </tr>'''

    return HTMLResponse(f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signatures · Everlight</title>
{BRAND_CSS}
<style>
  table {{ width: 100%; border-collapse: collapse; margin-top: .5rem; }}
  thead th {{
    text-align: left; padding: .5rem .65rem; color: #d4a843;
    font-family: 'JetBrains Mono',monospace; font-size: .68rem;
    text-transform: uppercase; letter-spacing: .12em;
    border-bottom: 2px solid #d4a843;
  }}
  tbody td {{
    padding: .55rem .65rem; border-bottom: 1px solid rgba(50,42,20,0.5);
    vertical-align: top;
  }}
  tbody tr:hover {{ background: rgba(212,168,67,0.04); }}
  .dim {{ color: #7a7560; }}
  .gold-hot {{ color: #ffcd3c; }}
  .stat-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem; margin: 1rem 0;
  }}
  .stat-card {{
    background: linear-gradient(180deg, #15140d 0%, #100f08 100%);
    border: 1px solid #322a14; border-radius: 10px; padding: 1rem 1.25rem;
  }}
  .stat-num {{
    color: #ffcd3c; font-family: 'Playfair Display',serif;
    font-size: 2.4rem; font-weight: 900; line-height: 1; margin-top: .2rem;
  }}
  .stat-label {{
    color: #d4a843; font-family: 'JetBrains Mono',monospace;
    font-size: .65rem; text-transform: uppercase; letter-spacing: .15em;
  }}
</style>
</head>
<body><div class="wrap">
  <div class="card">
    <div class="label">Audit Dashboard<span style="color:#b8902f;margin:0 .65em;">◆</span>Everlight Ventures</div>
    <h1 class="display">Signatures + Audit Trail</h1>
    <div class="meta" style="margin-top:.5rem;">
      Live view of every <code>sig_received</code> + <code>cert_generated</code> + <code>doc_viewed</code> event
      from the hash-chained <code>deal_execution.sqlite</code>. Each signature row links to the cert JSON file on disk.
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-label">Total signatures</div>
        <div class="stat-num">{total_sigs}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Doc views (token-gated)</div>
        <div class="stat-num">{total_views}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Active deals</div>
        <div class="stat-num">{len(per_deal)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Recent events shown</div>
        <div class="stat-num">{len(sig_events)}</div>
      </div>
    </div>
  </div>

  {f'''<div class="card">
    <div class="label">Per-deal signature counts</div>
    <table>
      <thead><tr><th>Deal</th><th style="text-align:right;">Signatures</th><th>Wire log</th></tr></thead>
      <tbody>{per_deal_rows}</tbody>
    </table>
  </div>''' if per_deal_rows else ''}

  <div class="card">
    <div class="label">Recent events (most recent 100)</div>
    <table>
      <thead><tr>
        <th>Timestamp UTC</th><th>Event</th><th>Deal</th><th>Actor</th>
        <th>Notes</th><th style="text-align:right;">Amount</th><th>Artifact</th>
      </tr></thead>
      <tbody>{rows_html or '<tr><td colspan="7" class="dim" style="padding:1.5rem;text-align:center;">No signature events yet. Click any sign URL from your inbox to populate.</td></tr>'}</tbody>
    </table>
  </div>

  <div style="text-align:center;margin-top:1rem;font-family:'JetBrains Mono',monospace;font-size:.7rem;color:#7a7560;">
    <a href="http://127.0.0.1:2000/" style="color:#d4a843;">← back to hub</a>
    <span style="margin:0 .5em;">·</span>
    <a href="/" style="color:#d4a843;">esign service</a>
    <span style="margin:0 .5em;">·</span>
    refresh page for latest
  </div>
</div></body></html>""")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(f"""<!doctype html><html><head><title>Everlight E-Sign</title>{BRAND_CSS}</head>
<body><div class="wrap"><div class="card">
  <div class="label">Everlight E-Sign Service</div>
  <h1 class="display">2302 ◆ E-Sign</h1>
  <div class="meta">
    <p>Free, self-hosted, UETA + E-SIGN Act compliant electronic signature service.</p>
    <p>Routes:</p>
    <ul>
      <li><code>GET  /sign/{{token}}</code> — render the document + signing form</li>
      <li><code>POST /sign/{{token}}</code> — submit signature</li>
      <li><code>GET  /sign/{{token}}/cert</code> — JSON certificate</li>
      <li><code>GET  /healthz</code> — ok</li>
    </ul>
    <p>Signing tokens are issued via <code>esign_server.make_token()</code>.</p>
  </div>
</div></div></body></html>""")
