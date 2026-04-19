import type { NextConfig } from 'next'

/**
 * Next.js config optimized for Cloudflare Pages deployment.
 *
 * All server logic lives in Supabase edge functions, not Next.js API routes.
 * This lets CF Pages run the app as client-side rendered with tiny server footprint.
 *
 * - images.unoptimized: true -- skip Next.js Image Optimization (CF has its own)
 * - remotePatterns -- whitelist Google avatars, Supabase storage, stock imagery
 * - ignoreDuringBuilds -- don't block deploys on lint warnings
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: 'https', hostname: 'lh3.googleusercontent.com' },
      { protocol: 'https', hostname: '*.supabase.co' },
      { protocol: 'https', hostname: 'images.unsplash.com' },
    ],
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
}

export default nextConfig
