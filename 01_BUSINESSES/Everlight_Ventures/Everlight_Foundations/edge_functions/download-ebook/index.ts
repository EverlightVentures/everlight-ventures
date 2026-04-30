// download-ebook: Token-gated download with 3-download limit
// Called from success page / email links instead of raw signed URLs
// Validates token, checks expiry + download count, returns fresh 1-hour signed URL

import { corsHeaders, handleCors, json, createSupabaseAdmin, postSlack, EBOOK_FILE_MAP } from "../_shared/mod.ts";

Deno.serve(async (req: Request) => {
  const corsResp = handleCors(req);
  if (corsResp) return corsResp;

  try {
    const supabase = createSupabaseAdmin();

    // Accept token from body (POST) or query param (GET link from email)
    let token: string | null = null;

    if (req.method === "GET") {
      const url = new URL(req.url);
      token = url.searchParams.get("token");
    } else {
      const body = await req.json();
      token = body.token;
    }

    if (!token) {
      return json({ error: "Missing download token" }, 400);
    }

    // Look up token
    const { data: tokenRow, error: tokenErr } = await supabase
      .from("download_tokens")
      .select("*")
      .eq("token", token)
      .maybeSingle();

    if (tokenErr || !tokenRow) {
      return json({ error: "Invalid download token" }, 404);
    }

    // Check expiry
    if (new Date(tokenRow.expires_at) < new Date()) {
      return json({
        error: "Download token has expired",
        expired: true,
        help: "Reply to your purchase email or contact support@everlightventures.io for a new link.",
      }, 410);
    }

    // Check download count
    const maxDownloads = tokenRow.max_downloads ?? 3;
    const currentCount = tokenRow.download_count ?? 0;

    if (currentCount >= maxDownloads) {
      return json({
        error: "Download limit reached",
        downloads_used: currentCount,
        max_downloads: maxDownloads,
        help: "You have used all your downloads. Contact support@everlightventures.io if you need help.",
      }, 429);
    }

    // Valid token -- generate fresh short-lived signed URL (1 hour)
    const slug = tokenRow.slug;
    const filePath = EBOOK_FILE_MAP[slug];

    if (!filePath) {
      return json({ error: "Invalid product slug on token" }, 400);
    }

    const { data: signedData, error: signedErr } = await supabase.storage
      .from("Ebooks")
      .createSignedUrl(filePath, 3600); // 1 hour

    if (signedErr || !signedData?.signedUrl) {
      console.error("Signed URL error:", signedErr);
      return json({ error: "Failed to generate download link" }, 500);
    }

    // Increment download count
    await supabase
      .from("download_tokens")
      .update({
        download_count: currentCount + 1,
        used: true,
      })
      .eq("token", token);

    // Slack notification
    postSlack(`Download #${currentCount + 1}/${maxDownloads} for "${slug}" (token: ${token.slice(0, 8)}...)`).catch((e) => console.error("Slack download notification failed:", e));

    return json({
      success: true,
      download_url: signedData.signedUrl,
      downloads_used: currentCount + 1,
      downloads_remaining: maxDownloads - currentCount - 1,
      expires_in: "1 hour",
    });
  } catch (err: unknown) {
    console.error("download-ebook error:", err);
    return json({ error: (err as Error).message ?? "Internal server error" }, 500);
  }
});
