"use client";
import { useEffect, useRef, useState } from "react";

/**
 * Parallax wrapper — moves contained content slower (or faster) than scroll.
 * speed = 0.5 → half as fast (lingers behind)
 * speed = -0.3 → moves opposite direction
 */
export default function Parallax({
  children,
  speed = 0.3,
  className = "",
}: { children: React.ReactNode; speed?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [y, setY] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const rect = el.getBoundingClientRect();
        const vh = window.innerHeight;
        // position: -vh (just below) to +vh (just above) → progress -1..1
        const progress = ((rect.top + rect.height / 2) - vh / 2) / vh;
        setY(-progress * 100 * speed);
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [speed]);

  return (
    <div
      ref={ref}
      className={className}
      style={{ transform: `translate3d(0, ${y}px, 0)`, willChange: "transform" }}
    >
      {children}
    </div>
  );
}
