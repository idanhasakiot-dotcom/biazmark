"use client";
import { useEffect, useRef, useState } from "react";

/**
 * Animates a number from 0 → value when it enters the viewport.
 * Supports prefix/suffix (like "$", "+", "%", "m", "d", "∞").
 * If value is non-numeric (e.g. "< 5m"), shows as-is without animation.
 */
export default function AnimatedCounter({
  value,
  duration = 1400,
  className = "",
}: { value: string | number; duration?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [display, setDisplay] = useState<string>("0");

  // Parse number (may be embedded: "120+" → 120, "$5K" → 5, etc.)
  const target = typeof value === "number"
    ? value
    : parseFloat(String(value).replace(/[^\d.-]/g, "")) || 0;
  const prefix = typeof value === "string" ? (String(value).match(/^[^\d-]+/)?.[0] || "") : "";
  const suffix = typeof value === "string" ? (String(value).match(/[^\d.]+$/)?.[0] || "") : "";
  const isNumeric = target > 0;

  useEffect(() => {
    if (!ref.current || !isNumeric) {
      setDisplay(String(value));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const tick = (now: number) => {
        const p = Math.min(1, (now - start) / duration);
        // ease-out cubic
        const eased = 1 - Math.pow(1 - p, 3);
        const cur = Math.round(target * eased);
        setDisplay(`${prefix}${cur}${suffix}`);
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { threshold: 0.4 });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [value, duration, target, prefix, suffix, isNumeric]);

  return <span ref={ref} className={className}>{isNumeric ? display : String(value)}</span>;
}
