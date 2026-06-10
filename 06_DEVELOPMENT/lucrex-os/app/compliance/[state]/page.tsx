import Link from "next/link";
import { ArrowLeft, CheckCircle2, XCircle, Clock, Phone, MessageSquare, Mail, FileSignature } from "lucide-react";
import { getStateGates } from "@/lib/api/wholesale";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

function Row({ label, value, ok }: { label: string; value: React.ReactNode; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-white/[0.03] last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`font-mono text-sm ${ok === true ? "text-green-400" : ok === false ? "text-red-400" : "text-gray-300"}`}>
        {value}
      </span>
    </div>
  );
}

export default async function StateDetail({ params }: { params: Promise<{ state: string }> }) {
  const { state } = await params;
  const { states } = await getStateGates();
  const s = states[state.toUpperCase()];
  if (!s) return notFound();

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto space-y-6 page-enter">
      <Link href="/compliance" className="inline-flex items-center gap-2 text-xs text-gray-500 hover:text-amber-400 transition">
        <ArrowLeft size={12} /> All states
      </Link>

      <div className="flex items-baseline justify-between flex-wrap gap-3">
        <div>
          <div className="font-mono text-5xl font-black text-amber-400">{state.toUpperCase()}</div>
          <h1 className="font-display text-2xl font-semibold mt-1">{s.name}</h1>
          <div className="text-xs text-gray-500 mt-1">{s.wholesale_legal_status?.replace(/_/g, " ")}</div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1.5 rounded-md text-xs font-bold uppercase border ${
            s.risk_rating === "low" ? "bg-green-400/10 text-green-400 border-green-400/30" :
            s.risk_rating === "high" ? "bg-red-400/10 text-red-400 border-red-400/30" :
            "bg-amber-400/10 text-amber-400 border-amber-400/30"
          }`}>{s.risk_rating} risk</span>
          {s.active_in_pipeline ? (
            <span className="px-3 py-1.5 rounded-md text-xs font-bold uppercase border bg-blue-400/10 text-blue-400 border-blue-400/30">active</span>
          ) : (
            <span className="px-3 py-1.5 rounded-md text-xs font-bold uppercase border bg-gray-400/10 text-gray-400 border-gray-400/30">inactive</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Outbound channels */}
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare size={14} className="text-amber-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Outbound channels</h2>
          </div>
          <Row label="SMS allowed" value={s.sms_allowed ? "YES" : "NO"} ok={s.sms_allowed} />
          {s.sms_conditions && s.sms_conditions.length > 0 && (
            <div className="text-[10px] text-gray-500 -mt-1 pl-2 mb-1">+ conditions: {s.sms_conditions.join(", ")}</div>
          )}
          <Row label="Cold call allowed" value={s.cold_call_allowed ? "YES" : "NO"} ok={s.cold_call_allowed} />
          {s.cold_call_conditions && s.cold_call_conditions.length > 0 && (
            <div className="text-[10px] text-gray-500 -mt-1 pl-2 mb-1">+ conditions: {s.cold_call_conditions.join(", ")}</div>
          )}
          <Row label="Inbound SMS allowed" value={s.inbound_sms_allowed ? "YES" : "NO"} ok={s.inbound_sms_allowed} />
          <Row label="Email hours restricted" value={s.email_hours_restricted ? "YES" : "NO"} ok={!s.email_hours_restricted} />
          <Row label="Auto bot calls (cold)" value={s.autonomous_bot_call_allowed_cold ? "YES" : "NO"} ok={s.autonomous_bot_call_allowed_cold} />
          {s.autonomous_bot_call_reason && (
            <div className="text-[10px] text-gray-500 mt-2 pt-2 border-t border-white/[0.03]">{s.autonomous_bot_call_reason}</div>
          )}
        </div>

        {/* Call hours */}
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Clock size={14} className="text-amber-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Call hours (local)</h2>
          </div>
          <Row label="Mon-Sat" value={`${s.outbound_call_hours_local.mon_sat_start} - ${s.outbound_call_hours_local.mon_sat_end}`} />
          <Row
            label="Sunday"
            value={s.outbound_call_hours_local.sun_allowed ? `${s.outbound_call_hours_local.sun_start ?? "?"} - ${s.outbound_call_hours_local.sun_end ?? "?"}` : "BLOCKED"}
            ok={s.outbound_call_hours_local.sun_allowed}
          />
          <Row label="Recording consent" value={s.call_recording_consent} />
          <Row label="Disclosure required" value={s.recording_disclosure_required ? "YES" : "NO"} ok={!s.recording_disclosure_required} />
          <Row label="State DNC list" value={s.state_dnc_list ? "YES" : "NO"} />
        </div>

        {/* Closing + contracts */}
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <FileSignature size={14} className="text-amber-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Closing &amp; contracts</h2>
          </div>
          <Row label="Closing type" value={s.closing_type} />
          <Row label="Preferred closer" value={s.preferred_closer_id ?? "-"} />
          <Row label="Assignment contract legal" value={s.assignment_contract_legal ? "YES" : "NO"} ok={s.assignment_contract_legal} />
          <Row label="Foreign LLC required" value={s.foreign_llc_registration_required ? "YES" : "NO"} />
          <Row label="ARV in writing OK" value={s.arv_in_writing_to_seller_allowed ? "YES" : "NO"} ok={s.arv_in_writing_to_seller_allowed} />
          <Row label="Unlicensed appraisal risk" value={s.unlicensed_appraisal_risk} />
        </div>

        {/* Solicitor + foreclosure */}
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Phone size={14} className="text-amber-400" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Registration &amp; foreclosure</h2>
          </div>
          <Row label="Solicitor reg required" value={s.solicitor_registration_required ? "YES" : "NO"} ok={!s.solicitor_registration_required} />
          <Row label="Solicitor bond" value={s.solicitor_bond_usd > 0 ? `$${s.solicitor_bond_usd.toLocaleString()}` : "$0"} />
          <Row label="Pre-foreclosure outreach" value={s.preforeclosure_outreach_allowed ? "YES" : "NO"} ok={s.preforeclosure_outreach_allowed} />
          <Row label="Foreclosure consultant statute" value={s.foreclosure_consultant_statute ? "YES" : "NO"} />
        </div>
      </div>

      {/* Disclosure */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Mail size={14} className="text-amber-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-amber-400/80">Disclosures required</h2>
        </div>
        <Row label="Seller disclosure" value={s.required_seller_disclosure} />
        <Row label="Buyer disclosure" value={s.required_buyer_disclosure ?? "-"} />
      </div>

      {/* Notes */}
      {s.gate_notes && (
        <div className="card border-amber-400/20">
          <div className="text-[10px] uppercase tracking-widest text-amber-400/80 mb-2">Gate notes</div>
          <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">{s.gate_notes}</p>
        </div>
      )}
    </div>
  );
}
