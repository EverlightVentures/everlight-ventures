import { supabase } from "./supabase";
import type { BookInput, JobResult } from "./types";

const FUNCTIONS_URL = process.env.NEXT_PUBLIC_FUNCTIONS_URL!;

async function getAuthHeader(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error("Not authenticated");
  }
  return { Authorization: `Bearer ${session.access_token}` };
}

export async function createJob(
  input: BookInput,
  tier: "free" | "paid"
): Promise<{ job_id: string }> {
  const headers = await getAuthHeader();
  const res = await fetch(`${FUNCTIONS_URL}/coverforge-create-job`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ input, tier }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`createJob failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function jobStatus(jobId: string): Promise<JobResult> {
  const headers = await getAuthHeader();
  const res = await fetch(
    `${FUNCTIONS_URL}/coverforge-job-status?job_id=${encodeURIComponent(jobId)}`,
    { headers }
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`jobStatus failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function startCheckout(slug: string): Promise<void> {
  const headers = await getAuthHeader();
  const res = await fetch(`${FUNCTIONS_URL}/create-checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify({ slug, product_type: "cover_credits" }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`startCheckout failed (${res.status}): ${text}`);
  }
  const { url } = await res.json();
  window.location.href = url;
}

export async function getCreditBalance(): Promise<number> {
  try {
    const { data, error } = await supabase.rpc("cover_credit_balance");
    if (error) return 0;
    return (data as number) ?? 0;
  } catch {
    return 0;
  }
}
