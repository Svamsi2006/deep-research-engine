/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Pass BACKEND_URL to server-side API route handlers.
  // On Vercel: set BACKEND_URL=https://your-render-app.onrender.com in the Dashboard.
  // Locally: set BACKEND_URL=http://localhost:8000 in .env (no NEXT_PUBLIC_ prefix needed).
  env: {
    BACKEND_URL: process.env.BACKEND_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
