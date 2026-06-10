import "server-only";
import { promises as fs } from "fs";
import path from "path";
import type {
  Lead,
  Buyer,
  TitleCompany,
  StateTitleEntry,
  DealEvent,
  KPIs,
} from "./types";

const WORKSPACE = process.env.WORKSPACE_ROOT ?? "/mnt/sdcard/AA_MY_DRIVE";
const WHOLESALE = path.join(
  WORKSPACE,
  "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"
);

const LEADS_DB = path.join(WHOLESALE, "leads_db.json");
const BUYERS_DB = path.join(WHOLESALE, "buyers_db.json");
const TITLES_JSON = path.join(WHOLESALE, "title_companies.json");
const EVENTS_JSONL = path.join(WORKSPACE, "_logs/dispatcher/events.jsonl");
const THREAD_CURSOR = path.join(WORKSPACE, "_logs/deal_thread_cursor.json");

// -----------------------------------------------------------------------------
// Per-call cache (within a single server render). Next.js will de-dupe imports.
// -----------------------------------------------------------------------------

async function readJsonSafe<T>(p: string, fallback: T): Promise<T> {
  try {
    const raw = await fs.readFile(p, "utf8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export async function loadLeads(): Promise<Lead[]> {
  return readJsonSafe<Lead[]>(LEADS_DB, []);
}

export async function loadBuyers(): Promise<Buyer[]> {
  return readJsonSafe<Buyer[]>(BUYERS_DB, []);
}

export async function loadTitleCompanies(): Promise<
  Record<string, StateTitleEntry | TitleCompany[]>
> {
  return readJsonSafe(TITLES_JSON, {});
}

export async function loadDealEvents(): Promise<DealEvent[]> {
  try {
    const raw = await fs.readFile(EVENTS_JSONL, "utf8");
    return raw
      .trim()
      .split("\n")
      .filter(Boolean)
      .map((ln) => {
        try {
          return JSON.parse(ln) as DealEvent;
        } catch {
          return null;
        }
      })
      .filter((x): x is DealEvent => x !== null);
  } catch {
    return [];
  }
}

export async function loadThreadCursor(): Promise<
  Record<string, { thread_ts?: string; status?: string }>
> {
  const raw = await readJsonSafe<{ leads?: Record<string, { thread_ts?: string; status?: string }> }>(
    THREAD_CURSOR,
    { leads: {} }
  );
  return raw.leads ?? {};
}

// -----------------------------------------------------------------------------
// Derived views
// -----------------------------------------------------------------------------

const INST_TOKENS = [
  "LLC",
  "TRUST",
  "INC",
  "CORP",
  " LP",
  "BANK",
  "AUTHORITY",
  "DIOCESE",
  "DEVELOPMENT",
  "ASSOCIATION",
  "REALTY",
  "HOLDINGS",
  "PARTNERS",
  "INVESTMENTS",
  "PROPERTIES",
];

export function isIndividual(lead: Lead): boolean {
  const nm = (lead.owner_name ?? "").toUpperCase();
  return !INST_TOKENS.some((t) => nm.includes(t));
}

export function hasContact(lead: Lead): boolean {
  return Boolean(
    lead.email ??
      lead.owner_email ??
      lead.phone ??
      lead.owner_phone
  );
}

export function contactMethod(lead: Lead): "email" | "phone" | "both" | "none" {
  const e = Boolean(lead.email ?? lead.owner_email);
  const p = Boolean(lead.phone ?? lead.owner_phone);
  if (e && p) return "both";
  if (e) return "email";
  if (p) return "phone";
  return "none";
}

export function leadARV(lead: Lead): number {
  const raw = lead.estimated_arv ?? lead.arv ?? 0;
  const n = typeof raw === "string" ? parseFloat(raw) : raw;
  return Number.isFinite(n) ? n : 0;
}

export function offerRange(lead: Lead): { low: number; high: number; mid: number } {
  const arv = leadARV(lead);
  const repair = Math.round((arv * 0.15) / 100) * 100;
  const high = Math.max(0, Math.round((arv * 0.75 - repair) / 100) * 100);
  const low = Math.max(0, Math.round((arv * 0.65 - repair) / 100) * 100);
  return { low, high, mid: Math.round((low + high) / 2) };
}

export function distressReason(lead: Lead): string {
  const d = (lead.detected_distress ?? lead.lead_type ?? "").toLowerCase();
  const REASONS: Record<string, string> = {
    pre_foreclosure: "Pre-foreclosure notice filed - owner may need a fast, clean exit.",
    preforeclosure: "Pre-foreclosure notice filed - owner may need a fast, clean exit.",
    pf: "Pre-foreclosure notice filed - owner may need a fast, clean exit.",
    high_equity: "High equity + long hold - cash buyer angle + principal-only offer.",
    fsbo: "Selling themselves, no agent - open to a direct cash offer without commissions.",
    fsbo_zillow: "Actively listed FSBO on Zillow - motivated seller, no MLS middleman.",
    fsbo_craigslist: "Listed on Craigslist - unconventional seller, fast-close preference.",
    tax_delinquent: "Back taxes overdue - seller may want a clean exit before the lien escalates.",
    probate: "Inherited property. Heirs often sell for cash to avoid holding costs.",
    expired_listing: "Could not sell with an agent - open to a direct cash offer.",
    absentee: "Owner lives out of state - may want to unload a remote property.",
    code_violation: "Municipal code issues piling up - cash as-is saves them fines.",
    generic: "General distressed-signal lead. Cash, speed, as-is.",
    attom_snapshot: "Pulled from ATTOM assessment snapshot. High-value filter match.",
    attom_scal: "ATTOM pre-screened high-equity lead.",
    oz_distress_hunt: "Opportunity Zone distressed property. Investor-friendly market.",
  };
  return REASONS[d] ?? `Lead type: ${d || "generic"}.`;
}

export function strategyLane(lead: Lead): string {
  const d = (lead.detected_distress ?? lead.lead_type ?? "").toLowerCase();
  if (d.includes("foreclosure") || d === "pf")
    return "Pre-foreclosure fast-close";
  if (d.includes("fsbo")) return "FSBO direct-to-seller";
  if (d.includes("probate")) return "Probate / estate";
  if (d.includes("absentee")) return "Absentee owner outreach";
  if (d.includes("tax")) return "Tax-delinquent cleanup";
  if (d.includes("code")) return "Code-violation as-is";
  if (d.includes("high_equity") || d.includes("scal")) return "High-equity long-hold";
  if (d.includes("oz")) return "Opportunity Zone investor";
  return "General distressed-cash offer";
}

// -----------------------------------------------------------------------------
// Title companies helper
// -----------------------------------------------------------------------------

export function titleCompaniesForState(
  db: Record<string, StateTitleEntry | TitleCompany[]>,
  state: string
): TitleCompany[] {
  const entry = db[state.toUpperCase()];
  if (!entry) return [];
  const list = Array.isArray(entry) ? entry : entry.companies ?? [];
  return [...list].sort(
    (a, b) =>
      Number(Boolean(b.primary)) - Number(Boolean(a.primary)) ||
      (a.rank ?? 999) - (b.rank ?? 999)
  );
}

// -----------------------------------------------------------------------------
// KPIs
// -----------------------------------------------------------------------------

export async function computeKPIs(): Promise<KPIs> {
  const [leads, events] = await Promise.all([loadLeads(), loadDealEvents()]);
  const now = Date.now();
  const day = 24 * 60 * 60 * 1000;

  const kpis: KPIs = {
    total: leads.length,
    contactable: 0,
    in_sequence: 0,
    replied: 0,
    closed: 0,
    by_state: {},
    clicks_24h: 0,
    new_today: 0,
  };

  for (const l of leads) {
    const st = (l.state ?? "??").toUpperCase();
    kpis.by_state[st] ??= { total: 0, contactable: 0, in_seq: 0, replied: 0 };
    kpis.by_state[st].total++;

    if (isIndividual(l) && hasContact(l)) {
      kpis.contactable++;
      kpis.by_state[st].contactable++;
    }
    if (l.status === "contacted" || l.status === "negotiating") {
      kpis.in_sequence++;
      kpis.by_state[st].in_seq++;
    }
    if (l.reply_received) {
      kpis.replied++;
      kpis.by_state[st].replied++;
    }
    if (l.status === "closed" || l.status === "funds_received") {
      kpis.closed++;
    }
    if (l.created_at) {
      try {
        const t = new Date(l.created_at).getTime();
        if (now - t < day) kpis.new_today++;
      } catch {}
    }
  }

  // 24h click counter
  const cutoff = now - day;
  for (const ev of events) {
    if (ev.type !== "magnet_click") continue;
    try {
      const t = new Date(ev.ts).getTime();
      if (t >= cutoff) kpis.clicks_24h++;
    } catch {}
  }

  return kpis;
}
