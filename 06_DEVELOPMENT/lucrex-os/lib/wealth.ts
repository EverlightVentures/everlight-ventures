/**
 * Wealth OS data layer: reads markdown directly from the Wealth_OS folder.
 * Server-only.
 */
import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";

const WEALTH_ROOT = process.env.WEALTH_OS_ROOT
  ?? "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wealth_OS";

export type WealthDoc = {
  slug: string;
  filename: string;
  title: string;
  content: string;
  frontmatter: Record<string, unknown>;
};

async function readDoc(absPath: string): Promise<WealthDoc | null> {
  try {
    const raw = await fs.readFile(absPath, "utf-8");
    const parsed = matter(raw);
    const filename = path.basename(absPath);
    const slug = filename.replace(/\.md$/i, "");
    const titleFromContent = parsed.content.match(/^#\s+(.+)$/m)?.[1]?.trim();
    const title =
      (parsed.data.title as string) ?? titleFromContent ?? slug;
    return {
      slug,
      filename,
      title,
      content: parsed.content,
      frontmatter: parsed.data,
    };
  } catch {
    return null;
  }
}

export async function readWealthRoot(filename: string): Promise<WealthDoc | null> {
  return readDoc(path.join(WEALTH_ROOT, filename));
}

export async function listWealthFolder(folder: string): Promise<WealthDoc[]> {
  const dir = path.join(WEALTH_ROOT, folder);
  let names: string[] = [];
  try {
    names = await fs.readdir(dir);
  } catch {
    return [];
  }
  const md = names.filter((n) => n.endsWith(".md")).sort();
  const docs = await Promise.all(md.map((n) => readDoc(path.join(dir, n))));
  return docs.filter((d): d is WealthDoc => d !== null);
}

export async function getLayers() {
  return listWealthFolder("01_Layers");
}

export async function getTiers() {
  return listWealthFolder("02_Tiers");
}

export async function getEngines() {
  return listWealthFolder("03_Engines");
}

export async function getDispatchLog() {
  return listWealthFolder("04_Dispatch_Log");
}

export async function getProfessionals() {
  return listWealthFolder("05_Professionals");
}

export async function getScenarios() {
  return listWealthFolder("06_Scenarios");
}

/**
 * Parse PRIORITIES.md and extract weights. Returns null if any weight is still `[?]`.
 */
export async function getPriorities() {
  const doc = await readWealthRoot("PRIORITIES.md");
  if (!doc) return { doc: null, weights: null };

  const KEYS = [
    "TAX_MINIMIZATION", "LIQUIDITY", "ASSET_PROTECTION", "GROWTH_LEVERAGE",
    "GEOGRAPHIC_FREEDOM", "PRIVACY", "GENERATIONAL", "SPEED_OF_DEPLOY",
    "COMPLEXITY_TOLERANCE", "ETHICS_FLOOR",
  ] as const;

  const weights: Record<string, number> = {};
  let allFilled = true;

  for (const k of KEYS) {
    const re = new RegExp(`${k}:\\s*(\\[\\?\\]|\\d{1,2})`);
    const m = doc.content.match(re);
    if (!m || m[1] === "[?]") {
      allFilled = false;
      weights[k] = 0;
    } else {
      const n = Number(m[1]);
      weights[k] = Number.isFinite(n) ? Math.min(10, Math.max(0, n)) : 0;
    }
  }

  return {
    doc,
    weights: allFilled ? (weights as unknown as import("@/components/RadarPriorities").PriorityWeights) : null,
    rawWeights: weights,
    allFilled,
  };
}

/**
 * Determine current tier based on a net worth in dollars.
 * Returns the tier slug (T00..T11) and gate threshold.
 */
const TIER_GATES: Array<{ tier: string; minNetWorth: number; label: string }> = [
  { tier: "T00", minNetWorth: 0,         label: "Foundation" },
  { tier: "T01", minNetWorth: 10_000,    label: "First LLC" },
  { tier: "T02", minNetWorth: 50_000,    label: "Systems" },
  { tier: "T03", minNetWorth: 100_000,   label: "S-Corp + R&D" },
  { tier: "T04", minNetWorth: 250_000,   label: "Holdco + IP" },
  { tier: "T05", minNetWorth: 500_000,   label: "DAPT + SBLOC" },
  { tier: "T06", minNetWorth: 1_000_000, label: "ILIT + GRAT" },
  { tier: "T07", minNetWorth: 2_500_000, label: "SLAT + Dynasty" },
  { tier: "T08", minNetWorth: 5_000_000, label: "Family Office" },
  { tier: "T09", minNetWorth: 10_000_000,label: "PPLI + PR Act 60" },
  { tier: "T10", minNetWorth: 25_000_000,label: "Direct Deals" },
  { tier: "T11", minNetWorth: 100_000_000,label: "Foundation" },
];

export function tierForNetWorth(netWorth: number) {
  let active = TIER_GATES[0];
  for (const t of TIER_GATES) {
    if (netWorth >= t.minNetWorth) active = t;
  }
  const idx = TIER_GATES.findIndex((t) => t.tier === active.tier);
  const next = TIER_GATES[idx + 1] ?? null;
  return {
    current: active,
    next,
    progress: next
      ? (netWorth - active.minNetWorth) / (next.minNetWorth - active.minNetWorth)
      : 1,
    allTiers: TIER_GATES,
  };
}
