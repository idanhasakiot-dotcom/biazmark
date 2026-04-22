"use client";

/**
 * IconBadge — serious replacement for emojis in hero cards.
 * Each kind is a clean SVG icon on a glowing gradient disc.
 */

type Kind = "bolt" | "phone" | "globe" | "lock" | "shield" | "chart" | "code" | "star";

const ICONS: Record<Kind, React.ReactNode> = {
  bolt: <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z" />,
  phone: (
    <>
      <rect x="5" y="2" width="14" height="20" rx="3" />
      <path d="M11 18h2" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20" />
    </>
  ),
  lock: (
    <>
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </>
  ),
  shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
  chart: (
    <>
      <path d="M3 3v18h18" />
      <path d="M7 14l4-4 4 4 5-6" />
    </>
  ),
  code: <path d="m16 18 6-6-6-6M8 6l-6 6 6 6" />,
  star: <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />,
};

const GRADIENTS: Record<string, [string, string]> = {
  indigo:  ["#6366f1", "#a855f7"],
  emerald: ["#10b981", "#06b6d4"],
  amber:   ["#f59e0b", "#ef4444"],
  rose:    ["#ec4899", "#f43f5e"],
  cyan:    ["#06b6d4", "#3b82f6"],
  slate:   ["#475569", "#1e293b"],
};

export default function IconBadge({
  kind,
  color = "indigo",
  size = 64,
}: {
  kind: Kind;
  color?: keyof typeof GRADIENTS;
  size?: number;
}) {
  const [a, b] = GRADIENTS[color];
  return (
    <div className="relative inline-block" style={{ width: size, height: size }}>
      {/* Outer glow */}
      <div className="absolute inset-0 rounded-2xl blur-2xl opacity-60"
           style={{ background: `linear-gradient(135deg, ${a}, ${b})` }} />
      {/* Inner disc */}
      <div
        className="relative w-full h-full rounded-2xl flex items-center justify-center overflow-hidden"
        style={{
          background: `linear-gradient(135deg, ${a}, ${b})`,
          boxShadow: `0 10px 40px -10px ${a}, inset 0 1px 0 rgba(255,255,255,0.2)`,
        }}
      >
        {/* Subtle grain on badge */}
        <div className="absolute inset-0 opacity-[0.15] mix-blend-overlay"
             style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")" }} />
        <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="relative" style={{ width: size * 0.5, height: size * 0.5 }}>
          {ICONS[kind]}
        </svg>
      </div>
    </div>
  );
}
