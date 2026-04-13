import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        display: ['Playfair Display', 'Georgia', 'serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'monospace'],
      },
      colors: {
        vanta: {
          void: '#050507',
          abyss: '#0a0a10',
          surface: '#0f0f18',
          elevated: '#151520',
        },
        gold: '#c9a84c',
        win: '#00e676',
        loss: '#ff2d55',
      },
    },
  },
  plugins: [],
}

export default config
