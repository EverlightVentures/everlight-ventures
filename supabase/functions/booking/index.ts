// Everlight Ventures -- Booking Page
// Simple scheduling page that lets prospects pick a time slot.
// Serves HTML at GET, processes bookings at POST.
// Deployed as Supabase Edge Function.

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

// Generate next 5 business days with 3 slots each
function getAvailableSlots(): { date: string; day: string; slots: string[] }[] {
  const days = [];
  const now = new Date();
  let d = new Date(now);
  d.setDate(d.getDate() + 1); // start tomorrow

  while (days.length < 5) {
    const dow = d.getDay();
    if (dow !== 0 && dow !== 6) {
      // weekday
      const dateStr = d.toISOString().split("T")[0];
      const dayName = d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric", timeZone: "America/Los_Angeles" });
      days.push({
        date: dateStr,
        day: dayName,
        slots: ["10:00 AM PT", "1:00 PM PT", "3:00 PM PT"],
      });
    }
    d.setDate(d.getDate() + 1);
  }
  return days;
}

function renderPage(): string {
  const slots = getAvailableSlots();
  const slotsHtml = slots
    .map(
      (day) => `
    <div class="day-group">
      <div class="day-label">${day.day}</div>
      <div class="slots">
        ${day.slots.map((s) => `<button class="slot-btn" data-date="${day.date}" data-time="${s}" onclick="selectSlot(this)">${s}</button>`).join("")}
      </div>
    </div>`
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Book a Call - Everlight Ventures</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0f; color: #e0e0e0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    .container { max-width: 480px; width: 100%; padding: 20px; }
    .logo { text-align: center; margin-bottom: 32px; }
    .logo-mark { width: 48px; height: 48px; border-radius: 12px; background: linear-gradient(135deg, #f59e0b, #ea580c, #dc2626); display: inline-flex; align-items: center; justify-content: center; font-weight: 900; font-size: 20px; color: #000; margin-bottom: 8px; }
    .logo h1 { font-size: 14px; letter-spacing: 0.25em; background: linear-gradient(90deg, #fbbf24, #f97316); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .logo p { font-size: 10px; color: #666; letter-spacing: 0.15em; }
    .card { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 24px; backdrop-filter: blur(10px); }
    h2 { font-size: 18px; margin-bottom: 4px; color: #fff; }
    .subtitle { font-size: 12px; color: #888; margin-bottom: 20px; }
    .agent-info { display: flex; align-items: center; gap: 12px; padding: 12px; background: rgba(245,158,11,0.05); border: 1px solid rgba(245,158,11,0.1); border-radius: 10px; margin-bottom: 20px; }
    .agent-avatar { width: 40px; height: 40px; border-radius: 10px; background: linear-gradient(135deg, rgba(236,72,153,0.3), rgba(245,158,11,0.2)); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; color: #f59e0b; }
    .agent-name { font-size: 13px; font-weight: 600; color: #fbbf24; }
    .agent-role { font-size: 10px; color: #888; }
    .day-group { margin-bottom: 16px; }
    .day-label { font-size: 11px; font-weight: 600; color: #999; letter-spacing: 0.1em; margin-bottom: 6px; }
    .slots { display: flex; gap: 8px; }
    .slot-btn { flex: 1; padding: 10px 0; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: rgba(255,255,255,0.02); color: #ccc; font-size: 12px; cursor: pointer; transition: all 0.2s; }
    .slot-btn:hover { border-color: rgba(245,158,11,0.3); color: #fbbf24; background: rgba(245,158,11,0.05); }
    .slot-btn.selected { border-color: #f59e0b; color: #f59e0b; background: rgba(245,158,11,0.1); font-weight: 600; }
    .form-group { margin-top: 20px; }
    .form-group label { display: block; font-size: 10px; color: #888; letter-spacing: 0.1em; margin-bottom: 4px; }
    .form-group input { width: 100%; padding: 10px 12px; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: rgba(255,255,255,0.03); color: #e0e0e0; font-size: 13px; outline: none; }
    .form-group input:focus { border-color: rgba(245,158,11,0.3); }
    .book-btn { width: 100%; margin-top: 20px; padding: 12px; border: none; border-radius: 10px; background: linear-gradient(135deg, #f59e0b, #ea580c); color: #000; font-size: 13px; font-weight: 700; letter-spacing: 0.05em; cursor: pointer; transition: all 0.2s; }
    .book-btn:hover { opacity: 0.9; transform: translateY(-1px); }
    .book-btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .success { text-align: center; padding: 40px 20px; }
    .success h3 { color: #fbbf24; margin-bottom: 8px; }
    .success p { color: #888; font-size: 13px; }
    .footer { text-align: center; margin-top: 20px; font-size: 9px; color: #444; }
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">
      <div class="logo-mark">EV</div>
      <h1>EVERLIGHT VENTURES</h1>
      <p>PARTNERSHIP CALL</p>
    </div>
    <div class="card" id="booking-form">
      <h2>Book a 15-Minute Call</h2>
      <p class="subtitle">Pick a time that works for you.</p>
      <div class="agent-info">
        <div class="agent-avatar">P</div>
        <div>
          <div class="agent-name">Piper Reeves</div>
          <div class="agent-role">Senior Outreach Specialist</div>
        </div>
      </div>
      ${slotsHtml}
      <div class="form-group">
        <label>YOUR NAME</label>
        <input type="text" id="name" placeholder="Jane Smith" required>
      </div>
      <div class="form-group">
        <label>EMAIL</label>
        <input type="email" id="email" placeholder="jane@company.com" required>
      </div>
      <div class="form-group">
        <label>COMPANY (OPTIONAL)</label>
        <input type="text" id="company" placeholder="Acme Corp">
      </div>
      <button class="book-btn" id="book-btn" disabled onclick="bookCall()">SELECT A TIME SLOT</button>
    </div>
    <div class="card success" id="success" style="display:none">
      <h3>You're Booked!</h3>
      <p>Piper will send you a calendar invite shortly. Looking forward to connecting.</p>
    </div>
    <div class="footer">Everlight Ventures &copy; 2026</div>
  </div>
  <script>
    let selectedDate = null, selectedTime = null;
    function selectSlot(btn) {
      document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      selectedDate = btn.dataset.date;
      selectedTime = btn.dataset.time;
      document.getElementById('book-btn').disabled = false;
      document.getElementById('book-btn').textContent = 'BOOK ' + selectedTime + ' ON ' + btn.closest('.day-group').querySelector('.day-label').textContent;
    }
    async function bookCall() {
      const name = document.getElementById('name').value.trim();
      const email = document.getElementById('email').value.trim();
      const company = document.getElementById('company').value.trim();
      if (!name || !email || !selectedDate || !selectedTime) { alert('Please fill in all fields and select a time.'); return; }
      const btn = document.getElementById('book-btn');
      btn.disabled = true; btn.textContent = 'BOOKING...';
      try {
        const resp = await fetch(window.location.href, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, company, date: selectedDate, time: selectedTime })
        });
        if (resp.ok) {
          document.getElementById('booking-form').style.display = 'none';
          document.getElementById('success').style.display = 'block';
        } else {
          btn.textContent = 'ERROR - TRY AGAIN'; btn.disabled = false;
        }
      } catch { btn.textContent = 'ERROR - TRY AGAIN'; btn.disabled = false; }
    }
  </script>
</body>
</html>`;
}

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: CORS });
  }

  if (req.method === "GET") {
    return new Response(renderPage(), {
      headers: { ...CORS, "Content-Type": "text/html; charset=utf-8" },
    });
  }

  if (req.method === "POST") {
    try {
      const body = await req.json();
      const { name, email, company, date, time } = body;

      // Store booking in Supabase
      const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
      const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";

      if (supabaseUrl && supabaseKey) {
        await fetch(`${supabaseUrl}/rest/v1/stark_commands`, {
          method: "POST",
          headers: {
            apikey: supabaseKey,
            Authorization: `Bearer ${supabaseKey}`,
            "Content-Type": "application/json",
            Prefer: "return=minimal",
          },
          body: JSON.stringify({
            user_id: "00000000-0000-0000-0000-000000000000",
            input_text: `BOOKING: ${name} (${email}) at ${company || "N/A"} - ${date} ${time}`,
            category: "deals",
            response_text: "Booking confirmed via Piper scheduling page",
            agents_used: ["Piper Reeves"],
            tier_at_time: "system",
          }),
        });
      }

      // Send confirmation email via Resend
      const resendKey = Deno.env.get("RESEND_API_KEY") || "";
      if (resendKey && email) {
        await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${resendKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from: "Piper Reeves <piper@everlightventures.io>",
            to: [email],
            reply_to: "sage@everlightventures.io",
            subject: `Confirmed: Call on ${date} at ${time}`,
            html: `<p>Hey ${name.split(" ")[0]},</p><p>You're all set! I've got us down for <b>${date} at ${time}</b>.</p><p>I'll send over a calendar invite shortly with the call link. Looking forward to connecting and exploring how Everlight can help.</p><p>Talk soon,<br>Piper Reeves<br>Senior Outreach Specialist<br>Everlight Ventures</p>`,
          }),
        });

        // Notify Rich via internal email
        await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${resendKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from: "Piper Reeves <piper@everlightventures.io>",
            to: ["1m.rich.gee@gmail.com"],
            subject: `[BOOKING] ${name} - ${company || "No company"} - ${date} ${time}`,
            html: `<p>New booking from the scheduling page:</p><ul><li><b>Name:</b> ${name}</li><li><b>Email:</b> ${email}</li><li><b>Company:</b> ${company || "N/A"}</li><li><b>Time:</b> ${date} at ${time}</li></ul><p>Piper will handle the call. Calendar invite going out.</p>`,
          }),
        });
      }

      // Post to Slack
      const slackToken = Deno.env.get("SLACK_BOT_TOKEN") || "";
      if (slackToken) {
        await fetch("https://slack.com/api/chat.postMessage", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${slackToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            channel: "C0ANLLV8JAC", // #broker-pipeline
            text: `*NEW BOOKING* via Piper's scheduling page\nName: ${name}\nEmail: ${email}\nCompany: ${company || "N/A"}\nTime: ${date} at ${time}`,
          }),
        });
      }

      return new Response(JSON.stringify({ ok: true }), {
        headers: { ...CORS, "Content-Type": "application/json" },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: String(err) }), {
        status: 500,
        headers: { ...CORS, "Content-Type": "application/json" },
      });
    }
  }

  return new Response("Method not allowed", { status: 405 });
});
