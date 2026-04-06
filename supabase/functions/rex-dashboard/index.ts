import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww";
const BASE = "https://jdqqmsmwmbsnlnstyavl.supabase.co";

const page = () => `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Rex Pipeline | Everlight Ventures</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Inter',sans-serif;background:#0a0a14;color:#f0f0f0;-webkit-font-smoothing:antialiased}
    :root{--gold:#c9a84c;--navy:#0a0a14;--card:#16162a;--border:#2a2a3a;--green:#22c55e;--red:#ef4444;--blue:#3b82f6;--orange:#f59e0b}
    #root{min-height:100vh}
  </style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const { useState, useEffect } = React;
const ANON = "${ANON_KEY}";
const API = "${BASE}/rest/v1";

function fmt(n) { return n ? "$" + Number(n).toLocaleString() : "$0"; }

function Badge({ text, color }) {
  const colors = { green: "var(--green)", red: "var(--red)", gold: "var(--gold)", blue: "var(--blue)", orange: "var(--orange)" };
  return <span style={{ background: (colors[color]||"#555")+"22", color: colors[color]||"#888", padding:"3px 10px", borderRadius:12, fontSize:11, fontWeight:600 }}>{text}</span>;
}

function StatCard({ label, value, sub, color="var(--gold)" }) {
  return (
    <div style={{ background:"var(--card)", border:"1px solid var(--border)", borderRadius:12, padding:"20px 16px", textAlign:"center" }}>
      <div style={{ fontSize:28, fontWeight:800, color }}>{value}</div>
      <div style={{ fontSize:12, color:"#8a8a9a", marginTop:4 }}>{label}</div>
      {sub && <div style={{ fontSize:11, color:"#5a5a6a", marginTop:2 }}>{sub}</div>}
    </div>
  );
}

function App() {
  const [leads, setLeads] = useState([]);
  const [buyers, setBuyers] = useState([]);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("arv");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const headers = { apikey: ANON };
    Promise.all([
      fetch(API + "/rex_pipeline?select=*&order=arv.desc", { headers }).then(r => r.json()),
      fetch(API + "/investor_buyers?select=*", { headers }).then(r => r.json()),
    ]).then(([l, b]) => {
      setLeads(Array.isArray(l) ? l : []);
      setBuyers(Array.isArray(b) ? b : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{padding:40,textAlign:"center",color:"var(--gold)"}}>Loading pipeline...</div>;

  const active = leads.filter(l => l.status !== "dead" && l.status !== "DISQUALIFIED" && l.status !== "opted_out");
  const tier1 = active.filter(l => l.close_tier === "CLOSE_THIS_WEEK");
  const tier2 = active.filter(l => l.close_tier === "CLOSE_THIS_MONTH");
  const tier3 = active.filter(l => l.close_tier === "LONG_GAME");
  const withEmail = active.filter(l => l.owner_email);
  const ozLeads = active.filter(l => l.opportunity_zone);
  const contacted = active.filter(l => l.outreach_count > 0);
  const totalFees = active.reduce((s, l) => s + (l.assignment_fee || 0), 0);

  const filtered = filter === "all" ? active
    : filter === "tier1" ? tier1
    : filter === "tier2" ? tier2
    : filter === "tier3" ? tier3
    : filter === "oz" ? ozLeads
    : filter === "email" ? withEmail
    : active;

  const sorted = [...filtered].sort((a, b) => {
    if (sort === "arv") return (b.arv || 0) - (a.arv || 0);
    if (sort === "fee") return (b.assignment_fee || 0) - (a.assignment_fee || 0);
    if (sort === "tier") return (a.close_tier || "").localeCompare(b.close_tier || "");
    return 0;
  });

  return (
    <div style={{ maxWidth:1200, margin:"0 auto", padding:"24px 16px" }}>
      {/* Header */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:24, flexWrap:"wrap", gap:12 }}>
        <div>
          <h1 style={{ fontSize:24, fontWeight:800 }}>REX <span style={{ color:"var(--gold)" }}>PIPELINE</span></h1>
          <p style={{ fontSize:13, color:"#5a5a6a" }}>Everlight Ventures | Wholesale Dashboard</p>
        </div>
        <div style={{ fontSize:12, color:"#5a5a6a" }}>Auto-refreshes on page load</div>
      </div>

      {/* Stats */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))", gap:12, marginBottom:24 }}>
        <StatCard label="Total Leads" value={active.length} />
        <StatCard label="Tier 1 (This Week)" value={tier1.length} color="var(--green)" />
        <StatCard label="Tier 2 (This Month)" value={tier2.length} color="var(--blue)" />
        <StatCard label="With Email" value={withEmail.length} color="var(--orange)" />
        <StatCard label="OZ Properties" value={ozLeads.length} color="var(--gold)" />
        <StatCard label="Contacted" value={contacted.length} sub={"of " + active.length} />
        <StatCard label="Buyers Ready" value={buyers.length} color="var(--green)" />
        <StatCard label="Total Fees" value={fmt(totalFees)} color="var(--gold)" sub="if all close" />
      </div>

      {/* Filters */}
      <div style={{ display:"flex", gap:8, marginBottom:16, flexWrap:"wrap" }}>
        {[["all","All"],["tier1","Tier 1"],["tier2","Tier 2"],["tier3","Long Game"],["oz","OZ Only"],["email","Has Email"]].map(([k,label]) => (
          <button key={k} onClick={() => setFilter(k)}
            style={{ background: filter===k ? "var(--gold)" : "var(--card)", color: filter===k ? "#0a0a14" : "#8a8a9a",
              border:"1px solid " + (filter===k ? "var(--gold)" : "var(--border)"), borderRadius:8, padding:"6px 14px", fontSize:12, fontWeight:600, cursor:"pointer" }}>
            {label} ({k==="all"?active.length:k==="tier1"?tier1.length:k==="tier2"?tier2.length:k==="tier3"?tier3.length:k==="oz"?ozLeads.length:withEmail.length})
          </button>
        ))}
        <select value={sort} onChange={e => setSort(e.target.value)}
          style={{ background:"var(--card)", color:"#8a8a9a", border:"1px solid var(--border)", borderRadius:8, padding:"6px 10px", fontSize:12 }}>
          <option value="arv">Sort: Value</option>
          <option value="fee">Sort: Fee</option>
          <option value="tier">Sort: Tier</option>
        </select>
      </div>

      {/* Table */}
      <div style={{ overflowX:"auto" }}>
        <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
          <thead>
            <tr style={{ borderBottom:"2px solid var(--border)" }}>
              {["Owner","Address","City","Value","Offer","Fee","Tier","Type","OZ","Contact","Step"].map(h => (
                <th key={h} style={{ padding:"10px 8px", textAlign:"left", color:"#5a5a6a", fontSize:11, fontWeight:600, textTransform:"uppercase", letterSpacing:1 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((l, i) => {
              const tierColor = l.close_tier === "CLOSE_THIS_WEEK" ? "green" : l.close_tier === "CLOSE_THIS_MONTH" ? "blue" : "orange";
              const tierLabel = l.close_tier === "CLOSE_THIS_WEEK" ? "THIS WEEK" : l.close_tier === "CLOSE_THIS_MONTH" ? "THIS MONTH" : "LONG";
              return (
                <tr key={i} style={{ borderBottom:"1px solid #1a1a2a" }}
                  onMouseOver={e => e.currentTarget.style.background="#1a1a2e"}
                  onMouseOut={e => e.currentTarget.style.background="transparent"}>
                  <td style={{ padding:"10px 8px", fontWeight:600, maxWidth:150, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{l.owner_name || "Unknown"}</td>
                  <td style={{ padding:"10px 8px", color:"#8a8a9a", maxWidth:200, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{l.address}</td>
                  <td style={{ padding:"10px 8px", color:"#8a8a9a" }}>{l.city}, {l.state}</td>
                  <td style={{ padding:"10px 8px", fontWeight:600 }}>{fmt(l.arv)}</td>
                  <td style={{ padding:"10px 8px" }}>{fmt(l.offer_price)}</td>
                  <td style={{ padding:"10px 8px", color:"var(--gold)", fontWeight:700 }}>{fmt(l.assignment_fee)}</td>
                  <td style={{ padding:"10px 8px" }}><Badge text={tierLabel} color={tierColor} /></td>
                  <td style={{ padding:"10px 8px" }}><Badge text={l.lead_type || "?"} color={l.lead_type?.includes("foreclosure") ? "red" : l.lead_type?.includes("code") ? "orange" : "blue"} /></td>
                  <td style={{ padding:"10px 8px" }}>{l.opportunity_zone ? <Badge text="OZ" color="gold" /> : ""}</td>
                  <td style={{ padding:"10px 8px" }}>{l.owner_email ? <Badge text="EMAIL" color="green" /> : l.owner_phone ? <Badge text="PHONE" color="blue" /> : <Badge text="NONE" color="red" />}</td>
                  <td style={{ padding:"10px 8px", color:"#5a5a6a" }}>{l.sequence_step}/7</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {sorted.length === 0 && <div style={{textAlign:"center",padding:40,color:"#5a5a6a"}}>No leads match this filter</div>}

      {/* Footer */}
      <div style={{ textAlign:"center", padding:"40px 0 20px", color:"#3a3a4a", fontSize:11 }}>
        Rex Pipeline | Everlight Ventures | Data refreshes on page load
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
</script>
</body>
</html>`;

serve((_req: Request) => {
  return new Response(page(), {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "public, max-age=300",
    },
  });
});
