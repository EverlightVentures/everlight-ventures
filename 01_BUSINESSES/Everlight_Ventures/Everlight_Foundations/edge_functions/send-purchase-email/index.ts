// send-purchase-email: Auto-sends branded HTML email after every ebook purchase
// Called by verify-ebook-purchase after generating download link
// Uses Resend API (free tier: 3k emails/mo)

const SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const BOOK_TITLES: Record<string, string> = {
  "sam-book-1": "Sam's First Superpower",
  "sam-book-2": "Sam's Second Superpower",
  "sam-book-3": "Sam's Third Superpower",
  "sam-book-4": "Sam's Fourth Superpower",
  "sam-book-5": "Sam's Fifth Superpower",
  "sam-bundle": "Sam & Robo Complete Bundle (5 Books)",
  "beyond-the-veil": "Beyond the Veil",
};

function buildEmailHtml(
  bookTitle: string,
  downloadUrl: string,
  customerName?: string
): string {
  const greeting = customerName ? `Hi ${customerName}` : "Hi there";
  return `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0A0A0A;font-family:Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;background:#1A1A1A;border-radius:12px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#D4AF37,#B8960C);padding:30px;text-align:center;">
    <h1 style="color:#0A0A0A;margin:0;font-size:24px;">Everlight Ventures</h1>
    <p style="color:#0A0A0A;margin:8px 0 0;font-size:14px;">Publishing</p>
  </div>
  <div style="padding:30px;color:#E0E0E0;">
    <h2 style="color:#D4AF37;margin-top:0;">Your Book is Ready!</h2>
    <p>${greeting},</p>
    <p>Thank you for purchasing <strong>${bookTitle}</strong>! Your download is ready.</p>
    <div style="text-align:center;margin:30px 0;">
      <a href="${downloadUrl}" style="display:inline-block;background:#D4AF37;color:#0A0A0A;padding:16px 32px;text-decoration:none;border-radius:8px;font-weight:bold;font-size:16px;">Download Your Book</a>
    </div>
    <p style="color:#999;font-size:13px;">This link expires in 24 hours. If it expires, reply to this email and we'll send a new one.</p>
    <h3 style="color:#D4AF37;font-size:15px;">How to Read:</h3>
    <ol style="color:#CCC;line-height:1.8;">
      <li>Download and <strong>extract the ZIP file</strong></li>
      <li>Open the <strong>.html file</strong> in any web browser (Chrome, Safari, Firefox)</li>
      <li>The reader works offline with dark mode, font size controls, and chapter navigation</li>
      <li>The <strong>.epub file</strong> also works with Apple Books, Kindle, Google Play Books, or Calibre</li>
    </ol>
    <p>Need help? Just reply to this email or contact <a href="mailto:support@everlightventures.io" style="color:#D4AF37;">support@everlightventures.io</a></p>
  </div>
  <div style="background:#111;padding:20px;text-align:center;color:#666;font-size:12px;">
    <p style="margin:0;">Everlight Ventures &bull; everlightventures.io</p>
    <p style="margin:4px 0 0;">Stories built to last.</p>
  </div>
</div>
</body>
</html>`;
}

function buildRecoveryEmailHtml(
  bookTitle: string,
  downloadUrl: string,
  bonusTitle: string,
  bonusUrl: string
): string {
  return `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0A0A0A;font-family:Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;background:#1A1A1A;border-radius:12px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#D4AF37,#B8960C);padding:30px;text-align:center;">
    <h1 style="color:#0A0A0A;margin:0;font-size:24px;">Everlight Ventures</h1>
    <p style="color:#0A0A0A;margin:8px 0 0;font-size:14px;">We Owe You One</p>
  </div>
  <div style="padding:30px;color:#E0E0E0;">
    <h2 style="color:#D4AF37;margin-top:0;">Your Download + A Free Gift</h2>
    <p>Hi there,</p>
    <p>Thank you for your patience! We had a technical issue that delayed your download of <strong>${bookTitle}</strong>. Everything is fixed now.</p>
    <h3 style="color:#D4AF37;">${bookTitle} (Your Purchase)</h3>
    <div style="text-align:center;margin:20px 0;">
      <a href="${downloadUrl}" style="display:inline-block;background:#D4AF37;color:#0A0A0A;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;">Download ${bookTitle}</a>
    </div>
    <h3 style="color:#D4AF37;">${bonusTitle} (FREE - Our Gift To You)</h3>
    <div style="text-align:center;margin:20px 0;">
      <a href="${bonusUrl}" style="display:inline-block;background:#D4AF37;color:#0A0A0A;padding:14px 28px;text-decoration:none;border-radius:8px;font-weight:bold;">Download ${bonusTitle} (FREE)</a>
    </div>
    <h3 style="color:#D4AF37;font-size:15px;">How to Read:</h3>
    <ol style="color:#CCC;line-height:1.8;">
      <li>Download and <strong>extract the ZIP file</strong></li>
      <li>Open the <strong>.html file</strong> in any web browser</li>
      <li>The reader works offline with dark mode and chapter navigation</li>
      <li>The <strong>.epub</strong> works with Apple Books, Kindle, etc.</li>
    </ol>
    <p>Thank you for supporting Everlight Ventures. We're just getting started!</p>
    <p>Need help? Reply to this email or contact <a href="mailto:support@everlightventures.io" style="color:#D4AF37;">support@everlightventures.io</a></p>
  </div>
  <div style="background:#111;padding:20px;text-align:center;color:#666;font-size:12px;">
    <p style="margin:0;">Everlight Ventures &bull; everlightventures.io</p>
  </div>
</div>
</body>
</html>`;
}

async function postSlack(text: string): Promise<void> {
  const url = Deno.env.get("SLACK_WEBHOOK_URL");
  if (!url) return;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
  } catch (e) {
    console.error("Slack failed:", e);
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const resendKey = Deno.env.get("RESEND_API_KEY");
    if (!resendKey) {
      return new Response(
        JSON.stringify({ error: "RESEND_API_KEY not configured" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const {
      to,
      slug,
      download_url,
      type = "purchase",  // "purchase" or "recovery"
      bonus_slug,
      bonus_download_url,
    } = await req.json();

    if (!to || !slug || !download_url) {
      return new Response(
        JSON.stringify({ error: "Missing to, slug, or download_url" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const bookTitle = BOOK_TITLES[slug] ?? slug;
    let subject: string;
    let html: string;

    if (type === "recovery" && bonus_slug && bonus_download_url) {
      const bonusTitle = BOOK_TITLES[bonus_slug] ?? bonus_slug;
      subject = `Your Everlight Download + A Free Gift From Us`;
      html = buildRecoveryEmailHtml(bookTitle, download_url, bonusTitle, bonus_download_url);
    } else {
      subject = `Your Download is Ready: ${bookTitle}`;
      html = buildEmailHtml(bookTitle, download_url);
    }

    // Send via Resend API
    const resendResp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${resendKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "Everlight Ventures <noreply@everlightventures.io>",
        to: [to],
        subject,
        html,
        reply_to: "support@everlightventures.io",
      }),
    });

    const resendData = await resendResp.json();

    if (!resendResp.ok) {
      console.error("Resend error:", resendData);
      await postSlack(`EMAIL FAILED to ${to} for "${slug}": ${JSON.stringify(resendData)}`);
      return new Response(
        JSON.stringify({ error: "Email send failed", details: resendData }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    await postSlack(
      type === "recovery"
        ? `Recovery email sent to ${to} for "${slug}" + free "${bonus_slug}"`
        : `Purchase confirmation sent to ${to} for "${slug}"`
    );

    return new Response(
      JSON.stringify({ success: true, email_id: resendData.id }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("send-purchase-email error:", err);
    return new Response(
      JSON.stringify({ error: err.message ?? "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
