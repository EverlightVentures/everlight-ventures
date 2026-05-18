#!/usr/bin/env python3
"""
Generate the multi-page Intel Center dashboard.
Each page = same head/style/body shell + a per-page <script type=module> section.

Run: python3 scripts/gen_pages.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 09_Dashboard

HEAD = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0a0a0f">
<title>{title} · Intel Center</title>

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800;900&family=DM+Sans:wght@400;500;700;800;900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

<script src="https://cdn.tailwindcss.com"></script>
<script>
tailwind.config = {{
  theme: {{
    extend: {{
      colors: {{
        ev: {{ bg:'#0a0a0f', surface:'#111118', s2:'#1a1a24', s3:'#222230', s4:'#2d2d3d',
              gold:'#c9a84c', goldDim:'#a0832e', goldGlow:'#e0c66a',
              cyan:'#22d3ee', purple:'#8b5cf6', green:'#22c55e',
              orange:'#f97316', red:'#dc2626', text:'#e8e8e8', dim:'#999' }}
      }},
      fontFamily: {{
        display: ['"Playfair Display"','serif'],
        sans:    ['"DM Sans"','"Inter"','sans-serif'],
        body:    ['"Inter"','sans-serif'],
        mono:    ['"JetBrains Mono"','monospace'],
      }},
      boxShadow: {{ glow:'0 0 40px rgba(201,168,76,0.25)', glowStrong:'0 0 60px rgba(201,168,76,0.5)' }},
    }}
  }}
}}
</script>
<script src="https://unpkg.com/lucide@latest"></script>
<script src="./data.js"></script>

<style>
  :root {{ --gold:#c9a84c; --gold-dim:#a0832e; --gold-glow:#e0c66a; --bg:#0a0a0f; }}
  *{{ -webkit-tap-highlight-color:transparent; }}
  html,body{{ background:var(--bg); color:#e8e8e8; font-family:"Inter",sans-serif; overflow-x:hidden; }}
  .mesh{{ position:fixed; inset:0; pointer-events:none; z-index:0; overflow:hidden; }}
  .mesh::before, .mesh::after, .mesh > span{{
    content:''; position:absolute; border-radius:50%; filter:blur(80px); opacity:0.45;
    animation: drift 22s ease-in-out infinite;
  }}
  .mesh::before{{ width:520px; height:520px; left:-10%;  top:-15%; background:radial-gradient(closest-side,#3a2a08,transparent); }}
  .mesh::after {{ width:480px; height:480px; right:-8%;  top:35%;  background:radial-gradient(closest-side,#1b1135,transparent); animation-delay:-7s; }}
  .mesh > span {{ width:600px; height:600px; left:35%;   bottom:-20%; background:radial-gradient(closest-side,#0a2027,transparent); animation-delay:-14s; }}
  @keyframes drift{{ 0%,100%{{transform:translate(0,0) scale(1)}} 33%{{transform:translate(40px,-30px) scale(1.05)}} 66%{{transform:translate(-30px,40px) scale(0.95)}} }}

  .glass{{ background:linear-gradient(135deg, rgba(17,17,24,0.78), rgba(17,17,24,0.45));
          border:1px solid rgba(255,255,255,0.06); backdrop-filter:blur(12px) saturate(140%);
          -webkit-backdrop-filter:blur(12px) saturate(140%); }}
  .glass-gold{{ background:linear-gradient(135deg, rgba(201,168,76,0.10), rgba(201,168,76,0.02));
               border:1px solid rgba(201,168,76,0.35); }}
  .gold{{ color:var(--gold); }}
  .gold-glow{{ text-shadow:0 0 24px rgba(201,168,76,0.45); }}
  .lift{{ transition:transform .25s ease, box-shadow .25s ease, border-color .25s ease; }}
  .lift:hover{{ transform:translateY(-2px); border-color:rgba(201,168,76,0.5); box-shadow:0 8px 32px rgba(201,168,76,0.12); }}
  .nav-link{{ color:#999; transition:color .2s; padding:.5rem .9rem; border-radius:.5rem; }}
  .nav-link:hover{{ color:#e0c66a; background:rgba(201,168,76,0.06); }}
  .nav-link.active{{ color:#c9a84c; background:rgba(201,168,76,0.12); border:1px solid rgba(201,168,76,0.25); }}
  .bar{{ height:6px; background:rgba(255,255,255,.06); border-radius:3px; overflow:hidden; position:relative; }}
  .bar > i{{ display:block; height:100%; background:linear-gradient(90deg,#c9a84c,#e0c66a); border-radius:3px; }}
  .chip{{ display:inline-flex; align-items:center; gap:.35rem; padding:.18rem .55rem; border-radius:9999px; font-size:.7rem;
         font-family:"JetBrains Mono",monospace; letter-spacing:.04em; }}
  .chip-gold{{ background:rgba(201,168,76,.10); color:#e0c66a; border:1px solid rgba(201,168,76,.3); }}
  .chip-green{{ background:rgba(34,197,94,.10); color:#4ade80; border:1px solid rgba(34,197,94,.3); }}
  .chip-red{{   background:rgba(220,38,38,.10); color:#f87171; border:1px solid rgba(220,38,38,.3); }}
  .chip-cyan{{  background:rgba(34,211,238,.10); color:#67e8f9; border:1px solid rgba(34,211,238,.3); }}
  main{{ animation: fadein .35s ease-out both; }}
  @keyframes fadein{{ from{{opacity:0; transform:translateY(6px)}} to{{opacity:1; transform:translateY(0)}} }}
  input.search{{ background: rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.1); color:#e8e8e8;
                 padding:.6rem 1rem .6rem 2.5rem; border-radius:.6rem; width:100%; outline:none;
                 transition: border-color .2s; }}
  input.search:focus{{ border-color:#c9a84c; }}
  .pill-btn{{ padding:.35rem .9rem; border-radius:9999px; font-size:.78rem; cursor:pointer;
              border:1px solid rgba(255,255,255,0.12); transition: all .2s; }}
  .pill-btn:hover{{ border-color:#c9a84c; color:#e0c66a; }}
  .pill-btn.on{{ background:rgba(201,168,76,0.15); border-color:#c9a84c; color:#e0c66a; }}
  table.intel{{ width:100%; border-collapse:collapse; }}
  table.intel th, table.intel td{{ text-align:left; padding:.6rem .8rem; border-bottom:1px solid rgba(255,255,255,0.05); font-size:.85rem; }}
  table.intel th{{ background:rgba(201,168,76,0.04); color:#c9a84c; font-weight:500; text-transform:uppercase; letter-spacing:.08em; font-size:.7rem; }}
  table.intel tr:hover td{{ background:rgba(201,168,76,0.03); }}
  table.intel a{{ color:#e0c66a; }}
  table.intel a:hover{{ text-decoration:underline; }}
</style>
</head>
<body class="min-h-screen relative">
<div class="mesh"><span></span></div>
<div id="app" class="relative z-10"></div>
'''

FOOTER_TAIL = '''</body>
</html>'''


def page(title: str, body_module: str) -> str:
    return HEAD.format(title=title) + f'\n<script type="module">\n{body_module}\n</script>\n' + FOOTER_TAIL


# ============== RESOURCES PAGE ==============
RESOURCES = '''
import { html, render, h, useState, useMemo, D, fmt, pct, useLucide, Icon, Nav, Footer } from "./shared.js";

function ResourcesPage(){
  useLucide();
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("ALL");
  const [agent, setAgent] = useState("ALL");
  const [onlyInUse, setOnlyInUse] = useState(false);

  const cats = useMemo(() => ["ALL", ...D.categories.map(c => c.name)], []);
  const agents = useMemo(() => ["ALL", ...D.agents.map(a => a.name)], []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return D.resources.filter(r => {
      if (cat !== "ALL" && r.category !== cat) return false;
      if (agent !== "ALL" && r.agent_owner !== agent) return false;
      if (onlyInUse && !r.in_use) return false;
      if (!needle) return true;
      return (r.domain + " " + r.purpose + " " + r.tags + " " + r.name).toLowerCase().includes(needle);
    });
  }, [q, cat, agent, onlyInUse]);

  return html`
    <${Nav} active="resources"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="mb-6">
        <h1 class="font-display text-3xl gold gold-glow mb-1">Resource Browser</h1>
        <p class="text-sm text-ev-dim">Search and filter all ${fmt(D.meta.total)} resources. Click a domain to open it.</p>
      </div>

      <div class="glass rounded-2xl p-5 mb-6 space-y-4">
        <div class="relative">
          <${Icon} name="search" cls="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ev-dim"/>
          <input class="search font-mono"
                 placeholder="Search domain, purpose, tag, name..."
                 value=${q} onInput=${e => setQ(e.target.value)}/>
        </div>
        <div class="flex flex-wrap gap-2 items-center">
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-2">Category</span>
          ${cats.slice(0, 9).map(c => html`
            <button class=${"pill-btn " + (cat===c ? "on" : "")} onClick=${() => setCat(c)}>${c==="ALL"?"All":c}</button>
          `)}
        </div>
        <div class="flex flex-wrap gap-2 items-center">
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-2">Agent</span>
          ${agents.map(a => html`
            <button class=${"pill-btn " + (agent===a ? "on" : "")} onClick=${() => setAgent(a)}>${a==="ALL"?"All":a}</button>
          `)}
          <label class="flex items-center gap-2 text-xs text-ev-dim ml-3 cursor-pointer">
            <input type="checkbox" checked=${onlyInUse} onChange=${e => setOnlyInUse(e.target.checked)}/>
            <span>only currently used</span>
          </label>
        </div>
      </div>

      <div class="text-xs text-ev-dim mb-3 font-mono">${fmt(filtered.length)} of ${fmt(D.meta.total)} match</div>

      <div class="glass rounded-2xl overflow-hidden">
        <div class="overflow-x-auto" style="max-height: 70vh; overflow-y:auto">
          <table class="intel">
            <thead><tr>
              <th>Domain</th><th>Purpose</th><th>Category</th><th>Agent</th><th class="w-16">Status</th>
            </tr></thead>
            <tbody>
              ${filtered.slice(0, 500).map(r => html`
                <tr>
                  <td class="font-mono"><a href=${"./resource.html?d=" + r.domain}>${r.domain}</a></td>
                  <td class="text-ev-text/80">${r.purpose}</td>
                  <td class="text-xs"><span class="chip chip-gold">${r.category}</span></td>
                  <td class="text-xs text-ev-dim">${r.agent_owner}</td>
                  <td>${r.in_use
                       ? html`<span class="chip chip-green">USED</span>`
                       : ((r.article_count||0) > 0
                          ? html`<span class="chip chip-cyan">${r.article_count} cached</span>`
                          : (r.verified_status === "checked"
                             ? html`<span class="chip chip-cyan">CURATED</span>`
                             : (r.verified_status === "unverified"
                                ? html`<span class="chip chip-red">REVIEW</span>` : "")))}</td>
                </tr>`)}
            </tbody>
          </table>
        </div>
        ${filtered.length > 500 && html`<div class="p-3 text-center text-xs text-ev-dim border-t border-white/5">Showing first 500 -- narrow your filters</div>`}
      </div>
    </main>
    <${Footer}/>`;
}

render(html`<${ResourcesPage}/>`, document.getElementById("app"));
'''

# ============== CATEGORIES PAGE ==============
CATEGORIES = '''
import { html, render, h, useState, useMemo, D, fmt, pct, useLucide, Icon, Nav, Footer, TOPIC_ICONS } from "./shared.js";

function CategoriesPage(){
  useLucide();
  const hash = decodeURIComponent((location.hash || "").replace(/^#/, ""));
  const [open, setOpen] = useState(hash || (D.categories[0] && D.categories[0].name) || "");

  return html`
    <${Nav} active="categories"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="mb-6">
        <h1 class="font-display text-3xl gold gold-glow mb-1">Categories</h1>
        <p class="text-sm text-ev-dim">${D.meta.categories} categories across ${fmt(D.meta.total)} resources. Pick one to drill in.</p>
      </div>

      <div class="grid lg:grid-cols-3 gap-4">
        <aside class="space-y-2 lg:col-span-1">
          ${D.categories.map(c => html`
            <button class=${"w-full text-left lift glass rounded-xl p-3 border " + (open===c.name ? "border-ev-gold/60 bg-ev-gold/5" : "border-white/5")}
                    onClick=${() => { setOpen(c.name); history.replaceState(null,"","#" + encodeURIComponent(c.name)); }}>
              <div class="flex items-center justify-between">
                <div>
                  <div class="font-medium text-sm">${c.name}</div>
                  <div class="text-[10px] text-ev-dim font-mono mt-0.5">${c.agent_owner}</div>
                </div>
                <div class="flex flex-col items-end gap-1">
                  <span class="font-mono gold text-sm">${c.count}</span>
                  ${c.fetchable && html`<span class="chip chip-cyan">FETCH</span>`}
                </div>
              </div>
            </button>`)}
        </aside>

        <section class="lg:col-span-2 glass rounded-2xl p-6">
          ${(() => {
            const cat = D.categories.find(c => c.name === open) || D.categories[0];
            if (!cat) return null;
            const items = D.resources.filter(r => r.category === cat.name);
            return html`
              <div class="flex items-start justify-between mb-5">
                <div>
                  <div class="text-[10px] uppercase tracking-[.2em] text-ev-dim mb-1">${cat.department}</div>
                  <h2 class="font-display text-2xl gold">${cat.name}</h2>
                  <div class="text-xs text-ev-dim mt-1">Owner: <span class="text-ev-text/80">${cat.agent_owner}</span> · ${cat.count} resources · ${cat.used} active</div>
                </div>
                ${cat.fetchable && html`<span class="chip chip-cyan">live-fetchable</span>`}
              </div>
              <div class="space-y-2">
                ${items.map(r => html`
                  <a href=${"./resource.html?d=" + r.domain} class="block lift glass rounded-lg p-3 border border-white/5">
                    <div class="flex justify-between items-start gap-3">
                      <div class="min-w-0">
                        <div class="font-mono gold text-sm truncate">${r.domain}</div>
                        <div class="text-xs text-ev-text/70 mt-1">${r.purpose}</div>
                      </div>
                      <div class="flex flex-col items-end gap-1 flex-shrink-0">
                        ${r.in_use && html`<span class="chip chip-green">USED</span>`}
                        ${(r.article_count||0) > 0 && html`<span class="chip chip-cyan">${r.article_count} items</span>`}
                        ${r.verified_status === "checked" && html`<span class="chip chip-cyan">CURATED</span>`}
                      </div>
                    </div>
                  </a>`)}
              </div>`;
          })()}
        </section>
      </div>
    </main>
    <${Footer}/>`;
}

render(html`<${CategoriesPage}/>`, document.getElementById("app"));
'''

# ============== AGENTS PAGE ==============
AGENTS = '''
import { html, render, h, useState, D, fmt, pct, useLucide, Icon, Nav, Footer } from "./shared.js";

function AgentsPage(){
  useLucide();
  const hash = (location.hash || "").replace(/^#/, "");
  const [open, setOpen] = useState(hash || (D.agents[0] && D.agents[0].slug) || "");
  const cur = D.agents.find(a => a.slug === open) || D.agents[0];
  const items = cur ? D.resources.filter(r => r.agent_owner === cur.name) : [];
  const itemsByCat = items.reduce((acc, r) => { (acc[r.category] = acc[r.category] || []).push(r); return acc; }, {});

  return html`
    <${Nav} active="agents"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="mb-6">
        <h1 class="font-display text-3xl gold gold-glow mb-1">Agent Roster</h1>
        <p class="text-sm text-ev-dim">${D.agents.length} agents own ${fmt(D.meta.total)} resources. Manifests live in <span class="font-mono text-ev-text/70">.claude/agents/sources/</span>.</p>
      </div>

      <div class="grid lg:grid-cols-3 gap-4">
        <aside class="space-y-2 lg:col-span-1">
          ${D.agents.map(a => {
            const usePct = pct(a.used, a.count);
            return html`
              <button class=${"w-full text-left lift glass rounded-xl p-3 border " + (open===a.slug ? "border-ev-gold/60 bg-ev-gold/5" : "border-white/5")}
                      onClick=${() => { setOpen(a.slug); history.replaceState(null,"","#"+a.slug); }}>
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-full bg-ev-gold/10 grid place-items-center font-bold text-xs gold flex-shrink-0">
                    ${a.name.split(" ").map(s=>s[0]).join("")}
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sm truncate">${a.name}</div>
                    <div class="text-[10px] text-ev-dim font-mono">${a.categories.length} categories · ${a.count} sources</div>
                  </div>
                  <div class="text-right">
                    <div class="font-mono gold text-sm">${a.count}</div>
                    <div class=${"text-[10px] font-mono " + (usePct < 5 ? "text-ev-red" : "text-ev-green")}>${usePct}%</div>
                  </div>
                </div>
              </button>`;
          })}
        </aside>

        <section class="lg:col-span-2 glass rounded-2xl p-6">
          ${cur && html`
            <div class="flex items-start justify-between mb-5">
              <div class="flex items-center gap-4">
                <div class="w-14 h-14 rounded-2xl bg-ev-gold/10 grid place-items-center font-bold gold border border-ev-gold/30">
                  ${cur.name.split(" ").map(s=>s[0]).join("")}
                </div>
                <div>
                  <h2 class="font-display text-2xl gold">${cur.name}</h2>
                  <div class="text-xs text-ev-dim mt-1">${cur.count} resources · ${cur.used} currently used (${pct(cur.used, cur.count)}%)</div>
                  <div class="text-[10px] text-ev-dim font-mono mt-1">manifest: .claude/agents/sources/${cur.slug}.md</div>
                </div>
              </div>
            </div>
            <div class="space-y-5">
              ${Object.entries(itemsByCat).sort((a,b) => b[1].length - a[1].length).map(([catName, catItems]) => html`
                <div>
                  <div class="flex items-center justify-between mb-2">
                    <h3 class="font-display text-lg gold">${catName}</h3>
                    <span class="font-mono text-xs gold">${catItems.length}</span>
                  </div>
                  <div class="space-y-1.5">
                    ${catItems.map(r => html`
                      <a href=${r.url} target="_blank" rel="noopener" class="block lift rounded-lg p-2.5 border border-white/5 hover:bg-ev-gold/5">
                        <div class="flex justify-between items-start gap-3">
                          <div class="min-w-0">
                            <span class="font-mono gold text-sm">${r.domain}</span>
                            <span class="text-xs text-ev-text/60 ml-2">${r.purpose}</span>
                          </div>
                          ${r.in_use && html`<span class="chip chip-green flex-shrink-0">USED</span>`}
                        </div>
                      </a>`)}
                  </div>
                </div>`)}
            </div>`}
        </section>
      </div>
    </main>
    <${Footer}/>`;
}

render(html`<${AgentsPage}/>`, document.getElementById("app"));
'''

# ============== AUDIT PAGE (two-axis: code-referenced + live-active) ==============
AUDIT = '''
import { html, render, h, D, fmt, pct, useLucide, Icon, Nav, Footer } from "./shared.js";

function AuditPage(){
  useLucide();
  const cats = [...D.categories].sort((a,b) => (b.live||0)*100/b.count - (a.live||0)*100/a.count);

  return html`
    <${Nav} active="audit"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="mb-6">
        <h1 class="font-display text-3xl gold gold-glow mb-1">Activation Audit</h1>
        <p class="text-sm text-ev-dim">
          Two axes: <span class="text-ev-cyan">code-referenced</span> (grep across workspace files) and
          <span class="text-ev-green">live-active</span> (HTTP-fetched + 2xx/3xx in last 30 days).
        </p>
      </div>

      <!-- Domain status breakdown -- visual split of the 745 -->
      ${D.meta.domain_status_breakdown && html`
        <div class="glass rounded-2xl p-6 mb-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-display text-xl gold">Domain status breakdown</h2>
            <span class="text-xs text-ev-dim font-mono">total: ${fmt(D.meta.total)}</span>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            ${[
              {key:"live", label:"Live", color:"green", icon:"check-circle"},
              {key:"auth_gated", label:"Auth-gated", color:"gold", icon:"lock"},
              {key:"rate_limited", label:"Rate-limited", color:"orange", icon:"clock"},
              {key:"dead", label:"Dead", color:"red", icon:"x-circle"},
              {key:"untested", label:"Untested", color:"dim", icon:"help-circle"},
            ].map(s => {
              const n = (D.meta.domain_status_breakdown||{})[s.key] || 0;
              return html`
                <div class="glass rounded-lg p-3 border" style=${"border-color:rgba(255,255,255,0.05)"}>
                  <div class="flex items-center gap-2 mb-1">
                    <${Icon} name=${s.icon} cls=${`w-3.5 h-3.5 text-ev-${s.color}`}/>
                    <span class="text-[10px] text-ev-dim uppercase tracking-widest">${s.label}</span>
                  </div>
                  <div class=${`text-xl font-mono font-bold text-ev-${s.color}`}>${fmt(n)}</div>
                </div>`;
            })}
          </div>
          <!-- horizontal stacked bar -->
          <div class="flex h-3 rounded overflow-hidden bg-white/5">
            ${(() => {
              const b = D.meta.domain_status_breakdown || {};
              const total = (b.live||0) + (b.auth_gated||0) + (b.rate_limited||0) + (b.dead||0) + (b.untested||0);
              if (!total) return null;
              return html`
                <div style=${`width:${(b.live||0)*100/total}%; background:#22c55e`} title=${"Live: " + (b.live||0)}></div>
                <div style=${`width:${(b.auth_gated||0)*100/total}%; background:#c9a84c`} title=${"Auth-gated: " + (b.auth_gated||0)}></div>
                <div style=${`width:${(b.rate_limited||0)*100/total}%; background:#f97316`} title=${"Rate-limited: " + (b.rate_limited||0)}></div>
                <div style=${`width:${(b.dead||0)*100/total}%; background:#dc2626`} title=${"Dead: " + (b.dead||0)}></div>
                <div style=${`width:${(b.untested||0)*100/total}%; background:#666`} title=${"Untested: " + (b.untested||0)}></div>`;
            })()}
          </div>
          <div class="text-[11px] text-ev-dim mt-2">
            Live = HTTP 200-399 within 30d. Auth-gated = 401/403 (alive but blocked). Dead = 404/410/5xx/timeout. Run <code class="font-mono gold">intel suite all</code> to re-test.
          </div>
        </div>`}

      <!-- KPI strip -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        ${[
          {label:"Live-active", value: fmt(D.meta.live_active||0), color: (D.meta.live_active_pct||0) < 15 ? "orange" : "green", icon:"zap"},
          {label:"Code-referenced", value: fmt(D.meta.in_use), color: "cyan", icon:"file-search"},
          {label:"Total catalogued", value: fmt(D.meta.total), color:"gold", icon:"database"},
          {label:"Cached articles", value: fmt(D.meta.articles_total||0), color:"purple", icon:"rss"},
        ].map(k => html`
          <div class="glass rounded-xl p-5">
            <div class=${`w-9 h-9 rounded-lg grid place-items-center bg-ev-${k.color}/10 border border-ev-${k.color}/30 mb-3`}>
              <${Icon} name=${k.icon} cls=${`w-4 h-4 text-ev-${k.color}`}/>
            </div>
            <div class=${`text-2xl font-mono font-bold text-ev-${k.color}`}>${k.value}</div>
            <div class="text-xs text-ev-dim mt-1">${k.label}</div>
          </div>`)}
      </div>

      <!-- Two-axis category bars -->
      <section class="glass rounded-2xl p-6 mb-6">
        <h2 class="font-display text-2xl gold mb-5">Activation by category</h2>
        <div class="text-[11px] text-ev-dim mb-4 flex items-center gap-4">
          <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-2 bg-ev-green rounded-sm"></span> live-active</span>
          <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-2 bg-ev-cyan rounded-sm"></span> code-referenced</span>
        </div>
        <div class="space-y-4">
          ${cats.map(c => {
            const livePct = pct(c.live||0, c.count);
            const codePct = pct(c.used||0, c.count);
            return html`
              <div>
                <div class="flex justify-between mb-1.5 text-sm items-center">
                  <span>${c.name}</span>
                  <span class="text-[11px] font-mono text-ev-dim">
                    <span class="text-ev-green">${c.live||0} live</span> ·
                    <span class="text-ev-cyan">${c.used||0} ref</span> ·
                    <span>${c.count} total</span>
                  </span>
                </div>
                <div class="relative h-3 bg-white/5 rounded-md overflow-hidden">
                  <div class="absolute inset-y-0 left-0 bg-ev-green/70 rounded-l" style=${"width:" + livePct + "%"}></div>
                  <div class="absolute inset-y-0 left-0 bg-ev-cyan/40 rounded-l border-r border-ev-cyan/60" style=${"width:" + codePct + "%; mix-blend-mode:screen"}></div>
                </div>
              </div>`;
          })}
        </div>
      </section>

      <!-- Most recently fetched live sources -->
      <section class="glass rounded-2xl p-6 mb-6">
        <h2 class="font-display text-2xl gold mb-5">Recently live-fetched (top ${Math.min(20, D.resources.filter(r=>r.live_active).length)})</h2>
        ${D.resources.filter(r=>r.live_active).length === 0
          ? html`<div class="text-sm text-ev-dim">No live activations yet -- run <code class="font-mono gold">intel suite all</code>.</div>`
          : html`
            <div class="grid md:grid-cols-2 gap-3">
              ${D.resources.filter(r=>r.live_active).sort((a,b)=> (b.live_count||0)-(a.live_count||0)).slice(0,20).map(r => html`
                <a href=${"./resource.html?d=" + r.domain} class="lift glass rounded-lg p-3 border border-white/5">
                  <div class="flex justify-between items-start mb-1">
                    <div class="font-mono gold text-sm">${r.domain}</div>
                    <div class="flex gap-1">
                      <span class="chip chip-green">${r.live_status||"?"}</span>
                      <span class="chip chip-cyan">${r.live_count||0}×</span>
                    </div>
                  </div>
                  <div class="text-xs text-ev-dim">${r.category} · ${r.agent_owner}</div>
                </a>`)}
            </div>`}
      </section>

      <!-- Top code-referenced (legacy audit) -->
      <section class="glass rounded-2xl p-6 mb-6">
        <h2 class="font-display text-2xl gold mb-5">Top code-referenced</h2>
        ${D.audit_top.length === 0
          ? html`<div class="text-sm text-ev-dim">No code audit yet -- run <span class="font-mono gold">intel audit</span>.</div>`
          : html`
            <div class="grid md:grid-cols-2 gap-3">
              ${D.audit_top.slice(0, 12).map(t => {
                const r = D.resources.find(x => x.domain === t.domain);
                return html`
                  <a href=${"./resource.html?d=" + t.domain} class="lift glass rounded-lg p-3 border border-white/5">
                    <div class="flex justify-between items-start mb-1">
                      <div class="font-mono gold text-sm">${t.domain}</div>
                      <span class="chip chip-cyan">${t.files} files</span>
                    </div>
                    ${r && html`<div class="text-xs text-ev-dim">${r.category} · ${r.agent_owner}</div>`}
                  </a>`;
              })}
            </div>`}
      </section>

      <section class="glass-gold rounded-2xl p-6">
        <h2 class="font-display text-2xl gold mb-3">CLI shortcuts</h2>
        <pre class="font-mono text-sm bg-black/30 rounded-lg p-3 border border-white/10 leading-relaxed overflow-x-auto"><span class="gold">$</span> intel suite all              <span class="text-ev-dim"># run every functional suite (~5-8 min)</span>
<span class="gold">$</span> intel suite news_brief       <span class="text-ev-dim"># pull every News & Journalism source</span>
<span class="gold">$</span> intel suite osint_sweep      <span class="text-ev-dim"># pull every OSINT source (~173 domains)</span>
<span class="gold">$</span> intel live-audit             <span class="text-ev-dim"># show live-active count + recent successes</span>
<span class="gold">$</span> intel investigate "Acme Corp" <span class="text-ev-dim"># OSINT investigation, streams to terminal</span></pre>
      </section>
    </main>
    <${Footer}/>`;
}

render(html`<${AuditPage}/>`, document.getElementById("app"));
'''

# ============== FEEDS PAGE ==============
FEEDS = '''
import { html, render, h, useState, D, fmt, useLucide, Icon, Nav, Footer, TOPIC_ICONS } from "./shared.js";

function FeedsPage(){
  useLucide();
  const hash = (location.hash || "").replace(/^#/, "");
  const [topic, setTopic] = useState(hash && D.fetchable_topics[hash] ? hash : "news");
  const cat = D.fetchable_topics[topic];
  const sources = D.resources.filter(r => r.category === cat);

  return html`
    <${Nav} active="feeds"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="mb-6">
        <h1 class="font-display text-3xl gold gold-glow mb-1">Live Feeds</h1>
        <p class="text-sm text-ev-dim">Source rosters for live-fetchable topics. Pull live data with <span class="font-mono gold">intel ${topic}</span> in the shell.</p>
      </div>

      <div class="flex flex-wrap gap-2 mb-6">
        ${Object.entries(D.fetchable_topics).map(([kw, c]) => html`
          <button class=${"pill-btn flex items-center gap-2 " + (topic===kw ? "on" : "")}
                  onClick=${() => { setTopic(kw); history.replaceState(null,"","#"+kw); }}>
            <${Icon} name=${TOPIC_ICONS[kw]||'rss'} cls="w-3.5 h-3.5"/>
            <span class="capitalize">${kw}</span>
            <span class="text-[10px] opacity-60">(${(D.categories.find(x=>x.name===c)||{count:0}).count})</span>
          </button>`)}
      </div>

      <div class="glass-gold rounded-2xl p-6 mb-6">
        <div class="flex items-center justify-between mb-3">
          <div>
            <div class="text-[10px] uppercase tracking-[.2em] text-ev-goldDim mb-1">Selected topic</div>
            <h2 class="font-display text-2xl gold capitalize">${topic} -- ${cat}</h2>
          </div>
          <div class="text-right">
            <div class="font-mono gold text-2xl">${sources.length}</div>
            <div class="text-[10px] text-ev-dim">sources</div>
          </div>
        </div>
        <pre class="font-mono text-sm text-ev-text/80 mt-4 bg-black/30 rounded-lg p-3 border border-white/10"><span class="gold">$</span> intel ${topic}    <span class="text-ev-dim"># pulls title + meta from each source in parallel</span></pre>
        <div class="text-xs text-ev-dim mt-2">
          Output goes to <span class="font-mono">06_DEVELOPMENT/everlight_os/intel_center/cache/fetch/</span> as JSON for downstream agents.
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-3">
        ${sources.map(r => html`
          <a href=${"./resource.html?d=" + r.domain} class="block lift glass rounded-xl p-4 border border-white/5">
            <div class="flex justify-between items-start gap-3 mb-2">
              <div class="min-w-0 flex-1">
                <div class="font-mono gold text-sm">${r.domain}</div>
                <div class="text-xs text-ev-text/70 mt-1">${r.purpose}</div>
              </div>
              <div class="flex flex-col items-end gap-1 flex-shrink-0">
                ${(r.article_count||0) > 0 && html`<span class="chip chip-cyan">${r.article_count} cached</span>`}
                ${r.in_use && html`<span class="chip chip-green">USED</span>`}
                ${r.verified_status === "checked" && html`<span class="chip chip-cyan">CURATED</span>`}
              </div>
            </div>
            <div class="text-[10px] text-ev-dim font-mono">owner: ${r.agent_owner}</div>
          </a>`)}
      </div>
    </main>
    <${Footer}/>`;
}

render(html`<${FeedsPage}/>`, document.getElementById("app"));
'''

# ============== ARTICLES PAGE (magazine layout) ==============
ARTICLES = '''
import { html, render, h, useState, useMemo, D, fmt, useLucide, Icon, Nav, Footer,
         relTime, readingTimeMin, inferSentiment, inferTopic, topicColor,
         accentForCategory, highlight, bucketByTime } from "./shared.js";

function ArticlesPage(){
  useLucide();
  const [q, setQ] = useState("");
  const [src, setSrc] = useState("ALL");
  const [topic, setTopic] = useState("ALL");
  const [expanded, setExpanded] = useState(new Set());
  const [view, setView] = useState("magazine");  // magazine | list

  // Flatten all cached articles across resources
  const all = useMemo(() => {
    const out = [];
    for (const r of D.resources) {
      for (const a of (r.articles||[])) {
        const text = (a.title||"") + " " + (a.summary||"");
        out.push({
          ...a,
          domain: r.domain, category: r.category, agent_owner: r.agent_owner,
          accent: accentForCategory(r.category),
          topic: inferTopic(text),
          sentiment: inferSentiment(text),
          readMin: readingTimeMin(a.summary||""),
        });
      }
    }
    out.sort((a,b) => {
      const ta = new Date(a.published || a.fetched_at || 0).getTime();
      const tb = new Date(b.published || b.fetched_at || 0).getTime();
      return tb - ta;
    });
    return out;
  }, []);

  const sources = useMemo(() => {
    const s = {};
    for (const a of all) s[a.domain] = (s[a.domain]||0) + 1;
    return [["ALL", all.length], ...Object.entries(s).sort((x,y)=>y[1]-x[1])];
  }, [all]);

  const topics = useMemo(() => {
    const t = {};
    for (const a of all) t[a.topic] = (t[a.topic]||0) + 1;
    return [["ALL", all.length], ...Object.entries(t).sort((x,y)=>y[1]-x[1])];
  }, [all]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return all.filter(a => {
      if (src !== "ALL" && a.domain !== src) return false;
      if (topic !== "ALL" && a.topic !== topic) return false;
      if (!needle) return true;
      return ((a.title||"") + " " + (a.summary||"")).toLowerCase().includes(needle);
    });
  }, [all, q, src, topic]);

  const featured = filtered[0];
  const grid = filtered.slice(1, 200);
  const buckets = bucketByTime(grid);

  function toggleExpand(id){
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const SENT_BADGE = {
    pos: { cls: "chip-green", icon: "trending-up", label: "positive" },
    neg: { cls: "chip-red",   icon: "trending-down", label: "alert" },
    neu: { cls: "chip-gold",  icon: "minus",  label: "neutral" },
  };

  function inferTarget(article){
    // Used by "investigate this" -- pick a likely entity from the title
    const t = article.title || "";
    const cap = t.match(/[A-Z][a-zA-Z]+(?:\\s+[A-Z][a-zA-Z]+){1,3}/);
    return cap ? cap[0] : article.domain;
  }

  const ArticleCard = ({a, hero=false}) => {
    const id = a.url || (a.title + a.fetched_at);
    const isOpen = expanded.has(id);
    const Sent = SENT_BADGE[a.sentiment] || SENT_BADGE.neu;
    return html`
      <article class=${"flex glass rounded-2xl overflow-hidden lift border border-white/5 " + (hero ? "" : "")}>
        <div style=${"width:4px;background:" + a.accent + ";flex-shrink:0"}></div>
        <div class="flex-1 p-5 min-w-0">
          <div class="flex items-start justify-between gap-3 mb-2">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="chip chip-gold">${a.domain}</span>
              <span class=${"chip chip-" + topicColor(a.topic)}>${a.topic}</span>
              <span class=${"chip " + Sent.cls + " flex items-center gap-1"}>
                <${Icon} name=${Sent.icon} cls="w-3 h-3"/> ${Sent.label}
              </span>
            </div>
            <div class="text-[10px] text-ev-dim font-mono whitespace-nowrap">${relTime(a.published || a.fetched_at)}</div>
          </div>

          <h3 class=${"font-display text-ev-text leading-snug mb-2 " + (hero ? "text-3xl" : "text-lg")}>
            ${highlight(a.title || "(untitled)", q)}
          </h3>

          ${a.summary && html`
            <p class=${"text-ev-text/75 leading-relaxed " + (isOpen ? "" : (hero ? "text-base" : "text-sm line-clamp-3"))} style=${isOpen ? "" : (hero ? "" : "display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden")}>
              ${highlight(a.summary, q)}
            </p>`}

          <div class="flex items-center gap-3 mt-3 pt-3 border-t border-white/5 text-[11px]">
            <span class="text-ev-dim flex items-center gap-1">
              <${Icon} name="clock" cls="w-3 h-3"/> ${a.readMin} min read
            </span>
            <span class="text-ev-dim">·</span>
            <span class="text-ev-dim">${a.agent_owner}</span>
            <div class="ml-auto flex items-center gap-1.5">
              ${a.summary && a.summary.length > 100 && html`
                <button onClick=${(e) => { e.preventDefault(); toggleExpand(id); }}
                        class="px-2 py-1 rounded text-ev-dim hover:text-ev-gold hover:bg-white/5 text-[11px]">
                  ${isOpen ? "Less" : "More"}
                </button>`}
              <a href=${"http://localhost:2301/?target=" + encodeURIComponent(inferTarget(a))} target="_blank" rel="noopener"
                 class="px-2 py-1 rounded bg-ev-purple/10 hover:bg-ev-purple/20 text-ev-purple flex items-center gap-1 text-[11px]">
                <${Icon} name="search-code" cls="w-3 h-3"/> Investigate
              </a>
              ${a.url && html`
                <a href=${a.url} target="_blank" rel="noopener"
                   class="px-2 py-1 rounded bg-ev-gold/10 hover:bg-ev-gold/20 gold flex items-center gap-1 text-[11px]">
                  <${Icon} name="external-link" cls="w-3 h-3"/> Open
                </a>`}
            </div>
          </div>
        </div>
      </article>`;
  };

  const TimeBucket = ({label, items}) => items.length > 0 && html`
    <section class="mb-8">
      <div class="flex items-center gap-3 mb-3">
        <div class="h-px flex-1 bg-gradient-to-r from-ev-gold/40 to-transparent"></div>
        <h2 class="text-[11px] uppercase tracking-[.22em] gold font-bold">${label}</h2>
        <span class="text-[10px] text-ev-dim font-mono">${items.length}</span>
        <div class="h-px flex-1 bg-gradient-to-l from-ev-gold/40 to-transparent"></div>
      </div>
      <div class="grid md:grid-cols-2 gap-4">
        ${items.map(a => html`<${ArticleCard} a=${a}/>`)}
      </div>
    </section>`;

  return html`
    <${Nav} active="articles"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">

      <!-- Header strip -->
      <div class="flex items-end justify-between mb-6 gap-4 flex-wrap">
        <div>
          <h1 class="font-display text-4xl gold gold-glow mb-1">The Brief</h1>
          <p class="text-sm text-ev-dim">${fmt(all.length)} live articles across ${sources.length-1} sources, auto-tagged by topic + sentiment.</p>
        </div>
        <div class="text-right">
          <div class="text-[10px] uppercase tracking-widest text-ev-dim">Refresh</div>
          <code class="text-xs gold font-mono">intel pull-all news</code>
        </div>
      </div>

      <!-- Search + topic strip -->
      <div class="glass rounded-2xl p-4 mb-5 space-y-3">
        <div class="relative">
          <${Icon} name="search" cls="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ev-dim"/>
          <input class="search font-mono text-sm"
                 placeholder="Search 730 sources, 200+ articles..."
                 value=${q} onInput=${e => setQ(e.target.value)}/>
        </div>
        <div class="flex flex-wrap gap-1.5 items-center">
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-1">Topic</span>
          ${topics.slice(0, 11).map(([t,n]) => html`
            <button class=${"pill-btn text-xs " + (topic === t ? "on" : "")} onClick=${() => setTopic(t)}>
              ${t === "ALL" ? "All" : t} <span class="opacity-50">(${n})</span>
            </button>`)}
        </div>
      </div>

      <!-- Source ribbon (sticky) -->
      <div class="glass rounded-2xl p-3 mb-6 -mx-1 px-3 sticky top-0 z-30 backdrop-blur">
        <div class="flex items-center gap-2 overflow-x-auto pb-1">
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-1 flex-shrink-0">Sources</span>
          ${sources.slice(0, 30).map(([d,n]) => html`
            <button class=${"pill-btn text-xs whitespace-nowrap " + (src===d ? "on" : "")} onClick=${() => setSrc(d)}>
              ${d==="ALL"?"All":d} <span class="opacity-50">${n}</span>
            </button>`)}
        </div>
      </div>

      <!-- Featured hero -->
      ${featured && html`
        <section class="mb-8">
          <div class="text-[11px] uppercase tracking-[.22em] gold font-bold mb-3">★ Featured</div>
          <${ArticleCard} a=${featured} hero=${true}/>
        </section>`}

      <!-- Time-grouped sections -->
      ${filtered.length > 1 ? html`
        <${TimeBucket} label="Today"     items=${buckets.today}/>
        <${TimeBucket} label="This week" items=${buckets.week}/>
        <${TimeBucket} label="Earlier"   items=${buckets.earlier}/>
      ` : html`
        <div class="glass rounded-xl p-12 text-center text-sm text-ev-dim">
          ${all.length === 0 ? html`No articles cached yet. Pull some: <code class="font-mono gold">intel pull-all news</code>` :
                                "No matches for these filters."}
        </div>`}

      ${filtered.length === 0 && all.length > 0 && html`
        <div class="glass rounded-xl p-8 text-center text-sm text-ev-dim">
          No matches. Try clearing the source/topic filter.
        </div>`}
    </main>
    <${Footer}/>`;
}

render(html`<${ArticlesPage}/>`, document.getElementById("app"));
'''

# ============== RESOURCE DETAIL PAGE ==============
RESOURCE = '''
import { html, render, h, useState, useMemo, D, fmt, useLucide, Icon, Nav, Footer } from "./shared.js";

function ResourcePage(){
  useLucide();
  const params = new URLSearchParams(location.search);
  const dParam = (params.get("d") || "").toLowerCase();
  const idParam = params.get("id");
  const r = D.resources.find(x => x.domain === dParam || x.id === idParam) || D.resources[0];

  if (!r) return html`<${Nav}/><main class="max-w-7xl mx-auto px-5 pt-8"><div class="glass rounded-xl p-8">Resource not found.</div></main><${Footer}/>`;

  const related = D.resources
    .filter(x => x.category === r.category && x.domain !== r.domain)
    .slice(0, 6);
  const setupLines = (r.setup_steps || "").split("\\n").filter(Boolean);

  return html`
    <${Nav} active="resources"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="text-xs text-ev-dim mb-3">
        <a href="./resources.html" class="hover:text-ev-gold">Resources</a>
        <span class="mx-1">/</span>
        <a href=${"./categories.html#" + encodeURIComponent(r.category)} class="hover:text-ev-gold">${r.category}</a>
        <span class="mx-1">/</span>
        <span class="font-mono">${r.domain}</span>
      </div>

      <!-- Hero -->
      <section class="glass-gold rounded-2xl p-7 mb-6 relative overflow-hidden">
        <div class="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-ev-gold/10 blur-3xl"></div>
        <div class="text-[11px] uppercase tracking-[.22em] text-ev-goldDim mb-2">${r.department}</div>
        <h1 class="font-display text-4xl gold gold-glow leading-tight">${r.name}</h1>
        <a href=${r.url} target="_blank" rel="noopener" class="font-mono text-lg gold hover:underline mt-1 inline-block">${r.domain}</a>
        <p class="text-ev-text/80 mt-3">${r.purpose}</p>
        <div class="flex flex-wrap gap-2 mt-4">
          <span class="chip chip-gold">${r.category}</span>
          ${r.in_use && html`<span class="chip chip-green">USED IN WORKSPACE</span>`}
          ${r.verified_status === "checked" && html`<span class="chip chip-cyan">CURATED</span>`}
          ${r.verified_status === "unverified" && html`<span class="chip chip-red">REVIEW</span>`}
          <span class="chip chip-cyan">${r.article_count || 0} cached items</span>
        </div>
        <div class="mt-5 flex flex-wrap gap-3 text-sm">
          <a href=${r.url} target="_blank" rel="noopener" class="px-4 py-2 rounded-lg bg-ev-gold/10 border border-ev-gold/40 hover:bg-ev-gold/20 transition gold flex items-center gap-2">
            <${Icon} name="external-link" cls="w-4 h-4"/> Open ${r.domain}
          </a>
          <button onClick=${() => navigator.clipboard?.writeText(`intel pull ${r.domain}`)} class="px-4 py-2 rounded-lg glass border border-white/10 hover:border-ev-gold/40 transition flex items-center gap-2">
            <${Icon} name="copy" cls="w-4 h-4"/> Copy `intel pull` command
          </button>
        </div>
      </section>

      <div class="grid lg:grid-cols-3 gap-6">
        <!-- LEFT: Use case + setup -->
        <div class="lg:col-span-2 space-y-6">
          ${r.use_case && html`
            <section class="glass rounded-2xl p-6">
              <div class="flex items-center gap-3 mb-3">
                <div class="w-9 h-9 rounded-lg bg-ev-purple/10 border border-ev-purple/30 grid place-items-center">
                  <${Icon} name="target" cls="w-4 h-4 text-ev-purple"/>
                </div>
                <h2 class="font-display text-2xl gold">Use case</h2>
              </div>
              <p class="text-ev-text/85 leading-relaxed">${r.use_case}</p>
            </section>`}

          ${setupLines.length > 0 && html`
            <section class="glass rounded-2xl p-6">
              <div class="flex items-center gap-3 mb-3">
                <div class="w-9 h-9 rounded-lg bg-ev-cyan/10 border border-ev-cyan/30 grid place-items-center">
                  <${Icon} name="list-checks" cls="w-4 h-4 text-ev-cyan"/>
                </div>
                <h2 class="font-display text-2xl gold">Setup</h2>
              </div>
              <ol class="space-y-2 list-decimal list-inside text-sm text-ev-text/80">
                ${setupLines.map(line => html`<li>${line.replace(/^\\d+\\.\\s*/, "")}</li>`)}
              </ol>
            </section>`}

          <!-- Latest cached articles -->
          <section class="glass rounded-2xl p-6">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-lg bg-ev-gold/10 border border-ev-gold/30 grid place-items-center">
                  <${Icon} name="rss" cls="w-4 h-4 gold"/>
                </div>
                <h2 class="font-display text-2xl gold">Latest items</h2>
              </div>
              <span class="font-mono text-xs gold">${r.article_count || 0}</span>
            </div>
            ${(r.articles || []).length === 0
              ? html`
                <div class="text-sm text-ev-dim">
                  No cached items yet. Pull live with:
                  <pre class="font-mono text-sm bg-black/40 rounded-lg p-3 mt-3 border border-white/10"><span class="gold">$</span> intel pull ${r.domain}</pre>
                </div>`
              : html`
                <div class="space-y-3">
                  ${(r.articles || []).map(a => html`
                    <a href=${a.url} target="_blank" rel="noopener" class="block lift rounded-lg p-3 border border-white/5 hover:bg-ev-gold/5">
                      <div class="font-medium text-sm text-ev-text">${a.title}</div>
                      ${a.summary && html`<div class="text-xs text-ev-text/60 mt-1">${a.summary.slice(0,200)}</div>`}
                      <div class="flex gap-3 mt-1 text-[11px] text-ev-dim">
                        ${a.published && html`<span>${a.published}</span>`}
                        ${a.fetched_at && html`<span>· cached ${a.fetched_at.slice(0,16)}</span>`}
                      </div>
                    </a>`)}
                </div>`}
          </section>
        </div>

        <!-- RIGHT: Owner card + related -->
        <aside class="space-y-5">
          <section class="glass rounded-2xl p-5">
            <div class="text-[10px] uppercase tracking-[.2em] text-ev-dim mb-2">Owned by</div>
            <a href=${"./agents.html#" + r.agent_owner.toLowerCase().replace(/[^a-z0-9]+/g,'_')}
               class="flex items-center gap-3 lift rounded-lg p-2 -mx-2">
              <div class="w-12 h-12 rounded-full bg-ev-gold/10 grid place-items-center font-bold gold border border-ev-gold/30">
                ${r.agent_owner.split(" ").map(s=>s[0]).join("")}
              </div>
              <div>
                <div class="font-medium gold">${r.agent_owner}</div>
                <div class="text-[11px] text-ev-dim">${r.department}</div>
              </div>
            </a>
            <div class="mt-3 text-[11px] text-ev-dim">
              <div>ID: <span class="font-mono">${r.id}</span></div>
              <div>Status: <span class="font-mono">${r.verified_status}</span></div>
              <div>Last checked: <span class="font-mono">${r.last_checked || "n/a"}</span></div>
            </div>
          </section>

          <section class="glass rounded-2xl p-5">
            <div class="text-[10px] uppercase tracking-[.2em] text-ev-dim mb-3">Shell commands</div>
            <pre class="font-mono text-xs bg-black/30 rounded p-3 border border-white/10 leading-relaxed overflow-x-auto"><span class="gold">$</span> intel show ${r.domain}
<span class="gold">$</span> intel pull ${r.domain}
<span class="gold">$</span> intel cat "${r.category}"</pre>
          </section>

          ${related.length > 0 && html`
            <section class="glass rounded-2xl p-5">
              <div class="text-[10px] uppercase tracking-[.2em] text-ev-dim mb-3">Related in ${r.category}</div>
              <div class="space-y-1.5">
                ${related.map(x => html`
                  <a href=${"./resource.html?d=" + x.domain} class="block lift rounded p-2 border border-white/5 text-sm">
                    <span class="font-mono gold">${x.domain}</span>
                    <span class="text-xs text-ev-text/60 ml-2">${x.purpose.slice(0, 60)}</span>
                  </a>`)}
              </div>
            </section>`}

          ${r.in_use && r.evidence && html`
            <section class="glass rounded-2xl p-5">
              <div class="text-[10px] uppercase tracking-[.2em] text-ev-dim mb-2">Already used in</div>
              <div class="space-y-1 text-[11px] font-mono text-ev-text/70">
                ${r.evidence.split("; ").map(f => html`<div>→ ${f}</div>`)}
              </div>
            </section>`}
        </aside>
      </div>
    </main>
    <${Footer}/>`;
}

render(html`<${ResourcePage}/>`, document.getElementById("app"));
'''

# ============== USAGE PAGE -- team telemetry ==============
USAGE = '''
import { html, render, h, D, fmt, useLucide, Icon, Nav, Footer } from "./shared.js";

function UsagePage(){
  useLucide();
  const u = D.usage || {investigations:{}, pulls:{}, leads:{}};
  const inv = u.investigations || {}; const pulls = u.pulls || {}; const leads = u.leads || {};
  const trigEntries = Object.entries(inv.by_trigger || {}).sort((a,b)=>b[1]-a[1]);
  const pullTrigEntries = Object.entries(pulls.by_trigger || {}).sort((a,b)=>b[1]-a[1]).slice(0,10);
  const timeline = pulls.timeline_24h || {};
  const maxV = Math.max(...Object.values(timeline), 1);
  const sortedBuckets = Object.entries(timeline).sort();

  return html`
    <${Nav} active="usage"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="mb-6">
        <h1 class="font-display text-3xl gold gold-glow mb-1">Team Usage Telemetry</h1>
        <p class="text-sm text-ev-dim">Who triggered what, when. From <span class="font-mono">cache/investigations.sqlite</span> + <span class="font-mono">cache/live_log.sqlite</span> + <span class="font-mono">Wholesale/leads_db.sqlite</span>.</p>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        ${[
          {label:"Investigations · total", value: fmt(inv.total||0), color:"gold", icon:"search"},
          {label:"Investigations · last 7d", value: fmt(inv.last_7d||0), color:"cyan", icon:"calendar"},
          {label:"Live pulls · total domains", value: fmt(pulls.total||0), color:"purple", icon:"radar"},
          {label:"Leads enriched", value: (leads.enriched||0) + ' / ' + (leads.total||0), color: (leads.enriched||0)>0?'green':'orange', icon:"users"},
        ].map(k => html`
          <div class="glass rounded-xl p-5">
            <div class=${`w-9 h-9 rounded-lg grid place-items-center bg-ev-${k.color}/10 border border-ev-${k.color}/30 mb-3`}>
              <${Icon} name=${k.icon} cls=${`w-4 h-4 text-ev-${k.color}`}/>
            </div>
            <div class=${`text-2xl font-mono font-bold text-ev-${k.color}`}>${k.value}</div>
            <div class="text-xs text-ev-dim mt-1">${k.label}</div>
          </div>`)}
      </div>

      <section class="glass rounded-2xl p-6 mb-6">
        <h2 class="font-display text-2xl gold mb-5">24h activity timeline · live pulls per hour</h2>
        ${sortedBuckets.length === 0
          ? html`<div class="text-sm text-ev-dim">No activity in the last 24h. Run <code class="font-mono gold">intel suite all</code> to populate.</div>`
          : html`<div class="overflow-x-auto whitespace-nowrap">
              ${sortedBuckets.map(([bucket, count]) => {
                const h = (count / maxV) * 100;
                return html`<div class="inline-block w-12 text-center mx-0.5 align-bottom">
                  <div class="h-32 flex items-end justify-center">
                    <div class="w-6 rounded-t" style=${"background:linear-gradient(180deg,#c9a84c,#a0832e);height:" + h + "%"} title=${count + " pulls"}></div>
                  </div>
                  <div class="text-[9px] text-ev-dim font-mono mt-1">${bucket}</div>
                  <div class="text-[10px] gold font-mono font-bold">${count}</div>
                </div>`;
              })}
            </div>`}
      </section>

      <div class="grid lg:grid-cols-2 gap-6 mb-6">
        <section class="glass rounded-2xl p-6">
          <h2 class="font-display text-2xl gold mb-5">Investigations by trigger</h2>
          ${trigEntries.length === 0
            ? html`<div class="text-sm text-ev-dim">No investigations yet.</div>`
            : html`<div class="space-y-2">
                ${trigEntries.map(([trig, n]) => html`
                  <div class="flex items-center justify-between p-3 rounded glass border border-white/5">
                    <span class="font-mono text-sm ${trig === '(legacy)' ? 'text-ev-dim' : 'gold'}">${trig}</span>
                    <span class="font-mono font-bold text-ev-gold">${n}</span>
                  </div>`)}
              </div>`}
        </section>

        <section class="glass rounded-2xl p-6">
          <h2 class="font-display text-2xl gold mb-5">Live pulls by trigger</h2>
          ${pullTrigEntries.length === 0
            ? html`<div class="text-sm text-ev-dim">No pulls logged.</div>`
            : html`<div class="space-y-2">
                ${pullTrigEntries.map(([trig, n]) => html`
                  <div class="flex items-center justify-between p-3 rounded glass border border-white/5">
                    <span class="font-mono text-sm ${trig === '(legacy)' || trig === 'unknown' ? 'text-ev-dim' : 'gold'}">${trig}</span>
                    <span class="font-mono font-bold text-ev-cyan">${n}</span>
                  </div>`)}
              </div>`}
        </section>
      </div>

      <section class="glass rounded-2xl p-6 mb-6">
        <h2 class="font-display text-2xl gold mb-5">Top investigated targets</h2>
        ${(inv.top_targets || []).length === 0
          ? html`<div class="text-sm text-ev-dim">No targets yet.</div>`
          : html`<table class="intel">
              <thead><tr><th>Target</th><th class="num">Investigations</th></tr></thead>
              <tbody>
                ${(inv.top_targets || []).map(t => html`
                  <tr><td class="font-mono">${t.target}</td><td class="num">${t.count}</td></tr>`)}
              </tbody></table>`}
      </section>

      <section class="glass-gold rounded-2xl p-6">
        <h2 class="font-display text-2xl gold mb-3">Operator's view</h2>
        <p class="text-sm text-ev-text/80 mb-3">
          Generate a full branded HTML usage report any time:
        </p>
        <pre class="font-mono text-sm bg-black/30 rounded-lg p-3 border border-white/10 leading-relaxed overflow-x-auto"><span class="gold">$</span> intel team-usage</pre>
      </section>
    </main>
    <${Footer}/>`;
}

render(html`<${UsagePage}/>`, document.getElementById("app"));
'''

# ============== CLIENTS PAGE -- per-target investigation ledger ==============
CLIENTS = '''
import { html, render, h, useState, useMemo, D, fmt, useLucide, Icon, Nav, Footer, relTime } from "./shared.js";

function ClientsPage(){
  useLucide();
  const all = D.clients || [];
  const [tab, setTab] = useState("people");      // people | addresses
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");   // all | dnc | verified

  const tabbed = useMemo(() => {
    return all.filter(c => {
      const isAddr = c.kind === "address";
      if (tab === "people"    && isAddr) return false;
      if (tab === "addresses" && !isAddr) return false;
      return true;
    });
  }, [all, tab]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return tabbed.filter(c => {
      if (filter === "dnc" && !c.dnc_blocked) return false;
      if (filter === "verified" && !(c.verified_findings > 0)) return false;
      if (!needle) return true;
      return ((c.target||"") + " " + (c.state||"") + " " + (c.id||"")).toLowerCase().includes(needle);
    });
  }, [tabbed, q, filter]);

  const peopleCount = all.filter(c => c.kind !== "address").length;
  const addrCount   = all.filter(c => c.kind === "address").length;

  const Row = ({c}) => html`
    <div class="glass rounded-xl border border-white/5 lift p-4 flex items-center gap-3 flex-wrap">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap mb-1">
          <span class="font-mono gold text-base">${c.target}</span>
          ${c.state && html`<span class="chip chip-cyan">${c.state}</span>`}
          ${c.dnc_blocked && html`<span class="chip chip-red">DNC BLOCKED</span>`}
          <span class="chip chip-gold">${c.kind}</span>
        </div>
        <div class="text-[11px] text-ev-dim font-mono flex items-center gap-3 flex-wrap">
          <span><${Icon} name="search" cls="w-3 h-3 inline -mt-0.5"/> ${c.investigation_count} investigation${c.investigation_count===1?"":"s"}</span>
          <span>·</span>
          <span><${Icon} name="clock" cls="w-3 h-3 inline -mt-0.5"/> last ${relTime(c.last_seen)}</span>
          <span>·</span>
          ${c.verified_findings > 0
            ? html`<span class="text-ev-green">${c.verified_findings} verified</span>`
            : html`<span class="text-ev-dim">0 verified</span>`}
          <span class="text-ev-dim">/ ${c.raw_findings} raw</span>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        <a href=${c.report_url} target="_blank" rel="noopener"
           class="px-3 py-2 rounded-lg bg-ev-gold/10 hover:bg-ev-gold/20 border border-ev-gold/30 gold flex items-center gap-2 text-xs">
          <${Icon} name="file-text" cls="w-3.5 h-3.5"/> Open Report
        </a>
      </div>
    </div>`;

  return html`
    <${Nav} active="clients"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="mb-6">
        <h1 class="font-display text-3xl gold gold-glow mb-1">Clients & Targets</h1>
        <p class="text-sm text-ev-dim">Every target ever investigated, grouped by latest investigation. Source: <span class="font-mono">cache/investigations.sqlite</span>.</p>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        ${[
          {label:"Total targets", value: fmt(all.length), color:"gold", icon:"users"},
          {label:"People", value: fmt(peopleCount), color:"cyan", icon:"user"},
          {label:"Addresses", value: fmt(addrCount), color:"purple", icon:"map-pin"},
          {label:"DNC blocked", value: fmt(all.filter(c=>c.dnc_blocked).length), color: all.filter(c=>c.dnc_blocked).length>0?"red":"green", icon:"shield-x"},
        ].map(k => html`
          <div class="glass rounded-xl p-5">
            <div class=${`w-9 h-9 rounded-lg grid place-items-center bg-ev-${k.color}/10 border border-ev-${k.color}/30 mb-3`}>
              <${Icon} name=${k.icon} cls=${`w-4 h-4 text-ev-${k.color}`}/>
            </div>
            <div class=${`text-2xl font-mono font-bold text-ev-${k.color}`}>${k.value}</div>
            <div class="text-xs text-ev-dim mt-1">${k.label}</div>
          </div>`)}
      </div>

      <div class="glass rounded-2xl p-4 mb-5 space-y-3">
        <div class="flex flex-wrap gap-2 items-center">
          <button class=${"pill-btn " + (tab==="people" ? "on" : "")} onClick=${() => setTab("people")}>
            People <span class="opacity-60">(${peopleCount})</span>
          </button>
          <button class=${"pill-btn " + (tab==="addresses" ? "on" : "")} onClick=${() => setTab("addresses")}>
            Addresses <span class="opacity-60">(${addrCount})</span>
          </button>
        </div>
        <div class="relative">
          <${Icon} name="search" cls="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ev-dim"/>
          <input class="search font-mono text-sm"
                 placeholder="Search target name, state, investigation id..."
                 value=${q} onInput=${e => setQ(e.target.value)}/>
        </div>
        <div class="flex flex-wrap gap-2 items-center">
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-2">Filter</span>
          <button class=${"pill-btn " + (filter==="all" ? "on" : "")} onClick=${() => setFilter("all")}>All</button>
          <button class=${"pill-btn " + (filter==="verified" ? "on" : "")} onClick=${() => setFilter("verified")}>Has verified intel</button>
          <button class=${"pill-btn " + (filter==="dnc" ? "on" : "")} onClick=${() => setFilter("dnc")}>DNC blocked</button>
        </div>
      </div>

      <div class="text-xs text-ev-dim mb-3 font-mono">${fmt(filtered.length)} of ${fmt(tabbed.length)} ${tab}</div>

      ${filtered.length === 0
        ? html`<div class="glass rounded-2xl p-12 text-center">
            <${Icon} name="search-x" cls="w-10 h-10 text-ev-dim mx-auto mb-3"/>
            <div class="text-sm text-ev-dim">
              ${all.length === 0
                ? html`No investigations yet. Run <code class="font-mono gold">intel investigate "Some Target"</code> to populate.`
                : "No targets match these filters. Try clearing the search or filter."}
            </div>
          </div>`
        : html`<div class="space-y-2">
            ${filtered.map(c => html`<${Row} c=${c}/>`)}
          </div>`}
    </main>
    <${Footer}/>`;
}

render(html`<${ClientsPage}/>`, document.getElementById("app"));
'''

# ============== REPORTS SEARCH PAGE -- one row per investigation ==============
REPORTS = '''
import { html, render, h, useState, useMemo, D, fmt, useLucide, Icon, Nav, Footer, relTime } from "./shared.js";

function ReportsPage(){
  useLucide();
  const [q, setQ] = useState("");
  const [kindFilter, setKindFilter] = useState("ALL");
  const [stateFilter, setStateFilter] = useState("ALL");
  const [showDnc, setShowDnc] = useState("ALL");  // ALL | DNC | NON_DNC
  const [showVerified, setShowVerified] = useState("ALL");  // ALL | VERIFIED | RAW

  const reports = D.reports || [];

  const kinds = useMemo(() => ["ALL", ...Array.from(new Set(reports.map(r => r.kind))).sort()], [reports]);
  const states = useMemo(() => ["ALL", ...Array.from(new Set(reports.map(r => r.state).filter(Boolean))).sort()], [reports]);
  const triggers = useMemo(() => ["ALL", ...Array.from(new Set(reports.map(r => r.triggered_by))).sort()], [reports]);
  const [triggerFilter, setTriggerFilter] = useState("ALL");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return reports.filter(r => {
      if (kindFilter !== "ALL" && r.kind !== kindFilter) return false;
      if (stateFilter !== "ALL" && r.state !== stateFilter) return false;
      if (triggerFilter !== "ALL" && r.triggered_by !== triggerFilter) return false;
      if (showDnc === "DNC" && !r.dnc_blocked) return false;
      if (showDnc === "NON_DNC" && r.dnc_blocked) return false;
      if (showVerified === "VERIFIED" && (r.verified_findings||0) === 0) return false;
      if (showVerified === "RAW" && (r.verified_findings||0) > 0) return false;
      if (!needle) return true;
      const hay = (r.target + " " + r.business_purpose + " " + r.kind + " " +
                    r.state + " " + r.triggered_by + " " + r.id).toLowerCase();
      return hay.includes(needle);
    });
  }, [q, kindFilter, stateFilter, triggerFilter, showDnc, showVerified, reports]);

  return html`
    <${Nav} active="reports"/>
    <main class="max-w-7xl mx-auto px-5 pt-8 pb-20">
      <div class="mb-6">
        <h1 class="font-display text-3xl gold gold-glow mb-1">Investigation Reports</h1>
        <p class="text-sm text-ev-dim">${fmt(reports.length)} total investigations. Searchable by target, purpose, state, agent who ran it, or investigation ID.</p>
      </div>

      <!-- KPI strip -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        ${[
          {label:"Total reports", value: fmt(reports.length), color:"gold", icon:"file-search"},
          {label:"With verified intel", value: reports.filter(r => (r.verified_findings||0) > 0).length, color:"green", icon:"check-circle"},
          {label:"DNC blocked", value: reports.filter(r => r.dnc_blocked).length, color:"red", icon:"ban"},
          {label:"Distinct targets", value: new Set(reports.map(r => r.target.toLowerCase())).size, color:"cyan", icon:"users"},
        ].map(k => html`
          <div class="glass rounded-xl p-5">
            <div class=${`w-9 h-9 rounded-lg grid place-items-center bg-ev-${k.color}/10 border border-ev-${k.color}/30 mb-3`}>
              <${Icon} name=${k.icon} cls=${`w-4 h-4 text-ev-${k.color}`}/>
            </div>
            <div class=${`text-2xl font-mono font-bold text-ev-${k.color}`}>${k.value}</div>
            <div class="text-xs text-ev-dim mt-1">${k.label}</div>
          </div>`)}
      </div>

      <!-- Filters -->
      <div class="glass rounded-2xl p-5 mb-6 space-y-3">
        <div class="relative">
          <${Icon} name="search" cls="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ev-dim"/>
          <input class="search font-mono"
                 placeholder="Search target, purpose, state, triggered_by, investigation_id..."
                 value=${q} onInput=${e => setQ(e.target.value)}/>
        </div>
        <div class="flex flex-wrap gap-2 items-center">
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-1">Kind</span>
          ${kinds.slice(0, 8).map(k => html`
            <button class=${"pill-btn " + (kindFilter===k ? "on" : "")} onClick=${() => setKindFilter(k)}>${k}</button>`)}
        </div>
        ${states.length > 1 && html`
          <div class="flex flex-wrap gap-2 items-center">
            <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-1">State</span>
            ${states.slice(0, 12).map(s => html`
              <button class=${"pill-btn " + (stateFilter===s ? "on" : "")} onClick=${() => setStateFilter(s)}>${s}</button>`)}
          </div>`}
        <div class="flex flex-wrap gap-2 items-center">
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-1">Triggered by</span>
          ${triggers.slice(0, 8).map(t => html`
            <button class=${"pill-btn " + (triggerFilter===t ? "on" : "")} onClick=${() => setTriggerFilter(t)}>${t}</button>`)}
        </div>
        <div class="flex flex-wrap gap-2 items-center">
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-1">DNC</span>
          ${["ALL","DNC","NON_DNC"].map(v => html`
            <button class=${"pill-btn " + (showDnc===v ? "on" : "")} onClick=${() => setShowDnc(v)}>${v==="NON_DNC"?"Non-DNC":v}</button>`)}
          <span class="text-[10px] uppercase tracking-widest text-ev-dim mr-1 ml-4">Verified</span>
          ${["ALL","VERIFIED","RAW"].map(v => html`
            <button class=${"pill-btn " + (showVerified===v ? "on" : "")} onClick=${() => setShowVerified(v)}>${v}</button>`)}
        </div>
      </div>

      <div class="text-xs text-ev-dim mb-3 font-mono">${fmt(filtered.length)} of ${fmt(reports.length)} reports</div>

      <!-- Report rows -->
      <div class="glass rounded-2xl overflow-hidden">
        <div class="overflow-x-auto" style="max-height: 70vh; overflow-y:auto">
          <table class="intel">
            <thead><tr>
              <th>Target</th><th>Kind</th><th>State</th><th class="num">Verified / Raw</th>
              <th>Triggered by</th><th>Purpose</th><th>When</th><th>Status</th><th></th>
            </tr></thead>
            <tbody>
              ${filtered.slice(0, 500).map(r => html`
                <tr>
                  <td class="font-mono">
                    <a href=${r.report_url} target="_blank" rel="noopener" class="gold hover:underline">${r.target}</a>
                  </td>
                  <td class="text-xs"><span class="chip chip-gold">${r.kind}</span></td>
                  <td class="text-xs text-ev-dim font-mono">${r.state || "—"}</td>
                  <td class="num font-mono">
                    <span class=${(r.verified_findings||0)>0 ? "text-ev-green" : "text-ev-dim"}>${r.verified_findings||0}</span>
                    <span class="text-ev-dim"> / ${r.raw_findings||0}</span>
                  </td>
                  <td class="text-xs text-ev-dim">${r.triggered_by}</td>
                  <td class="text-xs text-ev-text/70" style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title=${r.business_purpose}>${r.business_purpose || "—"}</td>
                  <td class="text-xs text-ev-dim font-mono">${relTime(r.started_at)}</td>
                  <td class="text-xs">
                    ${r.dnc_blocked
                      ? html`<span class="chip chip-red">DNC</span>`
                      : (r.verified_findings||0) > 0
                        ? html`<span class="chip chip-green">VERIFIED</span>`
                        : html`<span class="chip chip-gold">RAW</span>`}
                  </td>
                  <td class="text-xs">
                    <a href=${r.report_url} target="_blank" rel="noopener" class="px-2 py-1 rounded bg-ev-gold/10 hover:bg-ev-gold/20 gold inline-flex items-center gap-1">
                      <${Icon} name="external-link" cls="w-3 h-3"/> Open
                    </a>
                  </td>
                </tr>`)}
            </tbody>
          </table>
        </div>
        ${filtered.length > 500 && html`<div class="p-3 text-center text-xs text-ev-dim border-t border-white/5">Showing first 500 -- narrow your filters</div>`}
        ${filtered.length === 0 && html`
          <div class="p-12 text-center text-sm text-ev-dim">
            No reports match. ${reports.length === 0 ? html`Run <code class="font-mono gold">intel investigate "&lt;target&gt;" --purpose="..."</code> to create one.` : "Clear a filter or try a different search."}
          </div>`}
      </div>
    </main>
    <${Footer}/>`;
}

render(html`<${ReportsPage}/>`, document.getElementById("app"));
'''

PAGES = {
    "resources.html":  ("Resources",  RESOURCES),
    "categories.html": ("Categories", CATEGORIES),
    "agents.html":     ("Agents",     AGENTS),
    "audit.html":      ("Audit",      AUDIT),
    "feeds.html":      ("Live Feeds", FEEDS),
    "articles.html":   ("Articles",   ARTICLES),
    "resource.html":   ("Resource",   RESOURCE),
    "usage.html":      ("Usage",      USAGE),
    "clients.html":    ("Clients",    CLIENTS),
    "reports.html":    ("Reports",    REPORTS),
}

for fname, (title, body) in PAGES.items():
    out = ROOT / fname
    out.write_text(page(title, body))
    print(f"[INTEL DASH] wrote {out.relative_to(ROOT.parent)}")
