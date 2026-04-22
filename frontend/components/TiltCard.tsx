"use client";
import { useRef } from "react";

/**
 * 3D tilt card — rotates toward the mouse cursor.
 * Uses CSS transforms only (GPU, no JS animation loop).
 */
export default function TiltCard({
  children,
  className = "",
  intensity = 10,
}: { children: React.ReactNode; className?: string; intensity?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;  // 0..1
    const y = (e.clientY - r.top) / r.height;  // 0..1
    // Reduce to max ~6deg — elegant, not dramatic
    const soft = intensity * 0.6;
    const rotY = (x - 0.5) * soft * 2;
    const rotX = (0.5 - y) * soft * 2;
    el.style.transform = `perspective(1400px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(0)`;
    // Shine origin
    el.style.setProperty("--x", `${x * 100}%`);
    el.style.setProperty("--y", `${y * 100}%`);
  }
  function onLeave() {
    const el = ref.current;
    if (!el) return;
    el.style.transform = "perspective(1000px) rotateX(0) rotateY(0) translateZ(0)";
  }

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className={`relative transition-transform duration-200 ease-out ${className}`}
      style={{ transformStyle: "preserve-3d" }}
    >
      {/* Shine overlay following cursor */}
      <div
        className="absolute inset-0 rounded-[inherit] pointer-events-none opacity-0 hover:opacity-100 transition-opacity"
        style={{
          background:
            "radial-gradient(400px circle at var(--x, 50%) var(--y, 50%), rgba(255,255,255,0.12), transparent 40%)",
        }}
      />
      {children}
    </div>
  );
}
