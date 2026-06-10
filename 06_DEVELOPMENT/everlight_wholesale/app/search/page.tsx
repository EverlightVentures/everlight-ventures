import Link from "next/link";
import { loadLeads, loadBuyers, loadTitleCompanies } from "@/lib/data";
import { compactMoney } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { Search as SearchIcon, MapPin, Mail, Phone, Building2 } from "lucide-react";
import { Breadcrumbs } from "@/components/breadcrumbs";

export const dynamic = "force-dynamic";

export default async function SearchPage({ searchParams }: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await searchParams;
  const query = q.trim().toLowerCase();

  const [leads, buyers, titlesDb] = await Promise.all([
    loadLeads(), loadBuyers(), loadTitleCompanies(),
  ]);

  // Flatten all title companies
  const titles: { state: string; rank: number; name: string; phone?: string; notes?: string; primary: boolean }[] = [];
  for (const [state, entry] of Object.entries(titlesDb)) {
    const list = Array.isArray(entry) ? entry : (entry.companies ?? []);
    for (const c of list) {
      titles.push({ state, rank: c.rank, name: c.name, phone: c.phone, notes: c.notes, primary: Boolean(c.primary) });
    }
  }

  const matchLead = (l: any) => {
    if (!query) return false;
    return [l.owner_name, l.address, l.city, l.email, l.owner_email, l.phone, l.owner_phone, l.id]
      .filter(Boolean).some((v: string) => String(v).toLowerCase().includes(query));
  };
  const matchBuyer = (b: any) => {
    if (!query) return false;
    return [b.name, b.company, b.email, b.phone, b.city, b.buy_criteria]
      .filter(Boolean).some((v: string) => String(v).toLowerCase().includes(query));
  };
  const matchTitle = (t: any) => {
    if (!query) return false;
    return [t.name, t.notes, t.state].filter(Boolean).some((v: string) => String(v).toLowerCase().includes(query));
  };

  const leadHits = query ? leads.filter(matchLead).slice(0, 20) : [];
  const buyerHits = query ? buyers.filter(matchBuyer).slice(0, 10) : [];
  const titleHits = query ? titles.filter(matchTitle).slice(0, 10) : [];

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Search" }]} />
      <header>
        <div className="text-[11px] tracking-[0.3em] text-gold/80 uppercase">Global search</div>
        <h1 className="font-display text-4xl text-ivory mt-2 tracking-tight">
          {query ? <>Results for <span className="text-gold">&quot;{query}&quot;</span></> : "Search"}
        </h1>
      </header>

      <form method="get" className="relative max-w-xl">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-smoke" />
        <input
          name="q"
          defaultValue={query}
          autoFocus
          placeholder="Search any lead, buyer, title company, address, phone..."
          className="w-full pl-11 pr-4 py-3 bg-charcoal border border-ash rounded-lg text-ivory placeholder:text-smoke focus:border-gold/60 focus:outline-none"
        />
      </form>

      {!query && (
        <div className="text-fog text-sm py-10 border-t border-ash/60">
          Type a name, address, phone, or company to search across leads, buyers, and title companies.
        </div>
      )}

      {query && (
        <div className="space-y-8">
          {/* Leads */}
          <section>
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="font-display text-xl text-ivory">
                Leads <span className="text-gold/60 text-base ml-2">{leadHits.length}</span>
              </h2>
              <Link href="/" className="text-[11px] text-gold/80 hover:text-gold">all leads</Link>
            </div>
            {leadHits.length === 0 ? (
              <div className="text-sm text-smoke py-6 border border-dashed border-ash rounded">no lead matches</div>
            ) : (
              <div className="space-y-2">
                {leadHits.map((l) => (
                  <Link key={l.id} href={`/leads/${l.id}`}
                    className="flex items-center justify-between p-3 bg-card-gradient border border-ash rounded-lg hover:border-gold/50">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-ivory truncate">
                          {(l.owner_name || "Unknown").replace(/\s+/g, " ").trim()}
                        </span>
                        <StatusBadge status={l.status as string} />
                      </div>
                      <div className="text-[11px] text-smoke flex items-center gap-1 mt-0.5">
                        <MapPin className="w-3 h-3" />{l.address}, {l.city}, {l.state}
                      </div>
                    </div>
                    <div className="text-[11px] text-gold font-mono ml-4">{compactMoney(l.estimated_arv ?? l.arv ?? 0)}</div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          {/* Buyers */}
          <section>
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="font-display text-xl text-ivory">
                Buyers <span className="text-gold/60 text-base ml-2">{buyerHits.length}</span>
              </h2>
              <Link href="/buyers" className="text-[11px] text-gold/80 hover:text-gold">all buyers</Link>
            </div>
            {buyerHits.length === 0 ? (
              <div className="text-sm text-smoke py-6 border border-dashed border-ash rounded">no buyer matches</div>
            ) : (
              <div className="grid md:grid-cols-2 gap-2">
                {buyerHits.map((b, i) => (
                  <div key={`${b.email}-${i}`} className="p-3 bg-card-gradient border border-ash rounded-lg">
                    <div className="font-medium text-ivory">{b.company || b.name}</div>
                    <div className="text-[11px] text-fog space-y-0.5 mt-1">
                      {b.email && <div className="flex items-center gap-1.5 truncate"><Mail className="w-3 h-3" />{b.email}</div>}
                      {b.phone && <div className="flex items-center gap-1.5"><Phone className="w-3 h-3" />{b.phone}</div>}
                      <div className="text-gold text-[10px] tracking-wider mt-1">
                        {b.state} -- {b.market || b.city}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Title companies */}
          <section>
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="font-display text-xl text-ivory">
                Title companies <span className="text-gold/60 text-base ml-2">{titleHits.length}</span>
              </h2>
              <Link href="/title-companies" className="text-[11px] text-gold/80 hover:text-gold">all titles</Link>
            </div>
            {titleHits.length === 0 ? (
              <div className="text-sm text-smoke py-6 border border-dashed border-ash rounded">no title matches</div>
            ) : (
              <div className="grid md:grid-cols-2 gap-2">
                {titleHits.map((t, i) => (
                  <div key={`${t.state}-${t.rank}-${i}`}
                    className={`p-3 border rounded-lg ${t.primary ? "border-gold/40 bg-gold/5" : "border-ash bg-card-gradient"}`}>
                    <div className="flex items-center gap-2">
                      <Building2 className={t.primary ? "w-4 h-4 text-gold" : "w-4 h-4 text-smoke"} />
                      <span className="font-medium text-ivory">{t.name}</span>
                    </div>
                    <div className="text-[11px] text-fog mt-1">
                      {t.state} / rank #{t.rank} {t.phone && <span className="ml-2">{t.phone}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}