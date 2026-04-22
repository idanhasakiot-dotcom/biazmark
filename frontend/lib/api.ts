// Tiny typed API client. No runtime deps.
//
// Three modes:
//   1. Empty NEXT_PUBLIC_API_URL → same-origin, goes through Next.js rewrites to backend.
//      (This is what the Vercel deploy uses.)
//   2. Set NEXT_PUBLIC_API_URL → calls that origin directly.
//      (Used by the mobile app and static exports.)
//   3. Runtime override via localStorage `biazmark.apiBase` → lets users paste
//      their backend URL in the app without a rebuild.

const DEFAULT_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function apiBase(): string {
  if (typeof window !== "undefined") {
    const override = window.localStorage?.getItem("biazmark.apiBase");
    if (override) return override.replace(/\/$/, "");
  }
  return DEFAULT_BASE.replace(/\/$/, "");
}

const BASE_FOR_SERVER = (process.env.BIAZMARK_BACKEND_URL || DEFAULT_BASE || "http://localhost:8000").replace(/\/$/, "");

export type Tier = "free" | "basic" | "pro" | "enterprise";

export interface Business {
  id: string;
  name: string;
  description: string;
  website: string;
  industry: string;
  target_audience: string;
  goals: string;
  tier: Tier;
  created_at: string;
}

export interface Research {
  id: string;
  business_id: string;
  summary: string;
  competitors: any[];
  trends: any[];
  audience_insights: Record<string, any>;
  sources: any[];
  created_at: string;
}

export interface Strategy {
  id: string;
  business_id: string;
  version: number;
  positioning: string;
  value_prop: string;
  channels: any[];
  messaging_pillars: any[];
  kpis: any[];
  budget_split: Record<string, any>;
  approved: boolean;
  created_at: string;
}

export interface Campaign {
  id: string;
  business_id: string;
  strategy_id: string;
  name: string;
  channel: string;
  objective: string;
  status: string;
  created_at: string;
}

export interface ContentVariant {
  id: string;
  campaign_id: string;
  kind: string;
  headline: string;
  body: string;
  long_body: string;
  cta: string;
  visual_prompt: string;
  media_url: string;
  media_kind: string;
  meta: Record<string, any>;
  score: number;
  status: string;
  external_id: string;
  external_url: string;
  created_at: string;
}

export interface MediaAsset {
  id: string;
  business_id: string;
  variant_id: string;
  kind: string;
  prompt: string;
  provider: string;
  url: string;
  width: number;
  height: number;
  created_at: string;
}

export interface ConnectorAccount {
  id: string;
  business_id: string;
  platform: string;
  display_name: string;
  account_meta: Record<string, any>;
  status: string;
  expires_at: string | null;
  created_at: string;
}

export interface ConnectorStatus {
  platform: string;
  display_name: string;
  oauth_supported: boolean;
  oauth_configured: boolean;
  connected: boolean;
  account_name: string;
  account_meta: Record<string, any>;
}

export interface Metric {
  id: string;
  campaign_id: string;
  variant_id: string;
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number;
  revenue: number;
  engagement: number;
  captured_at: string;
}

export interface OptimizationEvent {
  id: string;
  business_id: string;
  campaign_id: string;
  kind: string;
  reason: string;
  payload: any;
  created_at: string;
}

export interface ConnectorInfo {
  platform: string;
  display_name: string;
  supports_publish: boolean;
  supports_metrics: boolean;
}

export interface TierInfo {
  tier: Tier;
  llm_provider: string;
  llm_model: string;
  research_depth: string;
  max_connectors: number;
  loop_interval_seconds: number | null;
  autonomous_agents: boolean;
  max_content_variants: number;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const base = typeof window === "undefined" ? BASE_FOR_SERVER : apiBase();
  // Short timeout on server-side so a missing backend never blocks page render for long.
  const isServer = typeof window === "undefined";
  const controller = new AbortController();
  const timeoutMs = isServer ? 2500 : 30000;
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${base}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status} ${res.statusText} — ${text}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(t);
  }
}

export const api = {
  tier: () => req<TierInfo>("/api/tier"),
  connectors: () => req<ConnectorInfo[]>("/api/connectors"),

  listBusinesses: () => req<Business[]>("/api/businesses"),
  getBusiness: (id: string) => req<Business>(`/api/businesses/${id}`),
  createBusiness: (payload: Partial<Business>) =>
    req<Business>("/api/businesses", { method: "POST", body: JSON.stringify(payload) }),

  runResearch: (id: string) =>
    req<Research>(`/api/businesses/${id}/research`, { method: "POST" }),
  listResearch: (id: string) => req<Research[]>(`/api/businesses/${id}/research`),

  runStrategy: (id: string, payload: { channels?: string[]; budget_hint?: string } = {}) =>
    req<Strategy>(`/api/businesses/${id}/strategies`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listStrategies: (id: string) => req<Strategy[]>(`/api/businesses/${id}/strategies`),
  approveStrategy: (id: string) =>
    req<Strategy>(`/api/strategies/${id}/approve`, { method: "POST" }),

  publishStrategy: (id: string, connector = "preview") =>
    req<Campaign[]>(`/api/strategies/${id}/publish`, {
      method: "POST",
      body: JSON.stringify({ connector }),
    }),

  listCampaigns: (businessId: string) =>
    req<Campaign[]>(`/api/businesses/${businessId}/campaigns`),
  getCampaign: (id: string) => req<Campaign>(`/api/campaigns/${id}`),
  listVariants: (id: string) => req<ContentVariant[]>(`/api/campaigns/${id}/variants`),
  listMetrics: (id: string) => req<Metric[]>(`/api/campaigns/${id}/metrics`),
  optimizeCampaign: (id: string) =>
    req<OptimizationEvent | null>(`/api/campaigns/${id}/optimize`, { method: "POST" }),
  listOptimizations: (businessId: string) =>
    req<OptimizationEvent[]>(`/api/businesses/${businessId}/optimizations`),

  // Content + media
  listBusinessContent: (businessId: string, kind?: string) =>
    req<ContentVariant[]>(
      `/api/businesses/${businessId}/content${kind ? `?kind=${kind}` : ""}`,
    ),
  listBusinessMedia: (businessId: string) =>
    req<MediaAsset[]>(`/api/businesses/${businessId}/media`),

  // Connections + OAuth
  listConnections: (businessId: string) =>
    req<ConnectorAccount[]>(`/api/businesses/${businessId}/connections`),
  connectorStatus: (businessId: string) =>
    req<ConnectorStatus[]>(`/api/businesses/${businessId}/connector-status`),
  startOAuth: (businessId: string, platform: string) =>
    req<{ authorise_url: string; state: string }>(
      `/api/businesses/${businessId}/oauth/${platform}/start`,
      { method: "POST" },
    ),
  deleteConnection: (id: string) => {
    const base = typeof window === "undefined" ? BASE_FOR_SERVER : apiBase();
    return fetch(`${base}/api/connections/${id}`, { method: "DELETE" });
  },
  oauthPlatforms: () =>
    req<{ platform: string; configured: boolean }[]>(`/api/oauth/platforms`),
  mediaProviders: () =>
    req<{ name: string; configured: boolean; supports_video: boolean }[]>(
      `/api/media/providers`,
    ),
};
