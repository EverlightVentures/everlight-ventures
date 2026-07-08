/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",          // emit a static out/ (no Node server; FastAPI serves it)
  basePath: "/console",      // namespace so it lives beside the vanilla dashboard
  assetPrefix: "/console",
  images: { unoptimized: true },
  trailingSlash: true,
  eslint: { ignoreDuringBuilds: true }, // lint is noise here; TS type-checks still run
};
export default nextConfig;
