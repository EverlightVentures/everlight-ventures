import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

function svcKey(): string {
  return (Deno.env.get("SB_SERVICE_ROLE_KEY") || Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")) as string;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  const j = (b: unknown, s = 200) =>
    new Response(JSON.stringify(b), { status: s, headers: { ...corsHeaders, "Content-Type": "application/json" } });
  const admin = createClient(SUPABASE_URL, svcKey());
  const jwt = req.headers.get("Authorization")?.replace("Bearer ", "");
  const { data: { user } } = await admin.auth.getUser(jwt ?? "");
  if (!user) return j({ error: "unauthorized" }, 401);

  const id = new URL(req.url).searchParams.get("job_id");
  const { data: job } = await admin.from("cover_jobs").select("*").eq("id", id).eq("user_id", user.id).maybeSingle();
  if (!job) return j({ error: "not_found" }, 404);

  const signed: Record<string, string> = {};
  if (job.status === "done" && job.tier === "paid" && job.outputs) {
    for (const [k, v] of Object.entries(job.outputs)) {
      if (typeof v === "string" && v.startsWith("covers/")) {
        const { data } = await admin.storage.from("covers").createSignedUrl(v.replace("covers/", ""), 3600);
        if (data) signed[k] = data.signedUrl;
      }
    }
  }
  return j({ status: job.status, tier: job.tier, outputs: job.outputs, signed, error: job.error });
});
