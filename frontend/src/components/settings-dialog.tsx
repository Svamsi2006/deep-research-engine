"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Settings, Save, Loader2, X } from "lucide-react";
import {
  getRuntimeSettings,
  saveRuntimeSettings,
  RuntimeSettings,
  RuntimeSettingsUpdate,
} from "@/lib/sse-client";

interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

const AI_PROVIDERS = ["ollama", "openai", "gemini", "deepseek", "openrouter", "grok", "groq"];
const WEB_PROVIDERS = ["tavily", "firecrawl", "duckduckgo"];

export default function SettingsDialog({ open, onClose }: SettingsDialogProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [settings, setSettings] = useState<RuntimeSettings | null>(null);
  const [form, setForm] = useState<RuntimeSettingsUpdate>({
    ai_provider: "openrouter",
    ai_api_key: "",
    ai_api_base_url: "",
    ai_model: "",
    ai_context_length: 128000,
    web_search_provider: "tavily",
    web_search_api_key: "",
    web_search_concurrency_limit: 2,
    web_search_advanced: false,
    web_search_topic: "general",
  });

  useEffect(() => {
    if (!open) return;
    let mounted = true;
    setLoading(true);
    setError("");
    setOk("");
    getRuntimeSettings()
      .then((data) => {
        if (!mounted) return;
        setSettings(data);
        setForm({
          ai_provider: data.ai_provider,
          ai_api_key: data.ai_api_key || "",
          ai_api_base_url: data.ai_api_base_url,
          ai_model: data.ai_model,
          ai_context_length: data.ai_context_length,
          web_search_provider: data.web_search_provider,
          web_search_api_key: data.web_search_api_key || "",
          web_search_concurrency_limit: data.web_search_concurrency_limit,
          web_search_advanced: data.web_search_advanced,
          web_search_topic: data.web_search_topic,
        });
      })
      .catch((e) => setError(e.message || "Failed to load settings"))
      .finally(() => setLoading(false));

    return () => {
      mounted = false;
    };
  }, [open]);

  const aiPreset = useMemo(() => {
    if (!settings) return null;
    return settings.ai_provider_presets[form.ai_provider] || null;
  }, [settings, form.ai_provider]);

  const webPreset = useMemo(() => {
    if (!settings) return null;
    return settings.web_provider_presets[form.web_search_provider] || null;
  }, [settings, form.web_search_provider]);

  const onProviderChange = (provider: string) => {
    const presetBase = settings?.ai_provider_presets?.[provider]?.api_base_url || "";

    setForm((prev) => ({
      ...prev,
      ai_provider: provider,
      ai_api_base_url: presetBase || prev.ai_api_base_url,
      ai_model: settings?.ai_provider_presets?.[provider]?.model || prev.ai_model,
      ai_context_length: settings?.ai_provider_presets?.[provider]?.context_length || prev.ai_context_length,
      web_search_provider:
        provider === "ollama" && !prev.web_search_api_key ? "duckduckgo" : prev.web_search_provider,
    }));
  };

  const onSave = async () => {
    try {
      setSaving(true);
      setError("");
      setOk("");
      await saveRuntimeSettings(form);
      const refreshed = await getRuntimeSettings();
      setSettings(refreshed);
      setForm({
        ai_provider: refreshed.ai_provider,
        ai_api_key: refreshed.ai_api_key || "",
        ai_api_base_url: refreshed.ai_api_base_url,
        ai_model: refreshed.ai_model,
        ai_context_length: refreshed.ai_context_length,
        web_search_provider: refreshed.web_search_provider,
        web_search_api_key: refreshed.web_search_api_key || "",
        web_search_concurrency_limit: refreshed.web_search_concurrency_limit,
        web_search_advanced: refreshed.web_search_advanced,
        web_search_topic: refreshed.web_search_topic,
      });
      setOk("Settings saved. New requests will use the updated configuration.");
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-background">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2">
            <Settings className="w-4 h-4 text-accent" />
            <h2 className="text-sm font-semibold">Settings</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="p-6 text-sm text-muted-foreground flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading settings...
          </div>
        ) : (
          <div className="p-4 space-y-5">
            <section className="space-y-3">
              <h3 className="text-xs uppercase tracking-wider text-muted-foreground">AI Provider</h3>
              <div className="grid md:grid-cols-2 gap-3">
                <label className="text-xs text-muted-foreground">
                  Provider
                  <select
                    value={form.ai_provider}
                    onChange={(e) => onProviderChange(e.target.value)}
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  >
                    {AI_PROVIDERS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </label>

                <label className="text-xs text-muted-foreground">
                  API Key
                  <input
                    value={form.ai_api_key}
                    onChange={(e) => setForm((prev) => ({ ...prev, ai_api_key: e.target.value }))}
                    placeholder="API Key"
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  />
                </label>

                <label className="text-xs text-muted-foreground md:col-span-2">
                  API Base URL
                  <input
                    value={form.ai_api_base_url}
                    onChange={(e) => setForm((prev) => ({ ...prev, ai_api_base_url: e.target.value }))}
                    placeholder={aiPreset?.api_base_url || "https://api.example.com/v1"}
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  />
                </label>

                <label className="text-xs text-muted-foreground">
                  Model
                  <input
                    value={form.ai_model}
                    onChange={(e) => setForm((prev) => ({ ...prev, ai_model: e.target.value }))}
                    placeholder={aiPreset?.model || "Model"}
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  />
                </label>

                <label className="text-xs text-muted-foreground">
                  Context Length (tokens)
                  <input
                    type="number"
                    min={1024}
                    value={form.ai_context_length}
                    onChange={(e) => setForm((prev) => ({ ...prev, ai_context_length: Number(e.target.value || 0) }))}
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  />
                </label>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-xs uppercase tracking-wider text-muted-foreground">Web Search Provider</h3>
              <div className="grid md:grid-cols-2 gap-3">
                <label className="text-xs text-muted-foreground">
                  Provider
                  <select
                    value={form.web_search_provider}
                    onChange={(e) => setForm((prev) => ({ ...prev, web_search_provider: e.target.value }))}
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  >
                    {WEB_PROVIDERS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </label>

                <label className="text-xs text-muted-foreground">
                  API Key
                  <input
                    value={form.web_search_api_key}
                    onChange={(e) => setForm((prev) => ({ ...prev, web_search_api_key: e.target.value }))}
                    placeholder="API Key"
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  />
                </label>

                <label className="text-xs text-muted-foreground">
                  Concurrency Limit
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={form.web_search_concurrency_limit}
                    onChange={(e) => setForm((prev) => ({ ...prev, web_search_concurrency_limit: Number(e.target.value || 2) }))}
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  />
                </label>

                <label className="text-xs text-muted-foreground flex items-center gap-2 mt-5">
                  <input
                    type="checkbox"
                    checked={form.web_search_advanced}
                    disabled={!webPreset?.supports_advanced}
                    onChange={(e) => setForm((prev) => ({ ...prev, web_search_advanced: e.target.checked }))}
                  />
                  Advanced Search
                </label>

                <label className="text-xs text-muted-foreground">
                  Search Topic
                  <select
                    value={form.web_search_topic}
                    disabled={!webPreset?.supports_topic}
                    onChange={(e) => setForm((prev) => ({ ...prev, web_search_topic: e.target.value }))}
                    className="mt-1 w-full rounded border border-border bg-muted px-2 py-2 text-sm text-foreground"
                  >
                    <option value="general">general</option>
                    <option value="news">news</option>
                    <option value="finance">finance</option>
                  </select>
                </label>
              </div>
            </section>

            {error && <p className="text-xs text-red-400">{error}</p>}
            {ok && <p className="text-xs text-emerald-400">{ok}</p>}

            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              <button onClick={onClose} className="rounded px-3 py-2 text-xs border border-border hover:bg-muted">Close</button>
              <button
                onClick={onSave}
                disabled={saving}
                className="rounded px-3 py-2 text-xs bg-accent text-accent-foreground hover:bg-accent/90 disabled:opacity-60 flex items-center gap-1"
              >
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save Settings
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
