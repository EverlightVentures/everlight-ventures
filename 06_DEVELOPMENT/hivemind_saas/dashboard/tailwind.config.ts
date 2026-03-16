import type { Config } from "tailwindcss";
import { fontFamily } from "tailwindcss/defaultTheme";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", ...fontFamily.sans],
        heading: ["DM Sans", "Inter", ...fontFamily.sans],
        display: ["DM Sans", ...fontFamily.sans],
      },
      colors: {
        // Base dark luxury palette
        void: "#0A0A0F",
        surface: {
          DEFAULT: "#111118",
          raised: "#16161F",
          overlay: "#1C1C27",
        },
        border: {
          DEFAULT: "#1E1E2E",
          subtle: "#16161F",
          strong: "#2A2A3E",
        },
        // Primary violet
        violet: {
          50: "#F5F3FF",
          100: "#EDE9FE",
          200: "#DDD6FE",
          300: "#C4B5FD",
          400: "#A78BFA",
          500: "#8B5CF6",
          600: "#7C3AED",
          700: "#6D28D9",
          800: "#5B21B6",
          900: "#4C1D95",
          950: "#2E1065",
        },
        // Gold accent
        gold: {
          50: "#FFFBEB",
          100: "#FEF3C7",
          200: "#FDE68A",
          300: "#FCD34D",
          400: "#FBBF24",
          500: "#F59E0B",
          600: "#D97706",
          700: "#B45309",
          800: "#92400E",
          900: "#78350F",
        },
        // Semantic
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
        info: "#3B82F6",
        // Text hierarchy
        text: {
          primary: "#F1F1F8",
          secondary: "#A0A0B8",
          muted: "#5C5C7A",
          disabled: "#3A3A52",
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "gradient-void": "linear-gradient(135deg, #0A0A0F 0%, #0F0F1A 50%, #0A0A12 100%)",
        "gradient-surface": "linear-gradient(135deg, #111118 0%, #16161F 100%)",
        "gradient-violet": "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)",
        "gradient-gold": "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)",
        "gradient-hero": "linear-gradient(135deg, #7C3AED20 0%, #0A0A0F 50%, #F59E0B10 100%)",
        "shimmer": "linear-gradient(90deg, transparent 0%, #7C3AED15 50%, transparent 100%)",
      },
      boxShadow: {
        "glow-violet": "0 0 20px rgba(124, 58, 237, 0.35), 0 0 60px rgba(124, 58, 237, 0.15)",
        "glow-violet-sm": "0 0 10px rgba(124, 58, 237, 0.25), 0 0 25px rgba(124, 58, 237, 0.1)",
        "glow-gold": "0 0 20px rgba(245, 158, 11, 0.35), 0 0 60px rgba(245, 158, 11, 0.15)",
        "glow-gold-sm": "0 0 10px rgba(245, 158, 11, 0.25), 0 0 25px rgba(245, 158, 11, 0.1)",
        "glow-success": "0 0 15px rgba(16, 185, 129, 0.3)",
        "glow-danger": "0 0 15px rgba(239, 68, 68, 0.3)",
        "card": "0 1px 3px rgba(0,0,0,0.5), 0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)",
        "card-hover": "0 2px 8px rgba(0,0,0,0.6), 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)",
        "card-active": "0 0 0 1px rgba(124, 58, 237, 0.5), 0 0 20px rgba(124, 58, 237, 0.2), 0 4px 16px rgba(0,0,0,0.4)",
        "sidebar": "4px 0 24px rgba(0,0,0,0.4)",
        "inset": "inset 0 1px 0 rgba(255,255,255,0.04), inset 0 -1px 0 rgba(0,0,0,0.2)",
      },
      borderRadius: {
        "xl": "12px",
        "2xl": "16px",
        "3xl": "20px",
        "4xl": "24px",
      },
      animation: {
        "glow-pulse": "glow-pulse 3s ease-in-out infinite",
        "glow-breathe": "glow-breathe 4s ease-in-out infinite",
        "slide-in-left": "slide-in-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "slide-in-right": "slide-in-right 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "fade-in": "fade-in 0.4s ease-out",
        "fade-up": "fade-up 0.4s ease-out",
        "shimmer": "shimmer 2.5s ease-in-out infinite",
        "spin-slow": "spin 8s linear infinite",
        "bounce-subtle": "bounce-subtle 2s ease-in-out infinite",
        "agent-pulse": "agent-pulse 2s ease-in-out infinite",
      },
      keyframes: {
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 10px rgba(124, 58, 237, 0.2), 0 0 25px rgba(124, 58, 237, 0.08)" },
          "50%": { boxShadow: "0 0 25px rgba(124, 58, 237, 0.5), 0 0 60px rgba(124, 58, 237, 0.2)" },
        },
        "glow-breathe": {
          "0%, 100%": { opacity: "0.7" },
          "50%": { opacity: "1" },
        },
        "slide-in-left": {
          from: { transform: "translateX(-20px)", opacity: "0" },
          to: { transform: "translateX(0)", opacity: "1" },
        },
        "slide-in-right": {
          from: { transform: "translateX(20px)", opacity: "0" },
          to: { transform: "translateX(0)", opacity: "1" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "shimmer": {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "bounce-subtle": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-4px)" },
        },
        "agent-pulse": {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.15)", opacity: "0.8" },
        },
      },
      transitionTimingFunction: {
        "premium": "cubic-bezier(0.4, 0, 0.2, 1)",
        "spring": "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
      spacing: {
        "sidebar": "260px",
        "sidebar-collapsed": "72px",
        "header": "64px",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
