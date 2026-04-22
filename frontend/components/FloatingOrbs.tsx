"use client";

// Purely decorative floating SVG orbs scattered through a section.
// Drop inside any `relative` container. Negative-z sits under content.
// Motion: float-a/b/c keyframes (defined in globals.css).

export default function FloatingOrbs({
  count = 6,
  seed = 0,
  colors = ["#8b5cf6", "#ec4899", "#06b6d4"],
}: { count?: number; seed?: number; colors?: string[] }) {
  // deterministic-ish positions based on seed
  const rand = (n: number) => {
    const x = Math.sin(seed * 9301 + n * 49297) * 233280;
    return x - Math.floor(x);
  };
  const orbs = Array.from({ length: count }, (_, i) => ({
    size: 40 + rand(i * 3) * 120,
    top: rand(i * 5) * 100,
    left: rand(i * 7) * 100,
    color: colors[i % colors.length],
    anim: ["float-a", "float-b", "float-c"][i % 3],
    delay: rand(i * 11) * 5,
    duration: 12 + rand(i * 13) * 10,
  }));

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none -z-0">
      {orbs.map((o, i) => (
        <span
          key={i}
          className="absolute rounded-full blur-3xl opacity-30 mix-blend-screen"
          style={{
            width: o.size,
            height: o.size,
            top: `${o.top}%`,
            left: `${o.left}%`,
            background: `radial-gradient(circle, ${o.color}, transparent 70%)`,
            animation: `${o.anim} ${o.duration}s ease-in-out ${o.delay}s infinite`,
          }}
        />
      ))}
    </div>
  );
}
