"use client";

type BootstrapPayload = {
  access_token: string;
  email: string;
  password: string;
  api_base_url: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_HIVE_API_URL || "http://127.0.0.1:8000";
let cachedBootstrap: BootstrapPayload | null = null;

async function getBootstrap(): Promise<BootstrapPayload> {
  if (cachedBootstrap) {
    return cachedBootstrap;
  }
  const response = await fetch(`${API_BASE_URL}/api/bootstrap`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Hive API bootstrap endpoint is unavailable");
  }
  cachedBootstrap = await response.json();
  return cachedBootstrap;
}

export async function hiveRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const bootstrap = await getBootstrap();
  const headers = new Headers(init.headers || {});
  headers.set("Authorization", `Bearer ${bootstrap.access_token}`);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function listIntegrations() {
  return hiveRequest<any[]>("/api/integrations/");
}

export async function connectIntegration(payload: Record<string, unknown>) {
  return hiveRequest<any>("/api/integrations/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function startHiveSession(prompt: string, agents: string[]) {
  return hiveRequest<any>("/api/sessions/", {
    method: "POST",
    body: JSON.stringify({ prompt, agents, mode: "full" }),
  });
}

export async function getHiveSession(sessionId: string) {
  return hiveRequest<any>(`/api/sessions/${sessionId}`);
}

export async function getDashboardSnapshot() {
  const [tenant, usage, sessions, integrations] = await Promise.all([
    hiveRequest<any>("/api/tenants/me"),
    hiveRequest<any>("/api/billing/usage"),
    hiveRequest<any>("/api/sessions?limit=6"),
    hiveRequest<any[]>("/api/integrations/"),
  ]);

  return { tenant, usage, sessions, integrations };
}
