import Link from "next/link";
import { getStateGates, getComplianceDocs } from "@/lib/api/wholesale";
import { Shield, FileText, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

export const dynamic = "force-dynamic";

const RISK_COLORS = {
  low:    { fg: "text-green-400",  bg: "bg-green-400/10",  border: "border-green-400/30" },
  medium: { fg: "text-amber-400",  bg: "bg-amber-400/10",  border: "border-amber-400/30" },
  high:   { fg: "text-red-400",    bg: "bg-red-400/10",    border: "border-red-400/30" },
};

function YN({ on, label }: { on: boolean; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px]">
      {on ? <CheckCircle2 size={11} className="text-green-400" /> : <XCircle size={11} className="text-red-400" />}
      <span className="text-gray-400">{label}</span>
    </div>
  );
}

export default async function CompliancePage() {
  const { meta, states } = await getStateGates();
  const docs = await getComplianceDocs();

  const stateEntries = Object.entries(states);
  const activeStates = stateEntries.filter(([, s]) => s.active_in_pipeline).length;

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6 page-enter">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold gradient-gold tracking-wider flex items-center gap-2">
            <Shield size={20} /> COMPLIANCE
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            State-by-state operational gates · {stateEntries.length} states · {activeStates} active in pipeline
          </p>
        </div>
        {meta && (
          <div className="text-[10px] text-gray-600 font-mono text-right">
            <div>generated {String(meta.generated)}</div>
            <div>reload: {String(meta.reload_cadence)}</div>
          </div>
        )}
      </div>

      {/* State grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stateEntries.map(([code, s]) => {
          const r = RISK_COLORS[s.risk_rating] ?? RISK_COLORS.medium;
          return (
            <Link
              key={code}
              href={`/compliance/${code}`}
              className="card group block"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-2xl font-bold text-amber-400">{code}</span>
                    <span className="text-xs text-gray-400">{s.name}</span>
                  </div>
                  <div className={`text-[10px] uppercase tracking-widest mt-1 ${r.fg}`}>
                    {s.wholesale_legal_status?.replace(/_/g, " ")}
                  </div>
                </div>
                <span className={`px-2 py-1 rounded-md text-[10px] uppercase font-semibold border ${r.bg} ${r.fg} ${r.border}`}>
                  {s.risk_rating}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-1.5 mb-3">
                <YN on={s.sms_allowed} label="SMS" />
                <YN on={s.cold_call_allowed} label="Cold call" />
                <YN on={s.preforeclosure_outreach_allowed} label="Pre-foreclosure" />
                <YN on={s.assignment_contract_legal} label="Assignment legal" />
              </div>

              <div className="border-t border-white/[0.04] pt-3 grid grid-cols-2 gap-2 text-[10px]">
                <div>
                  <span className="text-gray-500">Closing:</span>{" "}
                  <span className="font-mono text-gray-300">{s.closing_type}</span>
                </div>
                <div>
                  <span className="text-gray-500">Active:</span>{" "}
                  {s.active_in_pipeline
                    ? <span className="text-green-400 font-mono">YES</span>
                    : <span className="text-gray-500 font-mono">NO</span>}
                </div>
                <div className="col-span-2">
                  <span className="text-gray-500">Hours:</span>{" "}
                  <span className="font-mono text-gray-300">{s.outbound_call_hours_local?.mon_sat_start}-{s.outbound_call_hours_local?.mon_sat_end}</span>
                  {!s.outbound_call_hours_local?.sun_allowed && <span className="text-red-400 ml-2">no Sun</span>}
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Policy docs */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <FileText size={16} className="text-amber-400" />
          <h2 className="font-display text-lg font-semibold text-amber-400/80 uppercase tracking-wider">
            Policy library
          </h2>
          <span className="text-[10px] text-gray-600">{docs.length} docs</span>
        </div>
        {docs.length === 0 ? (
          <div className="text-sm text-gray-500 italic">No policy docs found in compliance folder.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {docs.map((d) => (
              <Link
                key={d.slug}
                href={`/compliance/policy/${d.slug}`}
                className="flex items-start gap-3 p-3 rounded-lg border border-white/[0.04] hover:border-amber-400/30 hover:bg-white/[0.02] transition group"
              >
                <FileText size={14} className="text-amber-400/60 mt-0.5 flex-shrink-0 group-hover:text-amber-400" />
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{d.title}</div>
                  <div className="text-[11px] text-gray-500 line-clamp-2 mt-0.5">{d.preview}</div>
                </div>
                <span className="text-[9px] text-gray-600 font-mono flex-shrink-0">{(d.size / 1024).toFixed(1)}k</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="card border-amber-400/30 bg-amber-400/5">
        <div className="flex items-start gap-2">
          <AlertTriangle size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-300">
            <span className="text-amber-400 font-semibold">Compliance principle:</span>{" "}
            {meta?.principle as string ?? "If a flag is false or missing, the pipeline must not perform that action in this state."}
          </div>
        </div>
      </div>
    </div>
  );
}
