"use client";
import { useEffect, useRef, useState } from "react";

type Direction = "up" | "down" | "left" | "right" | "scale" | "fade";

const OFFSETS: Record<Direction, string> = {
  up:    "translate3d(0, 40px, 0)",
  down:  "translate3d(0, -40px, 0)",
  left:  "translate3d(40px, 0, 0)",
  right: "translate3d(-40px, 0, 0)",
  scale: "scale(0.92)",
  fade:  "translate3d(0, 0, 0)",
};

/**
 * Scroll-triggered reveal.
 * By default re-triggers whenever the element enters the viewport —
 * so scrolling UP then back DOWN re-animates. Set once={true} to freeze.
 */
export default function Reveal({
  children,
  dir = "up",
  delay = 0,
  once = false,
  className = "",
}: {
  children: React.ReactNode;
  dir?: Direction;
  delay?: number;
  once?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setShown(true);
            if (once) io.disconnect();
          } else if (!once) {
            setShown(false);
          }
        }
      },
      { threshold: 0.08, rootMargin: "-30px 0px" }
    );
    io.observe(ref.current);
    return () => io.disconnect();
  }, [once]);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? "translate3d(0,0,0) scale(1)" : OFFSETS[dir],
        transition: `opacity 900ms cubic-bezier(0.16,1,0.3,1) ${delay}ms, transform 900ms cubic-bezier(0.16,1,0.3,1) ${delay}ms`,
        willChange: "opacity, transform",
      }}
    >
      {children}
    </div>
  );
}
