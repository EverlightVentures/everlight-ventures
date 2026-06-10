import { loadTitleCompanies, titleCompaniesForState } from "@/lib/data";
import { Building2, ExternalLink, Phone, Mail } from "lucide-react";
import { Breadcrumbs } from "@/components/breadcrumbs";

export const dynamic = "force-dynamic";

const WORKABLE_STATES = ["GA", "FL", "TX", "MO", "AZ", "TN", "NC"];

export default async function TitlesPage() {
  const db = await loadTitleCompanies();
  const rows = WORKABLE_STATES
    .map((st) => ({ state: st, companies: titleCompaniesForState(db, st) }))
    .filter((r) => r.companies.length > 0);

  return (
    <div className="space-y-6">
      <Breadcrumbs items={[{ label: "Title companies" }]} />
      <header>
        <div className="text-[11px] tracking-[0.3em] text-gold/80 uppercase">Closing partners</div>
        <h1 className="font-display text-4xl text-ivory mt-2 tracking-tight">Title companies</h1>
        <p className="text-fog text-sm mt-2 max-w-2xl">
          State-ranked closing partners. When a deal locks, we try rank 1. If they decline,
          we walk down the fallback chain automatically.
        </p>
      </header>

      <div className="space-y-8">
        {rows.map(({ state, companies }) => (
          <section key={state}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gold/10 border border-gold/30 rounded flex items-center justify-center">
                <span className="font-display text-gold text-lg">{state}</span>
              </div>
              <div>
                <h2 className="font-display text-xl text-ivory">{state} closing chain</h2>
                <p className="text-[11px] text-fog">
                  {companies.length} companies in fallback chain
                </p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {companies.map((tc) => (
                <div
                  key={`${state}-${tc.rank}-${tc.name}`}
                  className={`card-hover border rounded-xl p-4 transition ${
                    tc.primary
                      ? "border-gold/50 bg-gold/5 shadow-gold-glow"
                      : "border-ash bg-card-gradient"
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] tracking-[0.25em] text-fog uppercase">
                          RANK #{tc.rank}
                        </span>
                        {tc.primary && (
                          <span className="text-[10px] tracking-widest bg-gold text-obsidian rounded-full px-2 py-0.5">
                            PRIMARY
                          </span>
                        )}
                      </div>
                      <div className="font-medium text-ivory mt-1.5">{tc.name}</div>
                      {tc.contact && (
                        <div className="text-[11px] text-fog">{tc.contact}</div>
                      )}
                    </div>
                    <Building2 className={tc.primary ? "w-5 h-5 text-gold" : "w-5 h-5 text-smoke"} />
                  </div>

                  <div className="space-y-1.5 text-[12px] text-fog mt-3">
                    {tc.phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="w-3 h-3 text-smoke" />
                        <span>{tc.phone}</span>
                      </div>
                    )}
                    {tc.email && (
                      <div className="flex items-center gap-2">
                        <Mail className="w-3 h-3 text-smoke" />
                        <span className="truncate">{tc.email}</span>
                      </div>
                    )}
                    {tc.website && (
                      <a href={tc.website} target="_blank" rel="noreferrer"
                        className="inline-flex items-center gap-1 text-gold/80 hover:text-gold">
                        website <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>

                  {tc.notes && (
                    <p className="text-[11px] text-smoke mt-3 leading-relaxed line-clamp-3 pt-3 border-t border-ash/50">
                      {tc.notes}
                    </p>
                  )}

                  <div className="mt-3 pt-3 border-t border-ash/50 flex items-center justify-between text-[10px] text-fog">
                    <span>closed {tc.deals_closed ?? 0}</span>
                    {tc.handles_assignments && (
                      <span className="text-success">assignments OK</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}