/**
 * Wholesale data layer.
 * Reads compliance, contracts, buyers, legal docs from local files on Oracle.
 * Server-only.
 */
import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";

const WHOLESALE_ROOT  = process.env.WHOLESALE_ROOT  ?? "/home/opc/wholesale";
const WHOLESALE_AGENT = process.env.WHOLESALE_AGENT ?? "/home/opc/wholesale_agent";
const COMPLIANCE_MD   = process.env.COMPLIANCE_MD   ?? "/home/opc/wholesale/compliance";

/* ─── Compliance / state gates ─────────────────────────────── */

export type StateGate = {
  name: string;
  wholesale_legal_status: string;
  active_in_pipeline: boolean;
  sms_allowed: boolean;
  cold_call_allowed: boolean;
  inbound_sms_allowed: boolean;
  preforeclosure_outreach_allowed: boolean;
  autonomous_bot_call_allowed_cold: boolean;
  autonomous_bot_call_reason?: string;
  state_dnc_list: boolean;
  solicitor_registration_required: boolean;
  solicitor_bond_usd: number;
  call_recording_consent: string;
  recording_disclosure_required: boolean;
  outbound_call_hours_local: {
    mon_sat_start: string;
    mon_sat_end: string;
    sun_allowed: boolean;
    sun_start?: string;
    sun_end?: string;
  };
  email_hours_restricted: boolean;
  foreclosure_consultant_statute: boolean;
  closing_type: string;
  preferred_closer_id?: string;
  required_seller_disclosure: string;
  required_buyer_disclosure?: string | null;
  foreign_llc_registration_required: boolean;
  assignment_contract_legal: boolean;
  unlicensed_appraisal_risk: string;
  arv_in_writing_to_seller_allowed: boolean;
  risk_rating: "low" | "medium" | "high";
  gate_notes?: string;
  sms_conditions?: string[];
  cold_call_conditions?: string[];
};

export async function getStateGates(): Promise<{
  meta: Record<string, unknown> | null;
  states: Record<string, StateGate>;
}> {
  try {
    const raw = await fs.readFile(path.join(WHOLESALE_ROOT, "compliance/state_gates.json"), "utf-8");
    const all = JSON.parse(raw) as Record<string, unknown>;
    const meta = (all._meta as Record<string, unknown>) ?? null;
    const states: Record<string, StateGate> = {};
    for (const [k, v] of Object.entries(all)) {
      if (k.startsWith("_")) continue;
      states[k] = v as StateGate;
    }
    return { meta, states };
  } catch {
    return { meta: null, states: {} };
  }
}

/* ─── Compliance markdown library ─────────────────────────── */

export type ComplianceDoc = {
  slug: string;
  title: string;
  content: string;
  preview: string;
  size: number;
  updated: string | null;
};

const COMPLIANCE_TITLES: Record<string, string> = {
  API_KEY_ROTATION_POLICY:    "API Key Rotation Policy",
  BRAND_POSITIONING:          "Brand Positioning",
  BUSINESS_ENTITY_STATUS:     "Business Entity Status",
  CHANNEL_STRATEGY:           "Channel Strategy",
  DATA_ENCRYPTION_ATTESTATION:"Data Encryption Attestation",
  DISASTER_RECOVERY_RUNBOOK:  "Disaster Recovery Runbook",
  DISCLOSURE_TEMPLATES:       "Disclosure Templates",
  MFA_SETUP_GUIDE:            "MFA Setup Guide",
  STATE_COMPLIANCE_MATRIX:    "State Compliance Matrix",
};

export async function getComplianceDocs(): Promise<ComplianceDoc[]> {
  try {
    const names = (await fs.readdir(COMPLIANCE_MD)).filter((n) => n.endsWith(".md"));
    const docs = await Promise.all(names.map(async (n) => {
      const full = path.join(COMPLIANCE_MD, n);
      const stat = await fs.stat(full);
      const raw = await fs.readFile(full, "utf-8");
      const parsed = matter(raw);
      const slug = n.replace(/\.md$/i, "");
      const title = (parsed.data.title as string)
        ?? COMPLIANCE_TITLES[slug]
        ?? parsed.content.match(/^#\s+(.+)$/m)?.[1]?.trim()
        ?? slug;
      const preview = parsed.content
        .replace(/^#.*$/gm, "")
        .replace(/\n+/g, " ")
        .trim()
        .slice(0, 200);
      return {
        slug,
        title,
        content: parsed.content,
        preview,
        size: stat.size,
        updated: stat.mtime.toISOString(),
      };
    }));
    return docs.sort((a, b) => a.title.localeCompare(b.title));
  } catch {
    return [];
  }
}

export async function getComplianceDoc(slug: string): Promise<ComplianceDoc | null> {
  const docs = await getComplianceDocs();
  return docs.find((d) => d.slug === slug) ?? null;
}

/* ─── Contracts library ────────────────────────────────────── */

export type Contract = {
  slug: string;
  title: string;
  content: string;
  size: number;
};

const CONTRACT_DIRS = [
  "/home/opc/wholesale_agent/contracts",
  "/home/opc/wholesale/contracts",
  "/home/opc/hive_action_engine/deal_packages",
];

export async function getContracts(): Promise<Contract[]> {
  const all: Contract[] = [];
  for (const dir of CONTRACT_DIRS) {
    try {
      const names = (await fs.readdir(dir)).filter((n) => n.endsWith(".md"));
      for (const n of names) {
        const full = path.join(dir, n);
        try {
          const raw = await fs.readFile(full, "utf-8");
          const stat = await fs.stat(full);
          const parsed = matter(raw);
          const slug = n.replace(/\.md$/i, "");
          if (all.some((c) => c.slug === slug)) continue; // dedup
          const title = (parsed.data.title as string)
            ?? parsed.content.match(/^#\s+(.+)$/m)?.[1]?.trim()
            ?? slug;
          all.push({ slug, title, content: parsed.content, size: stat.size });
        } catch { /* skip */ }
      }
    } catch { /* skip */ }
  }
  return all.sort((a, b) => a.title.localeCompare(b.title));
}

export async function getContract(slug: string): Promise<Contract | null> {
  const contracts = await getContracts();
  return contracts.find((c) => c.slug === slug) ?? null;
}

/* ─── Buyers list ──────────────────────────────────────────── */

export type Buyer = {
  name?: string;
  company: string;
  email?: string;
  phone?: string;
  city?: string;
  state?: string;
  buy_criteria?: string;
  added_date?: string;
  deals_sent?: number;
  deals_closed?: number;
  status?: string;
  outreach_count?: number;
  last_outreach?: string;
  responded?: boolean;
  on_deal_list?: boolean;
};

export async function getBuyers(): Promise<Buyer[]> {
  const candidates = [
    "/home/opc/wholesale_agent/buyers_db.json",
    "/home/opc/hive_action_engine/wholesale_agent/buyers_db.json",
  ];
  for (const p of candidates) {
    try {
      const raw = await fs.readFile(p, "utf-8");
      const data = JSON.parse(raw);
      if (Array.isArray(data)) return data as Buyer[];
    } catch { /* try next */ }
  }
  return [];
}

export type BuyerStats = {
  total: number;
  byState: Record<string, number>;
  byStatus: Record<string, number>;
  responded: number;
  onDealList: number;
  totalOutreach: number;
  topCities: Array<{ city: string; count: number }>;
};

export function computeBuyerStats(buyers: Buyer[]): BuyerStats {
  const byState: Record<string, number> = {};
  const byStatus: Record<string, number> = {};
  const cityMap: Record<string, number> = {};
  let responded = 0, onDealList = 0, totalOutreach = 0;
  for (const b of buyers) {
    if (b.state) byState[b.state] = (byState[b.state] ?? 0) + 1;
    if (b.status) byStatus[b.status] = (byStatus[b.status] ?? 0) + 1;
    if (b.city) cityMap[b.city] = (cityMap[b.city] ?? 0) + 1;
    if (b.responded) responded++;
    if (b.on_deal_list) onDealList++;
    if (typeof b.outreach_count === "number") totalOutreach += b.outreach_count;
  }
  const topCities = Object.entries(cityMap)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8)
    .map(([city, count]) => ({ city, count }));
  return { total: buyers.length, byState, byStatus, responded, onDealList, totalOutreach, topCities };
}

/* ─── Legal docs (Everlight Foundations) ──────────────────── */

const LEGAL_ROOT = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/legal";

export async function getLegalDocs(): Promise<ComplianceDoc[]> {
  try {
    const names = (await fs.readdir(LEGAL_ROOT)).filter((n) => n.endsWith(".md"));
    const docs = await Promise.all(names.map(async (n) => {
      const full = path.join(LEGAL_ROOT, n);
      const stat = await fs.stat(full);
      const raw = await fs.readFile(full, "utf-8");
      const parsed = matter(raw);
      const slug = n.replace(/\.md$/i, "");
      const title = (parsed.data.title as string)
        ?? parsed.content.match(/^#\s+(.+)$/m)?.[1]?.trim()
        ?? slug;
      const preview = parsed.content
        .replace(/^#.*$/gm, "")
        .replace(/\n+/g, " ")
        .trim()
        .slice(0, 200);
      return {
        slug,
        title,
        content: parsed.content,
        preview,
        size: stat.size,
        updated: stat.mtime.toISOString(),
      };
    }));
    return docs.sort((a, b) => a.title.localeCompare(b.title));
  } catch {
    return [];
  }
}
