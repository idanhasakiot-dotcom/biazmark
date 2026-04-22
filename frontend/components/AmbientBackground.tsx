"use client";
import { useEffect, useRef } from "react";

/**
 * Ambient abstract canvas background — subtle animated mesh + flowing particles.
 * Sits behind all content with `fixed inset-0 -z-10`. GPU-light, 60fps on any device.
 *
 * Props:
 *   variant: "mesh" (default) | "constellation" | "waves"
 *   intensity: 0..1 (default 0.6) — lower = subtler
 */
export default function AmbientBackground({
  variant = "mesh",
  intensity = 0.6,
}: {
  variant?: "mesh" | "constellation" | "waves";
  intensity?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let rafId = 0;
    let w = 0, h = 0, dpr = 1;

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      if (!canvas) return;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      if (!ctx) return;
      ctx.scale(dpr, dpr);
    }

    resize();
    window.addEventListener("resize", resize, { passive: true });

    if (variant === "constellation") {
      const N = Math.min(60, Math.floor((w * h) / 30000));
      const stars: { x: number; y: number; vx: number; vy: number }[] = [];
      for (let i = 0; i < N; i++) {
        stars.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.15,
          vy: (Math.random() - 0.5) * 0.15,
        });
      }
      const draw = () => {
        if (!ctx) return;
        ctx.clearRect(0, 0, w, h);
        // stars
        for (const s of stars) {
          s.x += s.vx;
          s.y += s.vy;
          if (s.x < 0 || s.x > w) s.vx *= -1;
          if (s.y < 0 || s.y > h) s.vy *= -1;
          ctx.fillStyle = `rgba(255,255,255,${0.5 * intensity})`;
          ctx.beginPath();
          ctx.arc(s.x, s.y, 1.2, 0, Math.PI * 2);
          ctx.fill();
        }
        // connections
        for (let i = 0; i < stars.length; i++) {
          for (let j = i + 1; j < stars.length; j++) {
            const dx = stars[i].x - stars[j].x;
            const dy = stars[i].y - stars[j].y;
            const d2 = dx * dx + dy * dy;
            if (d2 < 140 * 140) {
              const a = (1 - Math.sqrt(d2) / 140) * 0.15 * intensity;
              ctx.strokeStyle = `rgba(139,92,246,${a})`;
              ctx.lineWidth = 0.5;
              ctx.beginPath();
              ctx.moveTo(stars[i].x, stars[i].y);
              ctx.lineTo(stars[j].x, stars[j].y);
              ctx.stroke();
            }
          }
        }
        rafId = requestAnimationFrame(draw);
      };
      draw();
    } else if (variant === "waves") {
      let t = 0;
      const draw = () => {
        if (!ctx) return;
        ctx.clearRect(0, 0, w, h);
        for (let i = 0; i < 3; i++) {
          const hue = [260, 320, 200][i];
          ctx.strokeStyle = `hsla(${hue},70%,60%,${0.1 * intensity})`;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          for (let x = 0; x <= w; x += 10) {
            const y = h / 2 + Math.sin((x + t * (1 + i * 0.3)) / (80 + i * 30)) * (60 + i * 30) + (i - 1) * 80;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }
          ctx.stroke();
        }
        t += 0.7;
        rafId = requestAnimationFrame(draw);
      };
      draw();
    } else {
      // mesh: moving soft blobs
      const blobs = [
        { x: w * 0.2, y: h * 0.3, r: 260, vx: 0.2, vy: 0.15, c: [139, 92, 246] },
        { x: w * 0.8, y: h * 0.6, r: 220, vx: -0.18, vy: 0.2, c: [236, 72, 153] },
        { x: w * 0.5, y: h * 0.8, r: 200, vx: 0.22, vy: -0.17, c: [6, 182, 212] },
      ];
      const draw = () => {
        if (!ctx) return;
        ctx.clearRect(0, 0, w, h);
        for (const b of blobs) {
          b.x += b.vx;
          b.y += b.vy;
          if (b.x < -100 || b.x > w + 100) b.vx *= -1;
          if (b.y < -100 || b.y > h + 100) b.vy *= -1;
          const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);
          const [r, G, B] = b.c;
          g.addColorStop(0, `rgba(${r},${G},${B},${0.22 * intensity})`);
          g.addColorStop(1, `rgba(${r},${G},${B},0)`);
          ctx.fillStyle = g;
          ctx.fillRect(b.x - b.r, b.y - b.r, b.r * 2, b.r * 2);
        }
        rafId = requestAnimationFrame(draw);
      };
      draw();
    }

    // Pause when tab not visible (battery-friendly)
    const onVis = () => {
      if (document.hidden) cancelAnimationFrame(rafId);
    };
    document.addEventListener("visibilitychange", onVis);

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [variant, intensity]);

  return (
    <canvas
      ref={ref}
      className="fixed inset-0 -z-10 pointer-events-none"
      aria-hidden="true"
    />
  );
}
