"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function ConnectButton({
  businessId,
  platform,
  connected,
  oauthReady,
}: {
  businessId: string;
  platform: string;
  connected: boolean;
  oauthReady: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onConnect() {
    setBusy(true);
    setError(null);
    try {
      const { authorise_url } = await api.startOAuth(businessId, platform);
      window.location.href = authorise_url;
    } catch (e: any) {
      setError(e?.message || "failed");
      setBusy(false);
    }
  }

  async function onDisconnect() {
    setBusy(true);
    setError(null);
    try {
      const conns = await api.listConnections(businessId);
      const match = conns.find((c) => c.platform === platform);
      if (match) {
        await api.deleteConnection(match.id);
        router.refresh();
      }
    } catch (e: any) {
      setError(e?.message || "failed");
    } finally {
      setBusy(false);
    }
  }

  if (connected) {
    return (
      <div className="flex flex-col items-end gap-1">
        <button className="btn-ghost text-danger" disabled={busy} onClick={onDisconnect}>
          Disconnect
        </button>
        {error && <div className="text-xs text-danger">{error}</div>}
      </div>
    );
  }

  if (!oauthReady) {
    return <span className="text-xs text-slate-500">—</span>;
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button className="btn-primary" disabled={busy} onClick={onConnect}>
        {busy ? "Connecting…" : "Connect"}
      </button>
      {error && <div className="text-xs text-danger">{error}</div>}
    </div>
  );
}
