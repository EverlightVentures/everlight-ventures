import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Data lives on the phone filesystem; server components read from disk
  experimental: {
    serverActions: { allowedOrigins: ["localhost:3001", "127.0.0.1:3001"] },
  },
};

export default nextConfig;
