"use client";
import { useEffect, useState } from "react";

// Cycles through multiple lines, typing each character on a realistic-ish cadence,
// pausing between lines, then restarting. Pure React, no deps.
export default function Typewriter({
  lines,
  loop = true,
  speed = 45,
  linePause = 1800,
  className,
}: {
  lines: string[];
  loop?: boolean;
  speed?: number;
  linePause?: number;
  className?: string;
}) {
  const [lineIdx, setLineIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [phase, setPhase] = useState<"type" | "pause" | "erase">("type");

  useEffect(() => {
    const current = lines[lineIdx] || "";
    let t: ReturnType<typeof setTimeout>;

    if (phase === "type") {
      if (charIdx < current.length) {
        t = setTimeout(() => setCharIdx((c) => c + 1), speed + Math.random() * 40);
      } else {
        t = setTimeout(() => setPhase("pause"), linePause);
      }
    } else if (phase === "pause") {
      t = setTimeout(() => setPhase("erase"), linePause);
    } else {
      if (charIdx > 0) {
        t = setTimeout(() => setCharIdx((c) => c - 1), 20);
      } else {
        const nxt = lineIdx + 1;
        if (nxt >= lines.length && !loop) return;
        setLineIdx(nxt % lines.length);
        setPhase("type");
      }
    }
    return () => clearTimeout(t);
  }, [phase, charIdx, lineIdx, lines, loop, speed, linePause]);

  const shown = (lines[lineIdx] || "").slice(0, charIdx);
  return (
    <span className={className}>
      {shown}
      <span className="inline-block w-[0.08em] h-[0.9em] bg-current ml-1 align-middle animate-pulse" />
    </span>
  );
}
