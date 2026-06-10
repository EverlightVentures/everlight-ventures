/**
 * Lucrex OS theme map.
 * Domain variants tint the accent color; the base palette stays constant.
 */

export type DomainKey =
  | "hub"
  | "wealth"
  | "trading"
  | "wholesale"
  | "broker"
  | "content"
  | "revenue"
  | "intel"
  | "hive"
  | "arcade";

export type DomainMeta = {
  key: DomainKey;
  label: string;
  tagline: string;
  accent: string;
  themeClass: string;
  href: string;
  icon: string;
};

export const DOMAINS: Record<DomainKey, DomainMeta> = {
  hub: {
    key: "hub",
    label: "Hub",
    tagline: "Empire at a glance",
    accent: "#D4A843",
    themeClass: "theme-wealth",
    href: "/",
    icon: "Home",
  },
  wealth: {
    key: "wealth",
    label: "Wealth OS",
    tagline: "Sovereign wealth architecture",
    accent: "#D4A843",
    themeClass: "theme-wealth",
    href: "/wealth",
    icon: "Crown",
  },
  trading: {
    key: "trading",
    label: "Trading",
    tagline: "XLM bot live",
    accent: "#06B6D4",
    themeClass: "theme-trading",
    href: "/trading",
    icon: "TrendingUp",
  },
  wholesale: {
    key: "wholesale",
    label: "Wholesale",
    tagline: "Real estate pipeline",
    accent: "#D97706",
    themeClass: "theme-wholesale",
    href: "/wholesale",
    icon: "Home",
  },
  broker: {
    key: "broker",
    label: "Broker OS",
    tagline: "B2B match + commission",
    accent: "#B8902F",
    themeClass: "theme-broker",
    href: "/broker",
    icon: "Handshake",
  },
  content: {
    key: "content",
    label: "Content",
    tagline: "Factory + repurpose",
    accent: "#EC4899",
    themeClass: "theme-content",
    href: "/content",
    icon: "Sparkles",
  },
  revenue: {
    key: "revenue",
    label: "Revenue",
    tagline: "MRR + Stripe",
    accent: "#D4A843",
    themeClass: "theme-revenue",
    href: "/revenue",
    icon: "DollarSign",
  },
  intel: {
    key: "intel",
    label: "Intel",
    tagline: "Blinko RAG + research",
    accent: "#A855F7",
    themeClass: "theme-intel",
    href: "/intel",
    icon: "Brain",
  },
  hive: {
    key: "hive",
    label: "Hive",
    tagline: "63 agents, 12 fire teams",
    accent: "#3B82F6",
    themeClass: "theme-hive",
    href: "/hive",
    icon: "Network",
  },
  arcade: {
    key: "arcade",
    label: "Arcade",
    tagline: "Vantaris + Alley Kingz",
    accent: "#F472B6",
    themeClass: "theme-arcade",
    href: "/arcade",
    icon: "Dice5",
  },
};

export const DOMAIN_ORDER: DomainKey[] = [
  "wealth",
  "wholesale",
  "trading",
  "broker",
  "revenue",
  "content",
  "intel",
  "hive",
  "arcade",
];

export const HUB_TILE_COLORS: Record<DomainKey, string> = Object.fromEntries(
  Object.entries(DOMAINS).map(([k, v]) => [k, v.accent])
) as Record<DomainKey, string>;
