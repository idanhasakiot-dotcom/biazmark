/** @type {import('next').NextConfig} */

// Internal API base — where the FastAPI backend lives.
// On Vercel, set BIAZMARK_BACKEND_URL to your deployed backend (Railway/Fly/Render).
// Locally, defaults to http://localhost:8000.
// If neither is set (fresh Vercel deploy with no backend yet), we skip rewrites
// so the demo pages render without cryptic proxy errors — the BackendBanner
// component explains the demo mode to visitors.
const BACKEND = process.env.BIAZMARK_BACKEND_URL ||
  (process.env.VERCEL ? "" : "http://localhost:8000");

const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "",
  },
  async rewrites() {
    if (!BACKEND) return [];
    return [
      { source: "/api/:path*", destination: `${BACKEND}/api/:path*` },
      { source: "/media/:path*", destination: `${BACKEND}/media/:path*` },
      { source: "/docs", destination: `${BACKEND}/docs` },
      { source: "/openapi.json", destination: `${BACKEND}/openapi.json` },
    ];
  },
  ...(process.env.BIAZMARK_STATIC_EXPORT === "1"
    ? { output: "export", trailingSlash: true, images: { unoptimized: true } }
    : {}),
};

module.exports = nextConfig;
