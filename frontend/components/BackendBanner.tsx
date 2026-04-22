"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

/**
 * Shows a dismissible banner when the backend API is unreachable.
 *
 * The Vercel-hosted demo doesn't have a backend wired up by default, so the
 * dashboard pages would look broken. This banner explains why + points at the
 * install page so visitors can spin up their own stack.
 *
 * When a backend IS reachable (or the user has dismissed the banner) we render
 * nothing — no layout shift, no chrome.
 */
export default function BackendBanner() {
  const [state, setState] = useState<"checking" | "ok" | "down" | "dismissed">("checking");

  useEffect(() => {
    if (sessionStorage.getItem("biazmark.banner.dismissed") === "1") {
      setState("dismissed");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const base =
          (typeof window !== "undefined" && localStorage.getItem("biazmark.apiBase")) ||
          process.env.NEXT_PUBLIC_API_URL ||
          "";
        const r = await fetch(`${base}/api/health`, { cache: "no-store" });
        if (!cancelled) setState(r.ok ? "ok" : "down");
      } catch {
        if (!cancelled) setState("down");
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (state !== "down") return null;

  return (
    <div
      className="relative z-30 border-b border-amber-500/20"
      style={{ background: "linear-gradient(90deg, rgba(245,158,11,0.08), rgba(236,72,153,0.08))" }}
    >
      <div className="max-w-6xl mx-auto px-6 py-2.5 flex items-center justify-between gap-3 text-sm">
        <div className="flex items-center gap-2 text-amber-200 min-w-0">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse shrink-0" />
          <span className="truncate">
            <span className="font-semibold">Demo mode.</span>{" "}
            <span className="text-amber-100/80">
              The backend isn't wired up here. Install in 2 minutes to get the full autonomous loop.
            </span>
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Link href="/install" className="btn-ghost !py-1 !px-2 text-amber-200 hover:text-white">
            Install →
          </Link>
          <button
            type="button"
            aria-label="Dismiss"
            onClick={() => {
              sessionStorage.setItem("biazmark.banner.dismissed", "1");
              setState("dismissed");
            }}
            className="text-amber-200/60 hover:text-amber-100 px-1"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  );
}
