import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Deep Research Engine — AI-Powered Engineering Research",
  description:
    "Ingest PDFs, URLs, and GitHub repos. Get cited engineering reports with a deterministic pipeline: Plan → Retrieve → Write → Judge → Refine. Free-tier LLM models via OpenRouter.",
  keywords: [
    "AI research",
    "engineering",
    "deep research",
    "PDF analysis",
    "technical reports",
    "flashcards",
    "LangGraph",
    "OpenRouter",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0a0a0a" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
