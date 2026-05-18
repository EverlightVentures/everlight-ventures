// Shared head/nav/footer for Intel Center dashboard pages.
// Imported as module by each page.
import { h, render } from "https://esm.sh/preact@10.22.0";
import { useEffect, useState, useMemo } from "https://esm.sh/preact@10.22.0/hooks";
import htm from "https://esm.sh/htm@3.1.1";

export const html = htm.bind(h);
export { h, render, useEffect, useState, useMemo };

export const D = window.INTEL || {meta:{}, categories:[], agents:[], resources:[], fetchable_topics:{}};
export const fmt = n => (n||0).toLocaleString();
export const pct = (used, total) => total ? Math.round(used*100/total) : 0;

export function useLucide(){
  useEffect(() => { if (window.lucide) window.lucide.createIcons(); });
}

export const Icon = ({name, cls=""}) => html`<i data-lucide=${name} class=${cls}></i>`;

export const NAV_LINKS = [
  ["Overview",   "./index.html",                "overview"],
  ["Articles",   "./articles.html",             "articles"],
  ["Reports",    "./reports.html",              "reports"],
  ["Clients",    "./clients.html",              "clients"],
  ["OSINT",      "http://localhost:2301/",      "osint",      true],
  ["Resources",  "./resources.html",            "resources"],
  ["Categories", "./categories.html",           "categories"],
  ["Agents",     "./agents.html",               "agents"],
  ["Live Feeds", "./feeds.html",                "feeds"],
  ["Usage",      "./usage.html",                "usage"],
  ["Audit",      "./audit.html",                "audit"],
];

export const Nav = ({active}) => html`
  <header class="border-b border-white/5 backdrop-blur">
    <div class="max-w-7xl mx-auto px-5 py-4 flex items-center gap-6">
      <a href="./index.html" class="flex items-center gap-3 group">
        <div class="w-10 h-10 rounded-xl glass-gold grid place-items-center group-hover:shadow-glow transition">
          <${Icon} name="brain-circuit" cls="w-5 h-5 gold"/>
        </div>
        <div>
          <div class="font-display text-xl gold gold-glow leading-tight">Intel Center</div>
          <div class="text-[10px] tracking-[.18em] text-ev-dim uppercase">Everlight Ventures</div>
        </div>
      </a>
      <nav class="flex items-center gap-1 ml-auto text-sm font-medium overflow-x-auto">
        ${NAV_LINKS.map(link => {
          const [label, href, key, external] = link;
          return html`<a href=${href}
                         target=${external ? "_blank" : null}
                         rel=${external ? "noopener" : null}
                         class=${"nav-link " + (active===key ? "active" : "") + (external ? " text-ev-purple" : "")}>
            ${label}${external ? " ↗" : ""}
          </a>`;
        })}
      </nav>
    </div>
  </header>`;

export const Footer = () => html`
  <footer class="border-t border-white/5 py-5 text-center text-xs text-ev-dim">
    Generated ${D.meta.generated || ''} · Lucrex · Everlight Ventures · port 2300
  </footer>`;

export const TOPIC_ICONS = {
  news:'newspaper', weather:'cloud-rain', space:'rocket', finance:'trending-up',
  osint:'shield-search', health:'heart-pulse', markets:'bar-chart-3', aviation:'plane'
};

export const slugFor = (cat) => "".concat(...[...cat.toLowerCase()].map(c => /[a-z0-9]/.test(c) ? c : '_')).replace(/^_+|_+$/g,'');

// ============================================================================
// Article-redesign helpers -- magazine UX utilities
// ============================================================================

export function relTime(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr.slice(0, 16);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return Math.floor(diff/60) + "m ago";
  if (diff < 86400) return Math.floor(diff/3600) + "h ago";
  if (diff < 604800) return Math.floor(diff/86400) + "d ago";
  return d.toLocaleDateString("en-US", {month:"short", day:"numeric", year: d.getFullYear() === new Date().getFullYear() ? undefined : "numeric"});
}

export function readingTimeMin(text = "") {
  return Math.max(1, Math.ceil((text.length || 0) / 800));
}

const SENTIMENT_NEG = /\b(crisis|crash|collapse|lawsuit|ban|fire|death|killed|loss|losses|down|tumble|plunge|recession|attack|threat|warn|warning|risk|danger|sanction|breach|hack|leak|outage|failure|panic|fear|sell-?off|conflict|war|invasion|missile|strike|protest|rights|abuse|fraud|scam|indict|arrest|prison|guilty|tornado|hurricane|earthquake|wildfire|flood|tsunami)\b/i;
const SENTIMENT_POS = /\b(growth|surge|boost|rally|gain|gains|win|wins|launch|breakthrough|record|soar|soars|profit|deal|partnership|innovation|approve|approved|expansion|hiring|raise|funded|ipo|milestone|success|first|new|debut|unveil|unveils|secure|secured|achievement|recovery|peace|resolve|talks|cooperation)\b/i;

export function inferSentiment(text = "") {
  if (SENTIMENT_NEG.test(text)) return "neg";
  if (SENTIMENT_POS.test(text)) return "pos";
  return "neu";
}

const TOPIC_RULES = [
  ["Markets",     /\b(stock|stocks|market|markets|bond|yields|rate|rates|fed|fomc|treasury|earnings|tariff|nasdaq|s&p|dow|nikkei|inflation|recession|gdp|cpi|trading|bitcoin|crypto|btc|eth|wall street)\b/i],
  ["Conflict",    /\b(war|invasion|attack|military|missile|strike|sanction|israel|iran|ukraine|russia|china|nato|nuclear|combat|troop|troops|gaza|hamas|hezbollah)\b/i],
  ["Politics",    /\b(election|president|senate|congress|biden|trump|democrat|republican|vote|votes|campaign|impeach|policy|law|legislation|cabinet|primary|debate)\b/i],
  ["Tech",        /\b(ai|gpt|openai|anthropic|claude|llm|chip|chips|silicon|google|microsoft|meta|apple|amazon|nvidia|software|hardware|robot|robots|app|startup|ipo|tech)\b/i],
  ["Space",       /\b(nasa|spacex|space|rocket|launch|orbit|mars|moon|asteroid|satellite|telescope|exoplanet|astronaut|cosmos|galaxy|hubble|webb)\b/i],
  ["Climate",     /\b(climate|warming|emissions|carbon|drought|wildfire|hurricane|storm|temperature|degree|noaa|epa|environment|renewable|solar|wind farm)\b/i],
  ["Health",      /\b(health|disease|outbreak|virus|vaccine|cancer|covid|pandemic|fda|cdc|hospital|patient|treatment|drug|biotech|pharma|trial|clinical)\b/i],
  ["Crime",       /\b(arrest|charge|charged|indictment|court|jury|verdict|prison|fbi|police|detective|murder|theft|fraud|scam|trafficking)\b/i],
  ["Business",    /\b(merger|acquisition|deal|buyout|ipo|raised|funding|series|ceo|cfo|board|company|firm|firms|partnership|expansion|layoff|hiring|profit|revenue)\b/i],
  ["Energy",      /\b(oil|opec|gas|crude|barrel|wti|brent|energy|electric|grid|battery|nuclear plant|reactor|pipeline|drilling)\b/i],
];

export function inferTopic(text = "") {
  for (const [name, re] of TOPIC_RULES) {
    if (re.test(text)) return name;
  }
  return "General";
}

const TOPIC_COLORS = {
  Markets:  "gold",      Conflict:  "red",
  Politics: "purple",    Tech:      "cyan",
  Space:    "purple",    Climate:   "green",
  Health:   "green",     Crime:     "red",
  Business: "gold",      Energy:    "orange",
  General:  "dim",
};
export const topicColor = (t) => TOPIC_COLORS[t] || "dim";

const CATEGORY_ACCENT = {
  "News & Journalism":         "#c9a84c",
  "Weather & Disaster Intel":  "#22d3ee",
  "Maps & Geospatial":         "#22d3ee",
  "Aviation & Maritime":       "#22d3ee",
  "Space & Science":           "#8b5cf6",
  "Economics & Markets":       "#c9a84c",
  "Trading & Finance":         "#c9a84c",
  "OSINT & Investigation":     "#dc2626",
  "Cybersecurity":             "#dc2626",
  "AI & Automation":           "#8b5cf6",
  "APIs & Developer Tools":    "#22d3ee",
  "Content Creation":          "#f97316",
  "eCommerce & Product Research": "#22c55e",
  "Real Estate & Property":    "#22c55e",
  "Logistics & Supply Chain":  "#22c55e",
  "Legal & Compliance":        "#dc2626",
  "Health & Environment":      "#22c55e",
  "Education & Training":      "#22d3ee",
  "Self-Hosting & Privacy":    "#22d3ee",
  "Decision Intelligence":     "#c9a84c",
};
export const accentForCategory = (c) => CATEGORY_ACCENT[c] || "#c9a84c";

export function highlight(text, query) {
  if (!query || !text) return text;
  const re = new RegExp("(" + query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig");
  const parts = text.split(re);
  return parts.map((p, i) => i % 2 === 1
    ? html`<mark style="background:rgba(201,168,76,0.25);color:#e0c66a;padding:0 .15em;border-radius:.15em">${p}</mark>`
    : p);
}

export function bucketByTime(items) {
  const today = []; const week = []; const earlier = [];
  const now = Date.now();
  for (const item of items) {
    const ts = (item.published && new Date(item.published).getTime())
            || (item.fetched_at && new Date(item.fetched_at).getTime())
            || 0;
    if (!ts) { earlier.push(item); continue; }
    const ageHrs = (now - ts) / 3600000;
    if (ageHrs <= 24) today.push(item);
    else if (ageHrs <= 168) week.push(item);
    else earlier.push(item);
  }
  return { today, week, earlier };
}
