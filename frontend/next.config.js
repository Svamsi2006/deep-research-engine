/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Server-side env vars for Vercel serverless route handlers.
  // Set these in Vercel Dashboard → Settings → Environment Variables.
  // OPENROUTER_API_KEY and GROQ_API_KEY are REQUIRED for LLM calls.
  // BACKEND_URL is NO LONGER NEEDED — all LLM calls happen on Vercel now.
  env: {
    OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY || "",
    GROQ_API_KEY: process.env.GROQ_API_KEY || "",
    OPENROUTER_MODEL: process.env.OPENROUTER_MODEL || "deepseek/deepseek-chat-v3-0324:free",
    GROQ_MODEL: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
  },
};

module.exports = nextConfig;
