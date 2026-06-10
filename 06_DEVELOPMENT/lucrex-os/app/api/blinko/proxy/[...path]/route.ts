/**
 * Blinko RAG proxy. Forwards /api/blinko/proxy/* to Blinko on :1111.
 */
import { NextResponse } from "next/server";

const BLINKO_BASE = process.env.BLINKO_BASE ?? "http://127.0.0.1:1111";

export const dynamic = "force-dynamic";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = new URL(req.url);
  const upstream = `${BLINKO_BASE}/${path.join("/")}${url.search}`;
  try {
    const r = await fetch(upstream, { cache: "no-store" });
    const body = await r.text();
    return new NextResponse(body, {
      status: r.status,
      headers: { "Content-Type": r.headers.get("content-type") ?? "application/json" },
    });
  } catch (e) {
    return NextResponse.json({ error: "blinko unreachable", upstream, message: e instanceof Error ? e.message : "?" }, { status: 502 });
  }
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const upstream = `${BLINKO_BASE}/${path.join("/")}`;
  const body = await req.text();
  try {
    const r = await fetch(upstream, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      cache: "no-store",
    });
    const respBody = await r.text();
    return new NextResponse(respBody, {
      status: r.status,
      headers: { "Content-Type": r.headers.get("content-type") ?? "application/json" },
    });
  } catch (e) {
    return NextResponse.json({ error: "blinko unreachable", upstream, message: e instanceof Error ? e.message : "?" }, { status: 502 });
  }
}
