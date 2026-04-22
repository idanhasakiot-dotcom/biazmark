"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

export function StrategyActions({ businessId }: { businessId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setError(null);
    try {
      await fn();
      router.refresh();
    } catch (e: any) {
      setError(e?.message || "failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex gap-2">
        <button
          className="btn-secondary"
          disabled={!!busy}
          onClick={() => run("research", () => api.runResearch(businessId))}
        >
          {busy === "research" ? "Researching…" : "Run research"}
        </button>
        <button
          className="btn-secondary"
          disabled={!!busy}
          onClick={() => run("strategy", () => api.runStrategy(businessId))}
        >
          {busy === "strategy" ? "Generating…" : "Generate strategy"}
        </button>
        <button
          className="btn-primary"
          disabled={!!busy}
          onClick={async () => {
            setBusy("publish");
            setError(null);
            try {
              const strategies = await api.listStrategies(businessId);
              const latest = strategies[0];
              if (!latest) {
                setError("No strategy yet — generate one first.");
                return;
              }
              await api.publishStrategy(latest.id, "preview");
              router.refresh();
            } catch (e: any) {
              setError(e?.message || "failed");
            } finally {
              setBusy(null);
            }
          }}
        >
          {busy === "publish" ? "Publishing…" : "Publish latest strategy"}
        </button>
      </div>
      {error && <div className="text-xs text-danger">{error}</div>}
    </div>
  );
}
