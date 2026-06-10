import { NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";

const WEALTH_ROOT = process.env.WEALTH_OS_ROOT
  ?? "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wealth_OS";

const PRIORITIES_PATH = path.join(WEALTH_ROOT, "PRIORITIES.md");

const VALID_KEYS = new Set([
  "TAX_MINIMIZATION", "LIQUIDITY", "ASSET_PROTECTION", "GROWTH_LEVERAGE",
  "GEOGRAPHIC_FREEDOM", "PRIVACY", "GENERATIONAL", "SPEED_OF_DEPLOY",
  "COMPLEXITY_TOLERANCE", "ETHICS_FLOOR",
]);

export async function POST(req: Request) {
  let body: { weights?: Record<string, number> };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const weights = body.weights;
  if (!weights || typeof weights !== "object") {
    return NextResponse.json({ error: "Missing weights" }, { status: 400 });
  }

  for (const [k, v] of Object.entries(weights)) {
    if (!VALID_KEYS.has(k)) {
      return NextResponse.json({ error: `Unknown key: ${k}` }, { status: 400 });
    }
    if (typeof v !== "number" || v < 0 || v > 10) {
      return NextResponse.json({ error: `Invalid value for ${k}: ${v}` }, { status: 400 });
    }
  }

  let content: string;
  try {
    content = await fs.readFile(PRIORITIES_PATH, "utf-8");
  } catch (e) {
    return NextResponse.json(
      { error: `Cannot read PRIORITIES.md at ${PRIORITIES_PATH}` },
      { status: 500 }
    );
  }

  for (const [k, v] of Object.entries(weights)) {
    const re = new RegExp(`(${k}:\\s*)(\\[\\?\\]|\\d{1,2})(\\s*)`, "g");
    const padded = String(v).padStart(2, " ");
    content = content.replace(re, `$1${padded.trim()}$3`);
  }

  try {
    await fs.writeFile(PRIORITIES_PATH, content, "utf-8");
  } catch (e) {
    return NextResponse.json(
      { error: `Cannot write to PRIORITIES.md: ${e instanceof Error ? e.message : "unknown"}` },
      { status: 500 }
    );
  }

  return NextResponse.json({ ok: true, weights });
}
