/**
 * Django ops proxy. Forwards /api/django/proxy/* to Django on :8504.
 * Path is forwarded verbatim (Django mounts at /taskboard/, /hive/, /reports/, etc).
 * Read-only (GET) for now. Mutations go through the Django web UI.
 */
import { NextResponse } from "next/server";

const DJANGO_BASE = process.env.DJANGO_API_BASE ?? "http://127.0.0.1:8504";
const DJANGO_TOKEN = process.env.DJANGO_API_TOKEN;

export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(req.url);
  const upstream = `${DJANGO_BASE}/${path.join("/")}${url.search}`;
  try {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (DJANGO_TOKEN) headers.Authorization = `Token ${DJANGO_TOKEN}`;
    const r = await fetch(upstream, { cache: "no-store", headers });
    const body = await r.text();
    return new NextResponse(body, {
      status: r.status,
      headers: { "Content-Type": r.headers.get("content-type") ?? "application/json" },
    });
  } catch (e) {
    return NextResponse.json(
      { error: "django unreachable", upstream, message: e instanceof Error ? e.message : "?" },
      { status: 502 }
    );
  }
}
