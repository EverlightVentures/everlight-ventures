import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

// Self-contained (no _shared import) so it deploys cleanly via the Supabase MCP.
const SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const MAX_VARIATIONS = 4; // mirrors render/pricing.py
const TIERS = ["free", "paid"];

function svcKey(): string {
  return (Deno.env.get("SB_SERVICE_ROLE_KEY") || Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")) as string;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  const json = (b: unknown, s = 200) =>
    new Response(JSON.stringify(b), { status: s, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  try {
    const admin = createClient(SUPABASE_URL, svcKey());
    const jwt = req.headers.get("Authorization")?.replace("Bearer ", "");
    const { data: { user } } = await admin.auth.getUser(jwt ?? "");
    if (!user) return json({ error: "unauthorized" }, 401);

    const body = await req.json();
    const tier = body?.tier;
    const input = body?.input ?? {};
    if (!TIERS.includes(tier)) return json({ error: "bad tier" }, 400);
    input.variations = Math.min(Math.max(Number(input.variations ?? 1), 1), MAX_VARIATIONS);

    if (tier === "paid") {
      const { data: bal } = await admin.rpc("cover_credit_balance", { uid: user.id });
      if ((bal ?? 0) < 1) return json({ error: "no_credits" }, 402);
      await admin.from("credit_ledger").insert({ user_id: user.id, delta: -1, reason: "debit" });
    }
    const { data: job, error } = await admin.from("cover_jobs")
      .insert({ user_id: user.id, tier, input, status: "queued" }).select("id").single();
    if (error) return json({ error: error.message }, 500);
    return json({ job_id: job.id });
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
});
