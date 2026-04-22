import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { ConnectButton } from "./connect-button";

export const dynamic = "force-dynamic";

export default async function ConnectionsPage({
  params,
}: {
  params: Promise<{ businessId: string }>;
}) {
  const { businessId } = await params;
  const biz = await api.getBusiness(businessId).catch(() => null);
  if (!biz) notFound();

  const [statuses, mediaProviders] = await Promise.all([
    api.connectorStatus(businessId).catch(() => []),
    api.mediaProviders().catch(() => []),
  ]);

  return (
    <div className="space-y-8">
      <div>
        <Link
          href={`/dashboard/${businessId}`}
          className="text-sm text-slate-400 hover:text-slate-200"
        >
          ← {biz.name}
        </Link>
        <h1 className="text-3xl font-bold mt-1">Connections</h1>
        <p className="text-slate-400 mt-1">
          Connect each platform once — Biazmark will post, run ads, and pull metrics on its own.
        </p>
      </div>

      <section>
        <h2 className="font-semibold mb-3">Platforms</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {statuses.map((s) => (
            <div key={s.platform} className="card">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{s.display_name}</span>
                    {s.connected && <span className="badge badge-success">connected</span>}
                    {!s.connected && s.oauth_supported && s.oauth_configured && (
                      <span className="badge badge-muted">not connected</span>
                    )}
                    {s.oauth_supported && !s.oauth_configured && (
                      <span className="badge badge-warning">app credentials needed</span>
                    )}
                    {!s.oauth_supported && !s.connected && (
                      <span className="badge badge-muted">env credentials</span>
                    )}
                  </div>
                  {s.account_name && (
                    <div className="text-sm text-slate-400 mt-1">{s.account_name}</div>
                  )}
                  {s.oauth_supported && !s.oauth_configured && (
                    <div className="text-xs text-slate-500 mt-2">
                      Add <code className="text-accent-400">{s.platform.toUpperCase()}_APP_ID</code> /{" "}
                      <code className="text-accent-400">_APP_SECRET</code> (or CLIENT_ID/SECRET) to your .env to enable OAuth.
                    </div>
                  )}
                </div>
                <ConnectButton
                  businessId={businessId}
                  platform={s.platform}
                  connected={s.connected}
                  oauthReady={s.oauth_supported && s.oauth_configured}
                />
              </div>
              {s.connected && s.account_meta && Object.keys(s.account_meta).length > 0 && (
                <details className="mt-3 text-xs text-slate-400">
                  <summary className="cursor-pointer hover:text-slate-200">Account details</summary>
                  <pre className="mt-2 text-[11px] bg-ink-900 rounded p-2 overflow-x-auto">
                    {JSON.stringify(s.account_meta, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="font-semibold mb-3">Media generation providers</h2>
        <div className="card divide-y divide-ink-700">
          {mediaProviders.map((p) => (
            <div key={p.name} className="py-3 first:pt-0 last:pb-0 flex items-center justify-between">
              <div>
                <div className="font-medium capitalize">{p.name}</div>
                <div className="text-xs text-slate-500">
                  {p.supports_video ? "images + video" : "images only"}
                </div>
              </div>
              {p.configured ? (
                <span className="badge badge-success">ready</span>
              ) : (
                <span className="badge badge-muted">add API key to .env</span>
              )}
            </div>
          ))}
          <div className="pt-3 text-xs text-slate-500">
            The first configured provider is used. Placeholder is always available so the pipeline
            never blocks — swap it out by adding an OpenAI / Replicate / Stability key.
          </div>
        </div>
      </section>
    </div>
  );
}
