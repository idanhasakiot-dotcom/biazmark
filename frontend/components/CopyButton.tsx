"use client";

import { useState } from "react";

/**
 * CopyButton — one-click copy to clipboard with visual feedback.
 *
 * Falls back cleanly on old browsers / HTTP contexts (where `clipboard` API is
 * unavailable) by using a transient textarea + `execCommand("copy")`.
 */
export default function CopyButton({
  text,
  label = "Copy",
  className = "",
  variant = "primary",
}: {
  text: string;
  label?: string;
  className?: string;
  variant?: "primary" | "ghost" | "minimal";
}) {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);

  async function onCopy() {
    setError(false);
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(ta);
        if (!ok) throw new Error("copy failed");
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      setError(true);
      setTimeout(() => setError(false), 1600);
    }
  }

  const base =
    variant === "primary"
      ? "btn-primary"
      : variant === "ghost"
        ? "btn-ghost"
        : "inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-100 transition-colors";

  return (
    <button
      type="button"
      onClick={onCopy}
      className={`${base} ${className}`}
      aria-label="Copy to clipboard"
    >
      {copied ? (
        <>
          <CheckIcon />
          <span>Copied!</span>
        </>
      ) : error ? (
        <>
          <span>× Failed</span>
        </>
      ) : (
        <>
          <CopyIcon />
          <span>{label}</span>
        </>
      )}
    </button>
  );
}

function CopyIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
      aria-hidden="true"
    >
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
      aria-hidden="true"
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}
