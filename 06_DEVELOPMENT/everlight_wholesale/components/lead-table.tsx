"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Search, MapPin, ArrowUpRight, Mail, Phone, Eye, LayoutGrid, List,
  Zap, TrendingUp, AlertCircle, Clock, Flame, Sparkles,
} from "lucide-react";
import type { Lead } from "@/lib/types";
import { cn } from "@/lib/utils";
import { compactMoney, humanStatus, statusColor, timeAgo } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { StateTabs, type StateFilter } from "@/components/state-tabs";

type ArvBand = "ALL" | "0-100k" | "100-250k" | "250-500k" | "500k+";
type ViewMode = "cards" | "compact";

// Deterministic gold-ish avatar color per owner name
function avatarGradient(name: string): string {
  const palettes = [
    "linear-gradient(135deg,#D4A843 0%,#8E6F1C 100%)",
    "linear-gradient(135deg,#EAD08B 0%,#9A7F33 100%)",
    "linear-gradient(135deg,#B38F2F 0%,#5A4218 100%)",
    "linear-gradient(135deg,#E8B947 0%,#7D5E13 100%)",
    "linear-gradient(135deg,#C49438 0%,#3D2F0E 100%)",
  ];
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return palettes[h % palettes.length];
}

function initials(name: string): string {
  return (name || "?")
    .replace(/,/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(s => s[0]?.toUpperCase() ?? "")
    .join("");
}

function TouchRing({ n, total = 7 }: { n: number; total?: number }) {
  const pct = Math.min(1, (n || 0) / total);
  const r = 14;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative flex-none w-10 h-10 flex items-center justify-center">
      <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90">
        <circle cx="18" cy="18" r={r} fill="none" stroke="#222" strokeWidth="3" />
        <circle
          cx="18" cy="18" r={r}
          fill="none"
          stroke="url(#goldring)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
        />
        <defs>
          <linearGradient id="goldring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#EAD08B" />
            <stop offset="100%" stopColor="#D4A843" />
          </linearGradient>
        </defs>
      </svg>
      <span className="text-[10px] font-mono tabular-nums text-gold relative">
        {n}<span className="text-smoke">/{total}</span>
      </span>
    </div>
  );
}

function LeadCard({ lead }: { lead: Lead }) {
  const name = (lead.owner_name || "Unknown").replace(/\s+/g, " ").trim();
  const arv = Number(lead.estimated_arv ?? lead.arv ?? 0);
  const hasEmail = Boolean(lead.email ?? lead.owner_email);
  const hasPhone = Boolean(lead.phone ?? lead.owner_phone);
  const isHot =
    (lead.status === "negotiating" || lead.status === "verbal_agreement") ||
    (lead.detected_distress && /foreclosure|tax|probate/i.test(String(lead.detected_distress)));

  return (
    <Link href={`/leads/${lead.id}`} className="group block">
      <div
        className="relative overflow-hidden rounded-2xl bg-card-gradient border border-ash hover:border-gold/50 hover:-translate-y-0.5 transition-all duration-200 p-4 h-full"
      >
        {/* subtle gold edge on hover */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gold/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

        <div className="flex items-start gap-3">
          {/* Avatar */}
          <div
            className="flex-none w-11 h-11 rounded-xl flex items-center justify-center font-display text-obsidian text-sm font-semibold shadow-md relative"
            style={{ background: avatarGradient(name) }}
          >
            {initials(name) || "?"}
            {isHot && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-obsidian border border-gold rounded-full flex items-center justify-center animate-pulse-gold">
                <Flame className="w-2.5 h-2.5 text-gold" />
              </span>
            )}
          </div>

          {/* Main info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="font-medium text-ivory truncate">{name}</div>
                <div className="text-[11px] text-smoke flex items-center gap-1 mt-0.5">
                  <MapPin className="w-3 h-3 flex-none" />
                  <span className="truncate">{lead.address}</span>
                </div>
              </div>
              <StatusBadge status={lead.status as string} />
            </div>

            <div className="flex items-center gap-3 text-[11px] mt-2">
              <span className="px-1.5 py-0.5 rounded bg-graphite border border-ash/60 font-mono text-fog">
                {(lead.state || "??").toUpperCase()}
              </span>
              <span className="text-gold font-mono tabular-nums">{compactMoney(arv)}</span>
              {(lead.detected_distress || lead.lead_type) && (
                <span className="text-[10px] text-fog/80 uppercase tracking-wider truncate max-w-[120px]">
                  {(lead.detected_distress || lead.lead_type || "").toString().replace(/_/g, " ")}
                </span>
              )}
            </div>
          </div>

          <TouchRing n={lead.outreach_count ?? 0} />
        </div>

        <div className="mt-3 pt-3 border-t border-ash/50 flex items-center justify-between gap-3 text-[11px]">
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "flex items-center gap-1",
                hasEmail ? "text-gold" : "text-smoke/60"
              )}
              title={hasEmail ? (lead.email ?? lead.owner_email ?? "") : "no email"}
            >
              <Mail className="w-3 h-3" />
            </span>
            <span
              className={cn(
                "flex items-center gap-1",
                hasPhone ? "text-gold" : "text-smoke/60"
              )}
              title={hasPhone ? (lead.phone ?? lead.owner_phone ?? "") : "no phone"}
            >
              <Phone className="w-3 h-3" />
            </span>
            <span className="text-smoke">
              <Clock className="w-3 h-3 inline mr-1" />
              {timeAgo(lead.last_outreach)}
            </span>
          </div>
          <span className="text-fog group-hover:text-gold transition-colors inline-flex items-center gap-1">
            Open <ArrowUpRight className="w-3 h-3" />
          </span>
        </div>
      </div>
    </Link>
  );
}


// ---------- Compact list row (spreadsheet-ish but prettier) ----------
function CompactRow({ lead }: { lead: Lead }) {
  const name = (lead.owner_name || "Unknown").replace(/\s+/g, " ").trim();
  const arv = Number(lead.estimated_arv ?? lead.arv ?? 0);
  const hasEmail = Boolean(lead.email ?? lead.owner_email);
  const hasPhone = Boolean(lead.phone ?? lead.owner_phone);
  return (
    <Link
      href={`/leads/${lead.id}`}
      className="group flex items-center gap-3 px-4 py-2.5 border-b border-ash/50 hover:bg-gold/5 transition-colors"
    >
      <div
        className="flex-none w-8 h-8 rounded-lg flex items-center justify-center font-display text-obsidian text-[11px] font-semibold"
        style={{ background: avatarGradient(name) }}
      >
        {initials(name)}
      </div>
      <div className="flex-1 min-w-0 grid grid-cols-12 gap-3 items-center">
        <div className="col-span-4 min-w-0">
          <div className="text-[13px] text-ivory font-medium truncate">{name}</div>
          <div className="text-[11px] text-smoke truncate">{lead.address}</div>
        </div>
        <div className="col-span-1 text-[11px] font-mono text-fog">
          {(lead.state || "??").toUpperCase()}
        </div>
        <div className="col-span-2 text-[11px]">
          <StatusBadge status={lead.status as string} />
        </div>
        <div className="col-span-2 font-mono text-gold tabular-nums text-right">
          {compactMoney(arv)}
        </div>
        <div className="col-span-2 flex items-center gap-2">
          <TouchRing n={lead.outreach_count ?? 0} />
          <div className="flex gap-1">
            <Mail className={cn("w-3 h-3", hasEmail ? "text-gold" : "text-smoke/40")} />
            <Phone className={cn("w-3 h-3", hasPhone ? "text-gold" : "text-smoke/40")} />
          </div>
        </div>
        <div className="col-span-1 text-[11px] text-fog text-right">
          {timeAgo(lead.last_outreach)}
        </div>
      </div>
      <ArrowUpRight className="w-4 h-4 text-smoke group-hover:text-gold transition-colors flex-none" />
    </Link>
  );
}


export function LeadTable({ leads }: { leads: Lead[] }) {
  const [stateFilter, setStateFilter] = useState<StateFilter>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [arvBand, setArvBand] = useState<ArvBand>("ALL");
  const [contactableOnly, setContactableOnly] = useState<boolean>(false);
  const [globalFilter, setGlobalFilter] = useState("");
  const [pageSize, setPageSize] = useState<number>(24);
  const [pageIndex, setPageIndex] = useState<number>(0);
  const [view, setView] = useState<ViewMode>("cards");
  const [sortKey, setSortKey] = useState<"arv" | "recent" | "touches" | "owner">("arv");

  const filteredLeads = useMemo(() => {
    return leads.filter((l) => {
      if (stateFilter !== "ALL" && (l.state || "").toUpperCase() !== stateFilter) return false;
      if (contactableOnly && !(l.email || l.owner_email || l.phone || l.owner_phone)) return false;
      if (statusFilter !== "ALL" && l.status !== statusFilter) return false;
      const arv = Number(l.estimated_arv || l.arv || 0);
      if (arvBand === "0-100k"   && !(arv > 0 && arv < 100_000))    return false;
      if (arvBand === "100-250k" && !(arv >= 100_000 && arv < 250_000)) return false;
      if (arvBand === "250-500k" && !(arv >= 250_000 && arv < 500_000)) return false;
      if (arvBand === "500k+"    && !(arv >= 500_000))               return false;
      if (globalFilter) {
        const v = globalFilter.toLowerCase();
        const hit = [
          l.owner_name, l.address, l.city, l.email, l.owner_email,
          l.phone, l.owner_phone, l.id
        ].some((x) => String(x ?? "").toLowerCase().includes(v));
        if (!hit) return false;
      }
      return true;
    });
  }, [leads, stateFilter, statusFilter, arvBand, contactableOnly, globalFilter]);

  const sortedLeads = useMemo(() => {
    const copy = [...filteredLeads];
    copy.sort((a, b) => {
      switch (sortKey) {
        case "arv":
          return Number(b.estimated_arv ?? b.arv ?? 0) - Number(a.estimated_arv ?? a.arv ?? 0);
        case "recent": {
          const ta = new Date(a.last_outreach ?? a.created_at ?? 0).getTime();
          const tb = new Date(b.last_outreach ?? b.created_at ?? 0).getTime();
          return tb - ta;
        }
        case "touches":
          return (b.outreach_count ?? 0) - (a.outreach_count ?? 0);
        case "owner":
          return String(a.owner_name ?? "").localeCompare(String(b.owner_name ?? ""));
      }
    });
    return copy;
  }, [filteredLeads, sortKey]);

  // Reset page on filter change
  useEffect(() => {
    setPageIndex(0);
  }, [stateFilter, statusFilter, arvBand, contactableOnly, globalFilter, sortKey]);

  const totalPages = Math.max(1, Math.ceil(sortedLeads.length / pageSize));
  const pageStart = pageIndex * pageSize;
  const pageLeads = sortedLeads.slice(pageStart, pageStart + pageSize);

  const stateCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const l of leads) {
      const st = (l.state || "").toUpperCase();
      counts[st] = (counts[st] ?? 0) + 1;
    }
    return counts;
  }, [leads]);

  const STATUSES = [
    "ALL", "new", "contacted", "negotiating", "verbal_agreement",
    "contract_sent", "signed", "closed", "dead"
  ];

  return (
    <div className="space-y-5">
      {/* Top bar: state + view mode */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <StateTabs value={stateFilter} onChange={setStateFilter} counts={stateCounts} />
        <div className="inline-flex items-center p-1 bg-charcoal border border-ash rounded-lg">
          <button
            onClick={() => setView("cards")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] tracking-wider uppercase transition-colors",
              view === "cards"
                ? "bg-gold text-obsidian shadow-gold-glow"
                : "text-fog hover:text-gold"
            )}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            cards
          </button>
          <button
            onClick={() => setView("compact")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] tracking-wider uppercase transition-colors",
              view === "compact"
                ? "bg-gold text-obsidian shadow-gold-glow"
                : "text-fog hover:text-gold"
            )}
          >
            <List className="w-3.5 h-3.5" />
            compact
          </button>
        </div>
      </div>

      {/* Search + sort */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[260px] max-w-xl">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-smoke" />
          <input
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search owner, address, city, email, phone..."
            className="w-full pl-10 pr-10 py-2.5 bg-charcoal border border-ash rounded-lg text-ivory text-sm placeholder:text-smoke focus:border-gold/60 focus:outline-none focus:shadow-gold-glow transition-all"
          />
          {globalFilter && (
            <button
              onClick={() => setGlobalFilter("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-smoke hover:text-gold"
            >
              <span className="text-lg leading-none">&times;</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-1 text-[11px]">
          <span className="text-smoke mr-1 tracking-widest uppercase">sort</span>
          {([
            { k: "arv",     label: "ARV",     Icon: TrendingUp },
            { k: "recent",  label: "recent",  Icon: Clock },
            { k: "touches", label: "touches", Icon: Zap },
            { k: "owner",   label: "owner",   Icon: Sparkles },
          ] as const).map(({ k, label, Icon }) => (
            <button
              key={k}
              onClick={() => setSortKey(k)}
              className={cn(
                "inline-flex items-center gap-1 px-2.5 py-1.5 rounded border text-[11px]",
                sortKey === k
                  ? "bg-gold/20 text-gold border-gold/50"
                  : "bg-charcoal text-fog border-ash hover:border-gold/40 hover:text-gold"
              )}
            >
              <Icon className="w-3 h-3" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Status + ARV chips */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] tracking-[0.25em] text-fog uppercase mr-1">status</span>
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "px-3 py-1.5 rounded-md text-[11px] uppercase tracking-wider border whitespace-nowrap transition-colors",
                statusFilter === s
                  ? "bg-gold text-obsidian border-gold"
                  : "bg-charcoal border-ash text-fog hover:text-gold hover:border-gold/50"
              )}
            >
              {s === "ALL" ? "all" : humanStatus(s)}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] tracking-[0.25em] text-fog uppercase mr-1">ARV band</span>
          {(["ALL","0-100k","100-250k","250-500k","500k+"] as ArvBand[]).map((b) => (
            <button
              key={b}
              onClick={() => setArvBand(b)}
              className={cn(
                "px-3 py-1 rounded-md text-[11px] tracking-wider border",
                arvBand === b
                  ? "bg-gold/20 text-gold border-gold/50"
                  : "bg-charcoal border-ash text-fog hover:text-gold hover:border-gold/50"
              )}
            >
              {b === "ALL" ? "any" : b}
            </button>
          ))}
          <label className="flex items-center gap-2 ml-2 text-[11px] text-fog cursor-pointer select-none">
            <input
              type="checkbox"
              checked={contactableOnly}
              onChange={(e) => setContactableOnly(e.target.checked)}
              className="accent-gold"
            />
            <span>contactable only</span>
          </label>
        </div>
      </div>

      {/* Results stats bar */}
      <div className="flex items-center justify-between text-[11px] text-fog">
        <div>
          <span className="font-mono text-gold tabular-nums">{sortedLeads.length}</span>
          {" of "}
          <span className="font-mono text-ivory tabular-nums">{leads.length}</span>
          {" leads"}
          {sortedLeads.length !== leads.length && (
            <button
              onClick={() => {
                setStateFilter("ALL");
                setStatusFilter("ALL");
                setArvBand("ALL");
                setContactableOnly(false);
                setGlobalFilter("");
              }}
              className="ml-3 text-gold/80 hover:text-gold"
            >
              clear filters
            </button>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-smoke">rows:</span>
          {[12, 24, 48, 96, 9999].map((n) => (
            <button
              key={n}
              onClick={() => setPageSize(n)}
              className={cn(
                "px-2 py-0.5 rounded border tabular-nums font-mono",
                pageSize === n
                  ? "bg-gold/20 text-gold border-gold/50"
                  : "border-ash text-fog hover:border-gold/40"
              )}
            >
              {n >= 999 ? "all" : n}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {pageLeads.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-ash rounded-2xl">
          <AlertCircle className="w-6 h-6 text-smoke mx-auto mb-2" />
          <div className="text-sm text-fog">No leads match those filters.</div>
        </div>
      ) : view === "cards" ? (
        // SSR-safe: cards are immediately visible. No opacity:0 initial state.
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {pageLeads.map((l) => (
            <LeadCard key={l.id} lead={l} />
          ))}
        </div>
      ) : (
        <div className="border border-ash rounded-2xl overflow-hidden bg-card-gradient">
          <div className="px-4 py-2 border-b border-ash bg-graphite/40 grid grid-cols-12 gap-3 text-[10px] tracking-[0.25em] text-fog uppercase">
            <div className="col-span-4 pl-11">Owner / property</div>
            <div className="col-span-1">State</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-2 text-right">ARV</div>
            <div className="col-span-2">Touches</div>
            <div className="col-span-1 text-right">Last</div>
          </div>
          <div>
            {pageLeads.map((l) => <CompactRow key={l.id} lead={l} />)}
          </div>
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between text-[11px]">
        <div className="text-fog">
          page{" "}
          <span className="text-gold font-mono tabular-nums">{pageIndex + 1}</span>
          {" / "}
          <span className="text-ivory font-mono tabular-nums">{totalPages}</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPageIndex(0)}
            disabled={pageIndex === 0}
            className="px-3 py-1.5 bg-charcoal border border-ash rounded hover:border-gold/50 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &laquo;
          </button>
          <button
            onClick={() => setPageIndex((i) => Math.max(0, i - 1))}
            disabled={pageIndex === 0}
            className="px-3 py-1.5 bg-charcoal border border-ash rounded hover:border-gold/50 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            prev
          </button>
          <button
            onClick={() => setPageIndex((i) => Math.min(totalPages - 1, i + 1))}
            disabled={pageIndex >= totalPages - 1}
            className="px-3 py-1.5 bg-charcoal border border-ash rounded hover:border-gold/50 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            next
          </button>
          <button
            onClick={() => setPageIndex(totalPages - 1)}
            disabled={pageIndex >= totalPages - 1}
            className="px-3 py-1.5 bg-charcoal border border-ash rounded hover:border-gold/50 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &raquo;
          </button>
        </div>
      </div>
    </div>
  );
}
