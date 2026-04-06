// =============================================================================
// Everlight Field Ops -- REST API Edge Function
// Endpoint: /field-ops-api
// =============================================================================

import { serve } from "https://deno.land/std@0.208.0/http/server.ts";
import { createClient, SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2.39.3";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ApiKeyRecord {
  id: string;
  user_id: string;
  tier: string;
  monthly_limit: number;
  usage_count: number;
  usage_reset_at: string;
  active: boolean;
}

interface RouteMatch {
  handler: (req: Request, params: Record<string, string>, db: SupabaseClient, apiKey?: ApiKeyRecord) => Promise<Response>;
  params: Record<string, string>;
}

// ---------------------------------------------------------------------------
// CORS & Response Helpers
// ---------------------------------------------------------------------------

const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key",
  "Access-Control-Max-Age": "86400",
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json" },
  });
}

function error(message: string, status = 400): Response {
  return json({ error: message }, status);
}

// ---------------------------------------------------------------------------
// Supabase Client (service role for full access)
// ---------------------------------------------------------------------------

function getDb(): SupabaseClient {
  const url = Deno.env.get("SUPABASE_URL")!;
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  return createClient(url, key);
}

// ---------------------------------------------------------------------------
// API Key Validation Middleware
// ---------------------------------------------------------------------------

async function validateApiKey(req: Request, db: SupabaseClient): Promise<ApiKeyRecord | null> {
  const apiKey = req.headers.get("X-API-Key");
  if (!apiKey) return null;

  // Hash the key the same way it was stored (SHA-256 hex)
  const encoder = new TextEncoder();
  const hashBuffer = await crypto.subtle.digest("SHA-256", encoder.encode(apiKey));
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const keyHash = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");

  const { data, error: dbErr } = await db
    .from("field_ops_api_keys")
    .select("*")
    .eq("key_hash", keyHash)
    .eq("active", true)
    .single();

  if (dbErr || !data) return null;

  const record = data as ApiKeyRecord;

  // Check if usage reset is needed
  if (new Date(record.usage_reset_at) < new Date()) {
    await db
      .from("field_ops_api_keys")
      .update({ usage_count: 0, usage_reset_at: new Date(Date.now() + 30 * 86400000).toISOString() })
      .eq("id", record.id);
    record.usage_count = 0;
  }

  // Check rate limit
  if (record.usage_count >= record.monthly_limit) return null;

  // Increment usage
  await db
    .from("field_ops_api_keys")
    .update({ usage_count: record.usage_count + 1 })
    .eq("id", record.id);

  return record;
}

// ---------------------------------------------------------------------------
// Route: GET /workers?lat=X&lng=Y&radius=Z&skill=S
// ---------------------------------------------------------------------------

async function searchWorkers(req: Request, _params: Record<string, string>, db: SupabaseClient): Promise<Response> {
  const url = new URL(req.url);
  const lat = parseFloat(url.searchParams.get("lat") || "");
  const lng = parseFloat(url.searchParams.get("lng") || "");
  const radius = parseInt(url.searchParams.get("radius") || "25", 10);
  const skill = url.searchParams.get("skill") || null;

  if (isNaN(lat) || isNaN(lng)) {
    return error("lat and lng query params are required");
  }

  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    return error("lat must be -90..90, lng must be -180..180");
  }

  const { data, error: dbErr } = await db.rpc("search_workers_nearby", {
    lat,
    lng,
    radius_miles: Math.min(radius, 200),
    skill_filter: skill,
  });

  if (dbErr) return error(dbErr.message, 500);
  return json({ workers: data, count: (data as unknown[]).length });
}

// ---------------------------------------------------------------------------
// Route: GET /workers/:id
// ---------------------------------------------------------------------------

async function getWorker(_req: Request, params: Record<string, string>, db: SupabaseClient): Promise<Response> {
  const { data, error: dbErr } = await db
    .from("field_ops_workers")
    .select("id, full_name, bio, skills, city, state, hourly_rate, per_task_rate, verified, verification_tier, rating, total_tasks_completed, profile_photo_url, created_at")
    .eq("id", params.id)
    .single();

  if (dbErr) return error("Worker not found", 404);
  return json({ worker: data });
}

// ---------------------------------------------------------------------------
// Route: POST /tasks (requires API key)
// ---------------------------------------------------------------------------

async function createTask(req: Request, _params: Record<string, string>, db: SupabaseClient, apiKey?: ApiKeyRecord): Promise<Response> {
  if (!apiKey) return error("Valid API key required in X-API-Key header", 401);

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return error("Invalid JSON body");
  }

  const required = ["title", "description", "category", "budget"];
  for (const field of required) {
    if (!body[field]) return error(`Missing required field: ${field}`);
  }

  const validCategories = [
    "retail_audit", "property_check", "delivery", "photography",
    "errand", "verification", "logistics", "other",
  ];
  if (!validCategories.includes(body.category as string)) {
    return error(`Invalid category. Must be one of: ${validCategories.join(", ")}`);
  }

  const budget = parseFloat(body.budget as string);
  if (isNaN(budget) || budget <= 0) return error("Budget must be a positive number");

  // Build location if lat/lng provided
  let location = null;
  if (body.lat && body.lng) {
    const lat = parseFloat(body.lat as string);
    const lng = parseFloat(body.lng as string);
    if (!isNaN(lat) && !isNaN(lng)) {
      location = `SRID=4326;POINT(${lng} ${lat})`;
    }
  }

  const insert: Record<string, unknown> = {
    posted_by: apiKey.user_id,
    posted_by_type: "api",
    title: body.title,
    description: body.description,
    category: body.category,
    budget,
    location,
    address: body.address || null,
    city: body.city || null,
    state: body.state || null,
    radius_miles: body.radius_miles ? parseInt(body.radius_miles as string, 10) : 10,
    proof_required: body.proof_required || ["photo"],
    deadline: body.deadline || null,
    metadata: body.metadata || {},
  };

  const { data, error: dbErr } = await db
    .from("field_ops_tasks")
    .insert(insert)
    .select()
    .single();

  if (dbErr) return error(dbErr.message, 500);
  return json({ task: data }, 201);
}

// ---------------------------------------------------------------------------
// Route: GET /tasks/:id
// ---------------------------------------------------------------------------

async function getTask(_req: Request, params: Record<string, string>, db: SupabaseClient): Promise<Response> {
  const { data, error: dbErr } = await db
    .from("field_ops_tasks")
    .select("*")
    .eq("id", params.id)
    .single();

  if (dbErr) return error("Task not found", 404);
  return json({ task: data });
}

// ---------------------------------------------------------------------------
// Route: POST /bookings
// ---------------------------------------------------------------------------

async function createBooking(req: Request, _params: Record<string, string>, db: SupabaseClient, apiKey?: ApiKeyRecord): Promise<Response> {
  if (!apiKey) return error("Valid API key required in X-API-Key header", 401);

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return error("Invalid JSON body");
  }

  if (!body.task_id || !body.worker_id) {
    return error("task_id and worker_id are required");
  }

  // Verify the task exists and is open
  const { data: task, error: taskErr } = await db
    .from("field_ops_tasks")
    .select("id, status, posted_by")
    .eq("id", body.task_id)
    .single();

  if (taskErr || !task) return error("Task not found", 404);
  if (task.status !== "open") return error("Task is not open for booking");

  // Verify the worker exists and is available
  const { data: worker, error: workerErr } = await db
    .from("field_ops_workers")
    .select("id, available")
    .eq("id", body.worker_id)
    .single();

  if (workerErr || !worker) return error("Worker not found", 404);
  if (!worker.available) return error("Worker is not currently available");

  // Check no existing active booking for this task
  const { data: existing } = await db
    .from("field_ops_bookings")
    .select("id")
    .eq("task_id", body.task_id)
    .not("status", "in", '("cancelled")')
    .limit(1);

  if (existing && existing.length > 0) {
    return error("Task already has an active booking");
  }

  const { data, error: dbErr } = await db
    .from("field_ops_bookings")
    .insert({
      task_id: body.task_id,
      worker_id: body.worker_id,
      payout_amount: body.payout_amount || null,
      platform_fee: body.platform_fee || null,
    })
    .select()
    .single();

  if (dbErr) return error(dbErr.message, 500);

  // Update task status to matched
  await db
    .from("field_ops_tasks")
    .update({ status: "matched" })
    .eq("id", body.task_id);

  return json({ booking: data }, 201);
}

// ---------------------------------------------------------------------------
// Route: GET /bookings/:id
// ---------------------------------------------------------------------------

async function getBooking(_req: Request, params: Record<string, string>, db: SupabaseClient): Promise<Response> {
  const { data, error: dbErr } = await db
    .from("field_ops_bookings")
    .select(`
      *,
      task:field_ops_tasks(id, title, category, city, state, budget, status),
      worker:field_ops_workers(id, full_name, rating, verification_tier)
    `)
    .eq("id", params.id)
    .single();

  if (dbErr) return error("Booking not found", 404);
  return json({ booking: data });
}

// ---------------------------------------------------------------------------
// Route: PATCH /bookings/:id
// ---------------------------------------------------------------------------

async function updateBooking(req: Request, params: Record<string, string>, db: SupabaseClient, apiKey?: ApiKeyRecord): Promise<Response> {
  if (!apiKey) return error("Valid API key required in X-API-Key header", 401);

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return error("Invalid JSON body");
  }

  // Only allow updating specific fields
  const allowedFields = ["status", "proof_urls", "proof_notes", "proof_validated", "proof_validated_by", "started_at", "completed_at"];
  const updates: Record<string, unknown> = {};

  for (const field of allowedFields) {
    if (body[field] !== undefined) {
      updates[field] = body[field];
    }
  }

  if (Object.keys(updates).length === 0) {
    return error("No valid fields to update");
  }

  // Validate status transitions
  if (updates.status) {
    const validStatuses = ["pending", "accepted", "in_progress", "proof_submitted", "completed", "disputed", "cancelled"];
    if (!validStatuses.includes(updates.status as string)) {
      return error(`Invalid status. Must be one of: ${validStatuses.join(", ")}`);
    }

    // Auto-set timestamps
    if (updates.status === "in_progress" && !updates.started_at) {
      updates.started_at = new Date().toISOString();
    }
    if (updates.status === "completed" && !updates.completed_at) {
      updates.completed_at = new Date().toISOString();
    }
  }

  const { data, error: dbErr } = await db
    .from("field_ops_bookings")
    .update(updates)
    .eq("id", params.id)
    .select()
    .single();

  if (dbErr) return error(dbErr.message, 500);

  // Sync task status if booking status changed
  if (updates.status && data) {
    const taskStatusMap: Record<string, string> = {
      accepted: "matched",
      in_progress: "in_progress",
      proof_submitted: "proof_submitted",
      completed: "completed",
      disputed: "disputed",
      cancelled: "open",
    };
    const newTaskStatus = taskStatusMap[updates.status as string];
    if (newTaskStatus) {
      await db
        .from("field_ops_tasks")
        .update({ status: newTaskStatus })
        .eq("id", (data as Record<string, unknown>).task_id);
    }
  }

  return json({ booking: data });
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

function matchRoute(method: string, pathname: string): RouteMatch | null {
  // Strip the function prefix -- Supabase calls as /field-ops-api/...
  const path = pathname.replace(/^\/field-ops-api/, "") || "/";

  const routes: Array<{
    method: string;
    pattern: RegExp;
    handler: RouteMatch["handler"];
    paramNames: string[];
  }> = [
    { method: "GET", pattern: /^\/workers\/?$/, handler: searchWorkers, paramNames: [] },
    { method: "GET", pattern: /^\/workers\/([0-9a-f-]{36})\/?$/, handler: getWorker, paramNames: ["id"] },
    { method: "POST", pattern: /^\/tasks\/?$/, handler: createTask, paramNames: [] },
    { method: "GET", pattern: /^\/tasks\/([0-9a-f-]{36})\/?$/, handler: getTask, paramNames: ["id"] },
    { method: "POST", pattern: /^\/bookings\/?$/, handler: createBooking, paramNames: [] },
    { method: "GET", pattern: /^\/bookings\/([0-9a-f-]{36})\/?$/, handler: getBooking, paramNames: ["id"] },
    { method: "PATCH", pattern: /^\/bookings\/([0-9a-f-]{36})\/?$/, handler: updateBooking, paramNames: ["id"] },
  ];

  for (const route of routes) {
    if (route.method !== method) continue;
    const match = path.match(route.pattern);
    if (match) {
      const params: Record<string, string> = {};
      route.paramNames.forEach((name, i) => {
        params[name] = match[i + 1];
      });
      return { handler: route.handler, params };
    }
  }

  return null;
}

// ---------------------------------------------------------------------------
// Main Handler
// ---------------------------------------------------------------------------

serve(async (req: Request): Promise<Response> => {
  // CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: CORS_HEADERS });
  }

  const url = new URL(req.url);
  const route = matchRoute(req.method, url.pathname);

  if (!route) {
    return json({
      error: "Not found",
      endpoints: [
        "GET  /field-ops-api/workers?lat=X&lng=Y&radius=Z&skill=S",
        "GET  /field-ops-api/workers/:id",
        "POST /field-ops-api/tasks",
        "GET  /field-ops-api/tasks/:id",
        "POST /field-ops-api/bookings",
        "GET  /field-ops-api/bookings/:id",
        "PATCH /field-ops-api/bookings/:id",
      ],
    }, 404);
  }

  try {
    const db = getDb();

    // Validate API key for write operations
    let apiKey: ApiKeyRecord | undefined;
    if (["POST", "PATCH", "PUT", "DELETE"].includes(req.method)) {
      const key = await validateApiKey(req, db);
      if (!key) {
        return error("Valid API key required. Pass it in the X-API-Key header.", 401);
      }
      apiKey = key;
    } else {
      // Optional key validation for reads (for rate limiting)
      const key = await validateApiKey(req, db);
      if (key) apiKey = key;
    }

    return await route.handler(req, route.params, db, apiKey);
  } catch (err) {
    console.error("Field Ops API error:", err);
    return error("Internal server error", 500);
  }
});
