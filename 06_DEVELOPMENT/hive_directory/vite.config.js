import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Default base is '/hive/' so the built bundle works behind nginx subpath routing.
// Override by setting VITE_BASE='/' for direct :8503 serve (dev / internal).
const BASE = process.env.VITE_BASE || '/hive/'

export default defineConfig({
  base: BASE,
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
    proxy: {
      '/api': 'http://127.0.0.1:8503',
      '/avatars': 'http://127.0.0.1:8503',
      '/photos': 'http://127.0.0.1:8503',
    },
  },
  build: { outDir: 'dist' },
})
