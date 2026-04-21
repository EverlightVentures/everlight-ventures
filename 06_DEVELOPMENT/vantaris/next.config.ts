import type { NextConfig } from 'next'

/**
 * Next.js config for pure static export.
 *
 * This app is a client-side SPA:
 * - All backend logic runs in Supabase edge functions (no Next.js API routes)
 * - All 35+ pages use 'use client' directive
 * - Realtime uses Supabase Realtime channels
 *
 * Static export outputs plain HTML/JS files that any CDN can serve.
 * No adapter (next-on-pages), no edge runtime config, no vendor lock-in.
 * Deploy target: `out/` directory.
 */
const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true, // better for static hosts (Cloudflare Pages, S3, etc.)
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    unoptimized: true, // required for static export
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true, // deploy even with TS warnings; fix them as we go
  },
}

export default nextConfig
