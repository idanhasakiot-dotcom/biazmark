"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function OptimizeButton({ campaignId }: { campaignId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function onOptimize() {
    setBusy(true);
    setMessage(null);
    try {
      const ev = await api.optimizeCampaign(campaignId);
      setMessage(ev?.reason || "Optimization cycle complete");
      router.refresh();
    } catch (e: any) {
      setMessage(e?.message || "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <button className="btn-primary" disabled={busy} onClick={onOptimize}>
        {busy ? "Analysing…" : "Run optimize cycle"}
      </button>
      {message && <div className="text-xs text-slate-400 max-w-xs text-right">{message}</div>}
    </div>
  );
}
