"use client";
import { useRef } from "react";
import Link from "next/link";

/**
 * Button/link that pulls toward the cursor when hovering within its area.
 * Feels premium, used in brands like Stripe and Linear.
 */
export default function MagneticButton({
  href,
  children,
  className = "",
  strength = 18,
}: { href: string; children: React.ReactNode; className?: string; strength?: number }) {
  const ref = useRef<HTMLAnchorElement>(null);

  function onMove(e: React.MouseEvent<HTMLAnchorElement>) {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = e.clientX - r.left - r.width / 2;
    const y = e.clientY - r.top - r.height / 2;
    el.style.transform = `translate3d(${x * 0.3 * (strength / 18)}px, ${y * 0.3 * (strength / 18)}px, 0)`;
  }
  function onLeave() {
    const el = ref.current;
    if (!el) return;
    el.style.transform = "translate3d(0, 0, 0)";
  }

  return (
    <Link
      ref={ref}
      href={href}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className={`inline-flex items-center gap-2 transition-transform duration-300 ease-out ${className}`}
    >
      {children}
    </Link>
  );
}
