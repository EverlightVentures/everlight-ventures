/**
 * External tools and legacy dashboards.
 * Lucrex OS centralizes them so you never hunt for a URL again.
 */

export type ExternalTool = {
  key: string;
  label: string;
  url: string;
  blurb: string;
  category: "ops" | "trading" | "automation" | "intel" | "public" | "infra";
  status: "live" | "internal" | "legacy" | "deprecated";
};

const ORACLE = "http://163.192.19.196";

export const EXTERNAL_TOOLS: ExternalTool[] = [
  {
    key: "django",
    label: "Django Ops :8504",
    url: `${ORACLE}:8504/`,
    blurb: "Legacy ops dashboard. 14 views: Reports, Sessions, Bot Intel, Taskboard, Payments, Funnel.",
    category: "ops",
    status: "legacy",
  },
  {
    key: "xlm",
    label: "XLM React Dash :8502",
    url: `${ORACLE}:8502/`,
    blurb: "Live XLM bot dashboard with tick chart, positions, decisions.",
    category: "trading",
    status: "live",
  },
  {
    key: "hive_directory",
    label: "Hive Directory",
    url: `${ORACLE}:8080/hive/`,
    blurb: "63-agent employee directory with profiles + relationships.",
    category: "ops",
    status: "live",
  },
  {
    key: "vantaris",
    label: "Vantaris Casino",
    url: `${ORACLE}:8080/`,
    blurb: "Casino games hub: blackjack, plus 5 more built.",
    category: "public",
    status: "live",
  },
  {
    key: "n8n",
    label: "n8n Automation :5678",
    url: `${ORACLE}:5678/`,
    blurb: "Workflow automation. PARKED 2026-04-24, replaced by content_tools.n8n_replacements.",
    category: "automation",
    status: "deprecated",
  },
  {
    key: "blinko",
    label: "Blinko RAG :1111",
    url: `${ORACLE}:1111/`,
    blurb: "Knowledge base, 449+ notes. API at /api/v1/note/list.",
    category: "intel",
    status: "live",
  },
  {
    key: "ev_io",
    label: "everlightventures.io",
    url: "https://everlightventures.io/",
    blurb: "Public marketing site (React/Vite on Cloudflare Pages).",
    category: "public",
    status: "live",
  },
];

export const TOOLS_BY_CATEGORY = EXTERNAL_TOOLS.reduce<Record<string, ExternalTool[]>>(
  (acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  },
  {}
);
