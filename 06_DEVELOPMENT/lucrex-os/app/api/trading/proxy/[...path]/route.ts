/**
 * Trading API proxy. Forwards /api/trading/proxy/* to the existing
 * xlm-dash FastAPI on :8502/api/* (which has all the rich endpoints
 * the React command center already uses).
 */
import { NextResponse } from "next/server";

const XLM_API_BASE = process.env.XLM_API_BASE ?? "http://127.0.0.1:8502";

export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(req.url);
  const upstream = `${XLM_API_BASE}/api/${path.join("/")}${url.search}`;
  try {
    const r = await fetch(upstream, { cache: "no-store" });
    const body = await r.text();
    return new NextResponse(body, {
      status: r.status,
      headers: { "Content-Type": r.headers.get("content-type") ?? "application/json" },
    });
  } catch (e) {
    return NextResponse.json(
      { error: "upstream unreachable", upstream, message: e instanceof Error ? e.message : "?" },
      { status: 502 }
    );
  }
}
