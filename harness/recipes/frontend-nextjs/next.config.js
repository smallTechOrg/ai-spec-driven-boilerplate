/** @type {import('next').NextConfig} */

// Backend base URL. The browser reaches the backend through a same-origin proxy
// (the rewrite below), so requests stay CORS-free. NEXT_PUBLIC_API_URL is read at
// build time; default is the local backend on :8000 (both python recipes serve there).
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig = {
  async rewrites() {
    return [
      // /api/run -> ${API_URL}/run ; /api/health -> ${API_URL}/health
      { source: "/api/:path*", destination: `${API_URL}/:path*` },
    ];
  },
};

module.exports = nextConfig;
