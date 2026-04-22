"use client";
import { useEffect, useRef, useState } from "react";

/**
 * SplitText — splits text into individual letters that animate into view
 * one by one with a staggered wave. Each letter rises from below + fades in.
 * Triggers once in view.
 */
export default function SplitText({
  text,
  delay = 0,
  stagger = 40,
  className = "",
}: { text: string; delay?: number; stagger?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setTimeout(() => setShown(true), delay);
          io.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    io.observe(ref.current);
    return () => io.disconnect();
  }, [delay]);

  const chars = Array.from(text);

  return (
    <span ref={ref} className={`inline-block ${className}`} aria-label={text}>
      {chars.map((ch, i) => (
        <span
          key={i}
          aria-hidden="true"
          className="inline-block"
          style={{
            opacity: shown ? 1 : 0,
            transform: shown ? "translate3d(0,0,0)" : "translate3d(0, 0.6em, 0) rotate(8deg)",
            transition: `opacity 700ms cubic-bezier(0.16,1,0.3,1) ${i * stagger}ms, transform 700ms cubic-bezier(0.16,1,0.3,1) ${i * stagger}ms`,
            willChange: "opacity, transform",
          }}
        >
          {ch === " " ? "\u00A0" : ch}
        </span>
      ))}
    </span>
  );
}
