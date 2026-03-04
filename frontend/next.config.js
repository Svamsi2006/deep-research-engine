/** @type {import('next').NextConfig} */
const BACKEND_URL = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

const nextConfig = {
  reactStrictMode: true,

  // Proxy all /api/* requests to the Python backend in development.
  // In production (Vercel), set NEXT_PUBLIC_API_URL to your Railway/Render backend URL
  // and calls will go there directly from the client.
  async rewrites() {
    return [
      {
        // Only proxy in dev — the frontend calls NEXT_PUBLIC_API_URL directly in prod
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },

  // Expose only the API URL to the client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
