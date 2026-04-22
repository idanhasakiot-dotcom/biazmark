import Link from "next/link";
import { api } from "@/lib/api";
import FloatingOrbs from "@/components/FloatingOrbs";
import Reveal from "@/components/Reveal";
import TiltCard from "@/components/TiltCard";
import SplitText from "@/components/SplitText";
import MagneticButton from "@/components/MagneticButton";
import Typewriter from "@/components/Typewriter";
import AnimatedCounter from "@/components/AnimatedCounter";
import IconBadge from "@/components/IconBadge";
import CopyButton from "@/components/CopyButton";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [businesses, tier, connectors] = await Promise.all([
    api.listBusinesses().catch(() => []),
    api.tier().catch(() => null),
    api.connectors().catch(() => []),
  ]);

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="relative text-center py-16 overflow-hidden rounded-3xl">
        <div className="aurora aurora-1" />
        <div className="aurora aurora-2" />
        <div className="aurora aurora-3" />
        <FloatingOrbs count={8} seed={1} />
        <div className="relative z-10 space-y-6">
          <Reveal dir="up">
            <div className="inline-flex items-center gap-2 rounded-full glass px-3 py-1 text-xs text-slate-300">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Autonomous · Self-improving · Live
            </div>
          </Reveal>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.05]">
            <SplitText text="Marketing that" /><br />
            <span className="text-gradient">
              <SplitText text="runs itself." delay={400} />
            </span>
          </h1>
          <Reveal dir="up" delay={200}>
            <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto">
              Brief in, campaigns out. Five AI agents handle research, strategy, content,
              publishing, analytics, and optimization — end to end.
            </p>
          </Reveal>
          <Reveal dir="up" delay={400}>
            <div className="text-slate-500 text-sm font-mono min-h-[1.5em]">
              Now generating:{" "}
              <span className="text-slate-200">
                <Typewriter
                  lines={[
                    "Meta ads for a coffee DTC brand",
                    "LinkedIn posts for a B2B SaaS",
                    "Articles for a wellness app",
                    "TikTok scripts for a fashion label",
                    "Email drip for a bookshop",
                  ]}
                />
              </span>
            </div>
          </Reveal>
          <Reveal dir="up" delay={600}>
            <div className="flex flex-wrap gap-3 justify-center pt-4">
              <MagneticButton href="/onboarding" className="btn-primary text-base px-6 py-3">
                Onboard a business →
              </MagneticButton>
              <Link href="/install" className="btn-secondary text-base px-6 py-3">
                Install in 2 minutes
              </Link>
              <Link href="/docs" className="btn-ghost text-base px-6 py-3">
                API docs
              </Link>
            </div>
          </Reveal>
          <Reveal dir="up" delay={800}>
            <div className="mt-8 max-w-xl mx-auto">
              <div className="glass rounded-xl px-4 py-3 flex items-center gap-3 justify-between group">
                <code className="text-xs md:text-sm font-mono text-slate-300 truncate">
                  iwr -useb https://biazmark.vercel.app/install.ps1 | iex
                </code>
                <CopyButton
                  text="iwr -useb https://biazmark.vercel.app/install.ps1 | iex"
                  label=""
                  variant="minimal"
                />
              </div>
              <div className="text-[11px] text-slate-500 mt-2 text-center">
                Windows installer · <Link href="/install" className="hover:text-slate-300 underline underline-offset-2">see Mac, Linux, Docker →</Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Stats */}
      <section className="grid md:grid-cols-3 gap-4">
        <Reveal dir="up" delay={0}>
          <TiltCard intensity={6}>
            <div className="card relative overflow-hidden">
              <div className="absolute -top-12 -right-12 w-32 h-32 bg-indigo-500/20 rounded-full blur-2xl" />
              <div className="relative">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Current tier</div>
                  <IconBadge kind="bolt" color="indigo" size={36} />
                </div>
                <div className="text-3xl font-bold capitalize mt-3">{tier?.tier ?? "—"}</div>
                <div className="text-sm text-slate-400 mt-1">
                  {tier?.llm_model} · {tier?.research_depth} research
                </div>
                <div className="text-sm text-slate-400">
                  {tier?.autonomous_agents
                    ? "Autonomous agents on"
                    : `Loop: ${tier?.loop_interval_seconds ? `${Math.round(tier.loop_interval_seconds / 60)} min` : "manual"}`}
                </div>
              </div>
            </div>
          </TiltCard>
        </Reveal>
        <Reveal dir="up" delay={100}>
          <TiltCard intensity={6}>
            <div className="card relative overflow-hidden">
              <div className="absolute -top-12 -right-12 w-32 h-32 bg-pink-500/20 rounded-full blur-2xl" />
              <div className="relative">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Businesses</div>
                  <IconBadge kind="chart" color="rose" size={36} />
                </div>
                <div className="text-3xl font-bold mt-3">
                  <AnimatedCounter value={businesses.length} />
                </div>
                <div className="text-sm text-slate-400 mt-1">
                  {businesses.length > 0 ? "Managed in this instance" : "None yet — onboard one"}
                </div>
              </div>
            </div>
          </TiltCard>
        </Reveal>
        <Reveal dir="up" delay={200}>
          <TiltCard intensity={6}>
            <div className="card relative overflow-hidden">
              <div className="absolute -top-12 -right-12 w-32 h-32 bg-cyan-500/20 rounded-full blur-2xl" />
              <div className="relative">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-slate-500">Connectors</div>
                  <IconBadge kind="globe" color="cyan" size={36} />
                </div>
                <div className="text-3xl font-bold mt-3">
                  <AnimatedCounter value={connectors.length} />
                </div>
                <div className="text-sm text-slate-400 mt-1 line-clamp-2">
                  {connectors.map((c) => c.display_name).join(" · ")}
                </div>
              </div>
            </div>
          </TiltCard>
        </Reveal>
      </section>

      {/* Capabilities row */}
      <section>
        <Reveal dir="up">
          <h2 className="text-2xl font-semibold mb-6">Five agents. One loop.</h2>
        </Reveal>
        <div className="grid md:grid-cols-5 gap-3">
          {[
            { kind: "chart", color: "indigo", name: "Researcher", desc: "Market + competitors" },
            { kind: "bolt", color: "rose", name: "Strategist", desc: "Positioning + channels" },
            { kind: "star", color: "amber", name: "Creator", desc: "Posts · ads · articles · emails" },
            { kind: "globe", color: "cyan", name: "Analyst", desc: "Reads metrics, finds signal" },
            { kind: "shield", color: "emerald", name: "Optimizer", desc: "Kills losers, scales winners" },
          ].map((a, i) => (
            <Reveal key={a.name} dir="up" delay={i * 80}>
              <div className="card hover:border-accent-500/40 transition-colors">
                <IconBadge kind={a.kind as any} color={a.color as any} size={44} />
                <div className="mt-3 font-semibold">{a.name}</div>
                <div className="text-xs text-slate-400 mt-1">{a.desc}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Businesses */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <Reveal dir="left">
            <h2 className="text-2xl font-semibold">Your businesses</h2>
          </Reveal>
          <Reveal dir="right">
            <Link href="/onboarding" className="btn-secondary">+ New</Link>
          </Reveal>
        </div>
        {businesses.length === 0 ? (
          <Reveal dir="up">
            <div className="card text-center py-20 relative overflow-hidden">
              <FloatingOrbs count={4} seed={3} colors={["#6366f1", "#ec4899"]} />
              <div className="relative text-slate-400">
                <div className="text-5xl mb-3 opacity-40">✨</div>
                <div>No businesses yet. Start by{" "}
                  <Link href="/onboarding" className="text-accent-400 hover:underline">
                    onboarding one
                  </Link>.
                </div>
              </div>
            </div>
          </Reveal>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {businesses.map((b, i) => (
              <Reveal key={b.id} dir="up" delay={i * 60}>
                <Link href={`/dashboard/${b.id}`} className="block">
                  <TiltCard intensity={5}>
                    <div className="card card-hover">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-lg font-semibold">{b.name}</div>
                          <div className="text-sm text-slate-400 mt-1 line-clamp-2">
                            {b.description || "—"}
                          </div>
                        </div>
                        <span className={`badge ${tierBadgeClass(b.tier)} capitalize`}>
                          {b.tier}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-4 text-xs text-slate-500">
                        {b.industry && <span>{b.industry}</span>}
                        {b.website && (
                          <>
                            <span>·</span>
                            <span className="truncate">{b.website}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </TiltCard>
                </Link>
              </Reveal>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function tierBadgeClass(tier: string) {
  switch (tier) {
    case "enterprise":
      return "badge-success";
    case "pro":
      return "badge-accent";
    case "basic":
      return "badge-warning";
    default:
      return "badge-muted";
  }
}
