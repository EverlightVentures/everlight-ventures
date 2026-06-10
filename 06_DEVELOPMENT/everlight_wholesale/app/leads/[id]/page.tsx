import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, MapPin, Mail, Phone, Home, DollarSign, Target, Building2, ExternalLink, Clock } from "lucide-react";
import {
  loadLeads, loadTitleCompanies, loadDealEvents, loadThreadCursor, loadBuyers,
  titleCompaniesForState, offerRange, distressReason, strategyLane,
  leadARV, contactMethod,
} from "@/lib/data";
import { money, compactMoney, timeAgo, humanStatus } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { ConversationTimeline } from "@/components/conversation-timeline";
import { MatchedBuyers } from "@/components/matched-buyers";
import { Breadcrumbs } from "@/components/breadcrumbs";

export const dynamic = "force-dynamic";

export default async function LeadDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [leads, titles, events, threads, buyers] = await Promise.all([
    loadLeads(), loadTitleCompanies(), loadDealEvents(), loadThreadCursor(), loadBuyers(),
  ]);

  const lead = leads.find((l) => String(l.id ?? "") === id);
  if (!lead) notFound();

  const stateTitles = titleCompaniesForState(titles, lead.state || "");
  const offer = offerRange(lead);
  const reason = distressReason(lead);
  const lane = strategyLane(lead);
  const leadEvents = events
    .filter((ev) => {
      const p: any = ev.payload || {};
      return (p.lead_id && p.lead_id === id) ||
             (p.record && p.record.id === id);
    })
    .sort((a, b) => (a.ts < b.ts ? 1 : -1))
    .slice(0, 30);

  const threadInfo = threads[id];
  const contactMeth = contactMethod(lead);
  const arv = leadARV(lead);

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[
        { label: "Leads", href: "/" },
        { label: (lead.owner_name || "Lead").replace(/\s+/g, " ").trim() },
      ]} />
      <Link href="/" className="inline-flex items-center gap-2 text-sm text-fog hover:text-gold transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Back to dashboard
      </Link>

      <header className="flex items-start justify-between gap-6 flex-wrap">
        <div>
          <div className="text-[11px] tracking-[0.3em] text-gold/80 uppercase">Lead file</div>
          <h1 className="font-display text-3xl md:text-4xl text-ivory mt-2 tracking-tight">
            {(lead.owner_name || "Unknown Owner").replace(/\s+/g, " ").trim()}
          </h1>
          <div className="flex items-center gap-2 mt-2 text-fog">
            <MapPin className="w-4 h-4" />
            <span>{lead.address}, {lead.city}, {lead.state} {lead.zip ?? ""}</span>
          </div>
          <div className="flex items-center gap-3 mt-3">
            <StatusBadge status={lead.status as string} />
            <span className="text-[11px] text-smoke">
              lead_id <code className="text-fog">{lead.id}</code>
            </span>
            {lead.source && (
              <span className="text-[11px] text-smoke">source <code className="text-fog">{lead.source}</code></span>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Strategy lane</div>
          <div className="font-display text-2xl text-gold mt-1">{lane}</div>
          <p className="text-[12px] text-fog mt-1 max-w-sm">{reason}</p>
        </div>
      </header>

      <div className="divider-gold" />

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Property + offer math */}
        <div className="lg:col-span-2 bg-card-gradient border border-ash rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Property + offer math</div>
              <h3 className="font-display text-xl text-ivory mt-1">The numbers</h3>
            </div>
            {lead.listing_url && (
              <a href={lead.listing_url} target="_blank" rel="noreferrer"
                className="text-[11px] text-gold/80 hover:text-gold inline-flex items-center gap-1">
                Listing <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Metric label="ARV"           value={arv ? money(arv) : "--"} />
            <Metric label="Repair est"    value={arv ? money(Math.round(arv * 0.15 / 100) * 100) : "--"} />
            <Metric label="Offer low"     value={money(offer.low)} />
            <Metric label="Offer high"    value={money(offer.high)} accent />
            <Metric label="Beds / Baths"  value={`${lead.beds ?? "?"} / ${lead.baths ?? "?"}`} sub="rooms" />
            <Metric label="Sq Ft"         value={lead.sqft ? String(lead.sqft) : "--"} />
            <Metric label="Year built"    value={lead.year_built ? String(lead.year_built) : "--"} />
            <Metric label="Last sale"     value={lead.last_sale_price ? money(lead.last_sale_price) : "--"}
                    sub={lead.last_sale_date ? String(lead.last_sale_date).slice(0, 10) : ""} />
          </div>

          <div className="pt-4 border-t border-ash/60">
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase mb-2">Why this lead</div>
            <p className="text-sm text-ivory leading-relaxed">{reason}</p>
          </div>
        </div>

        {/* Contact + status */}
        <aside className="bg-card-gradient border border-ash rounded-xl p-5">
          <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Owner contact</div>
          <h3 className="font-display text-xl text-ivory mt-1 mb-4">Reach path</h3>

          <div className="space-y-3">
            <ContactRow
              Icon={Mail} label="Email"
              value={lead.email || lead.owner_email || ""}
              placeholder="no email (run skip-trace)"
              active={contactMeth === "email" || contactMeth === "both"}
            />
            <ContactRow
              Icon={Phone} label="Phone"
              value={lead.phone || lead.owner_phone || ""}
              placeholder="no phone (run skip-trace)"
              active={contactMeth === "phone" || contactMeth === "both"}
            />
          </div>

          <div className="mt-6 pt-4 border-t border-ash/60">
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Outreach progress</div>
            <div className="mt-2 flex items-center gap-1.5">
              {Array.from({ length: 7 }).map((_, i) => (
                <span key={i}
                  className={`h-2 flex-1 rounded-full ${i < (lead.outreach_count ?? 0) ? "bg-gold" : "bg-ash"}`} />
              ))}
            </div>
            <div className="flex justify-between text-[11px] text-fog mt-2">
              <span>{lead.outreach_count ?? 0} / 7 touches</span>
              <span>last: {timeAgo(lead.last_outreach)}</span>
            </div>
          </div>

          {threadInfo?.thread_ts && (
            <div className="mt-4 pt-4 border-t border-ash/60">
              <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Slack thread</div>
              <a
                href={`https://app.slack.com/client/T08JZUBNHL1/C0ANLLV8JAC/thread/C0ANLLV8JAC-${threadInfo.thread_ts}`}
                target="_blank" rel="noreferrer"
                className="mt-2 inline-flex items-center gap-2 text-gold hover:underline text-sm"
              >
                Open thread in Slack <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}
        </aside>
      </div>

      {/* Title companies */}
      <section className="bg-card-gradient border border-ash rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Title companies ({lead.state})</div>
            <h3 className="font-display text-xl text-ivory mt-1">
              {lead.assigned_title_company
                ? `Assigned: ${lead.assigned_title_company}`
                : "Ranked fallback chain"}
            </h3>
          </div>
          <Link href="/title-companies" className="text-[11px] text-gold/80 hover:text-gold">
            see all
          </Link>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {stateTitles.slice(0, 6).map((tc, i) => (
            <div key={tc.id ?? `${tc.name}-${i}`}
              className={`border rounded-lg p-4 ${tc.primary
                ? "border-gold/40 bg-gold/5" : "border-ash bg-graphite/40"}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-[10px] tracking-[0.25em] text-fog uppercase">
                    #{tc.rank} {tc.primary ? " -- primary" : ""}
                  </div>
                  <div className="font-medium text-ivory mt-1">{tc.name}</div>
                </div>
                <Building2 className={tc.primary ? "w-4 h-4 text-gold" : "w-4 h-4 text-smoke"} />
              </div>
              {tc.phone && <div className="text-[12px] text-fog mt-2">{tc.phone}</div>}
              {tc.website && (
                <a href={tc.website} target="_blank" rel="noreferrer"
                  className="text-[11px] text-gold/80 hover:text-gold inline-flex items-center gap-1 mt-1">
                  site <ExternalLink className="w-3 h-3" />
                </a>
              )}
              {tc.notes && (
                <p className="text-[11px] text-smoke mt-2 leading-relaxed line-clamp-2">{tc.notes}</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Matched buyers -- who do we blast this to if Rich signs */}
      <section>
        <div className="flex items-end justify-between mb-4 flex-wrap gap-2">
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Assignment-ready buyers</div>
            <h3 className="font-display text-2xl text-ivory mt-1">
              Who gets this deal if we close
            </h3>
            <p className="text-[11px] text-smoke mt-1">
              Ranked by state match, market fit, price-band compatibility, and response history.
            </p>
          </div>
          <Link href="/buyers" className="text-[11px] text-gold/80 hover:text-gold whitespace-nowrap">
            full buyer book &rarr;
          </Link>
        </div>
        <MatchedBuyers lead={lead} buyers={buyers} />
      </section>

      {/* Conversation history -- WHO said WHAT WHEN with branded HTML preview */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">Outreach history</div>
            <h3 className="font-display text-2xl text-ivory mt-1">Every email, every reply</h3>
            <p className="text-[11px] text-smoke mt-1">
              Click any row to unfold the exact branded email we delivered.
            </p>
          </div>
          <span className="text-[11px] text-smoke">
            {(lead.conversation ?? []).length} messages
          </span>
        </div>
        <ConversationTimeline lead={lead} />
      </section>

      {/* Dispatcher events (magnet clicks, status transitions) */}
      <section className="bg-card-gradient border border-ash rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[10px] tracking-[0.3em] text-fog uppercase">System events</div>
            <h3 className="font-display text-xl text-ivory mt-1">Magnet clicks + status transitions</h3>
          </div>
          <span className="text-[11px] text-smoke">{leadEvents.length} events</span>
        </div>

        {leadEvents.length === 0 ? (
          <div className="text-sm text-fog py-8 text-center border-t border-ash/60">
            No magnet clicks or dispatcher events for this lead yet.
          </div>
        ) : (
          <ol className="space-y-2">
            {leadEvents.map((ev) => (
              <li key={ev.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-graphite/40">
                <EventIcon type={ev.type} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-ivory">{humanEvent(ev.type)}</div>
                  {(ev.payload as any)?.magnet && (
                    <div className="text-[11px] text-smoke">{(ev.payload as any).magnet}</div>
                  )}
                </div>
                <div className="text-[11px] text-fog font-mono">
                  <Clock className="inline w-3 h-3 mr-1 text-smoke" />
                  {timeAgo(ev.ts)}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-[10px] tracking-[0.2em] text-fog uppercase">{label}</div>
      <div className={`font-display text-xl mt-1 ${accent ? "text-gold" : "text-ivory"}`}>{value}</div>
      {sub && <div className="text-[11px] text-smoke">{sub}</div>}
    </div>
  );
}

function ContactRow({
  Icon, label, value, placeholder, active,
}: { Icon: any; label: string; value: string; placeholder: string; active: boolean }) {
  return (
    <div className={`flex items-center gap-3 p-2.5 rounded-lg border ${active ? "border-gold/30 bg-gold/5" : "border-ash"}`}>
      <Icon className={`w-4 h-4 ${active ? "text-gold" : "text-smoke"}`} />
      <div className="flex-1 min-w-0">
        <div className="text-[10px] tracking-[0.2em] text-fog uppercase">{label}</div>
        <div className={`text-sm truncate ${active ? "text-ivory" : "text-smoke italic"}`}>
          {value || placeholder}
        </div>
      </div>
    </div>
  );
}

function EventIcon({ type }: { type: string }) {
  const map: Record<string, { cls: string; ch: string }> = {
    wholesale_lead_new:       { cls: "bg-gold/20 text-gold",      ch: "N" },
    wholesale_reply:          { cls: "bg-success/20 text-success", ch: "R" },
    magnet_click:             { cls: "bg-fog/20 text-ivory",      ch: "*" },
    magnet_accept:            { cls: "bg-success/30 text-success",ch: "A" },
    magnet_counter:           { cls: "bg-warning/20 text-warning",ch: "?" },
    magnet_call:              { cls: "bg-gold/30 text-gold",      ch: "C" },
    magnet_not_interested:    { cls: "bg-ash text-smoke",         ch: "-" },
    stripe_charge:            { cls: "bg-gold text-obsidian",     ch: "$" },
  };
  const m = map[type] ?? { cls: "bg-ash text-smoke", ch: "-" };
  return (
    <span className={`flex-none w-7 h-7 rounded-full flex items-center justify-center font-mono text-sm ${m.cls}`}>
      {m.ch}
    </span>
  );
}

function humanEvent(t: string): string {
  return ({
    wholesale_lead_new:    "New lead ingested",
    wholesale_reply:       "Seller replied",
    magnet_click:          "Seller clicked CashOfferScan",
    magnet_accept:         "Seller ACCEPTED offer",
    magnet_counter:        "Seller countered",
    magnet_call:           "Seller requested a call",
    magnet_not_interested: "Seller passed",
    stripe_charge:         "Stripe payment received",
  } as Record<string, string>)[t] ?? t;
}
