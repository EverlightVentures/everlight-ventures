/**
 * Shared utilities for all Supabase edge functions.
 * Import from "../_shared/mod.ts" in each function.
 */

import Stripe from "https://esm.sh/stripe@14.21.0?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

// --- Supabase ---

// Platform-aware: the edge runtime injects SUPABASE_URL for whichever project the
// function is deployed to (AK project mfghdobptredxxhbjwyz vs casino jdqqmsmwmbsnlnstyavl).
// Hardcoded fallback kept for local tooling only. AUTH_SEPARATION_DOCTRINE.md applies.
export const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "https://jdqqmsmwmbsnlnstyavl.supabase.co";

export function createSupabaseAdmin() {
  return createClient(
    SUPABASE_URL,
    Deno.env.get("SB_SERVICE_ROLE_KEY")!
  );
}

// --- Stripe ---

export function createStripeClient() {
  return new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
    apiVersion: "2023-10-16",
    httpClient: Stripe.createFetchHttpClient(),
  });
}

// --- CORS ---

export const corsHeaders: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, stripe-signature",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

export function handleCors(req: Request): Response | null {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  return null;
}

// --- JSON Response ---

export function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

// --- Slack ---

export async function postSlack(text: string, webhookUrl?: string): Promise<void> {
  const url = webhookUrl ?? Deno.env.get("SLACK_WEBHOOK_URL");
  if (!url) return;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
  } catch (err: unknown) {
    console.error("Slack notification failed:", err);
  }
}

// --- Ebook File Map ---

export const EBOOK_FILE_MAP: Record<string, string> = {
  "sam-book-1": "sam-book-1/Sams_First_Superpower.zip",
  "sam-book-2": "sam-book-2/Sams_Second_Superpower.zip",
  "sam-book-3": "sam-book-3/Sams_Third_Superpower.zip",
  "sam-book-4": "sam-book-4/Sams_Fourth_Superpower.zip",
  "sam-book-5": "sam-book-5/Sams_Fifth_Superpower.zip",
  "sam-bundle": "sam-bundle/Sam_And_Robo_Complete.zip",
  "beyond-the-veil": "beyond-the-veil/Beyond_The_Veil.zip",
};
