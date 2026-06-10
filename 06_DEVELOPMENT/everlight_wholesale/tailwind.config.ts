import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Everlight palette
        obsidian:   "#0A0A0A",
        charcoal:   "#141414",
        graphite:   "#1A1A1A",
        ash:        "#222222",
        gold:       "#D4A843",
        goldmuted:  "#9A7F33",
        goldsoft:   "#EAD08B",
        ivory:      "#E8E8E8",
        fog:        "#9A9A9A",
        smoke:      "#666666",
        // Semantic
        success:    "#65D195",
        warning:    "#E8B947",
        danger:     "#D65B5B",
      },
      fontFamily: {
        display: ["var(--font-playfair)", "Playfair Display", "serif"],
        sans:    ["var(--font-inter)",   "Inter", "system-ui", "sans-serif"],
        mono:    ["ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        "gold-glow":   "0 0 40px -10px rgba(212,168,67,0.35)",
        "deep":        "0 20px 50px -20px rgba(0,0,0,0.8)",
        "card":        "0 1px 0 rgba(212,168,67,0.05) inset, 0 10px 40px -20px rgba(0,0,0,0.8)",
      },
      backgroundImage: {
        "gold-gradient":     "linear-gradient(135deg, #D4A843 0%, #EAD08B 50%, #D4A843 100%)",
        "obsidian-gradient": "linear-gradient(180deg, #0A0A0A 0%, #141414 100%)",
        "card-gradient":     "linear-gradient(160deg, #141414 0%, #0E0E0E 100%)",
      },
      animation: {
        "pulse-gold": "pulse-gold 2.5s ease-in-out infinite",
        "shimmer":    "shimmer 2.5s linear infinite",
      },
      keyframes: {
        "pulse-gold": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(212,168,67,0.35)" },
          "50%":      { boxShadow: "0 0 0 10px rgba(212,168,67,0)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
