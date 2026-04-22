"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, type Tier } from "@/lib/api";
import Reveal from "@/components/Reveal";
import FloatingOrbs from "@/components/FloatingOrbs";

const TIERS: { value: Tier; label: string; desc: string; accent: string }[] = [
  { value: "free", label: "Free", desc: "Local LLM · preview only · manual approve", accent: "from-slate-500 to-slate-700" },
  { value: "basic", label: "Basic", desc: "Claude Haiku · 1 platform live · daily loop", accent: "from-amber-400 to-rose-500" },
  { value: "pro", label: "Pro", desc: "Claude Sonnet · 5 platforms · hourly loop", accent: "from-indigo-500 to-purple-600" },
  { value: "enterprise", label: "Enterprise", desc: "Claude Opus · all platforms · autonomous agents", accent: "from-emerald-500 to-cyan-600" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    description: "",
    website: "",
    industry: "",
    target_audience: "",
    goals: "",
    tier: "basic" as Tier,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upd = (k: keyof typeof form) => (e: React.ChangeEvent<any>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const b = await api.createBusiness(form);
      router.push(`/dashboard/${b.id}`);
    } catch (err: any) {
      setError(err?.message || "Failed to create business");
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto relative">
      <div className="absolute -top-20 -left-20 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -top-10 -right-20 w-64 h-64 bg-pink-500/10 rounded-full blur-3xl pointer-events-none" />

      <Reveal dir="up">
        <h1 className="text-4xl font-bold mb-2">
          Onboard a <span className="text-gradient">business</span>
        </h1>
        <p className="text-slate-400 mb-8">
          The more detail you share, the better the first research + strategy pass. You can edit everything later.
        </p>
      </Reveal>

      <form onSubmit={onSubmit} className="space-y-5">
        <Reveal dir="up" delay={50}>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="label">Name *</label>
              <input required className="input" value={form.name} onChange={upd("name")} placeholder="e.g. Acme Coffee" />
            </div>
            <div>
              <label className="label">Website</label>
              <input className="input" value={form.website} onChange={upd("website")} placeholder="acme.com" />
            </div>
          </div>
        </Reveal>

        <Reveal dir="up" delay={100}>
          <div>
            <label className="label">Description</label>
            <textarea className="textarea" value={form.description} onChange={upd("description")}
              placeholder="What does this business/app/idea do? What makes it different?" />
          </div>
        </Reveal>

        <Reveal dir="up" delay={150}>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="label">Industry / niche</label>
              <input className="input" value={form.industry} onChange={upd("industry")} placeholder="specialty coffee, B2B SaaS, ..." />
            </div>
            <div>
              <label className="label">Goals</label>
              <input className="input" value={form.goals} onChange={upd("goals")} placeholder="awareness, leads, signups, retention" />
            </div>
          </div>
        </Reveal>

        <Reveal dir="up" delay={200}>
          <div>
            <label className="label">Target audience</label>
            <textarea className="textarea" value={form.target_audience} onChange={upd("target_audience")}
              placeholder="Who are they? Where do they hang out? What do they care about?" />
          </div>
        </Reveal>

        <Reveal dir="up" delay={250}>
          <div>
            <label className="label">Tier</label>
            <div className="grid md:grid-cols-2 gap-3">
              {TIERS.map((t) => (
                <label
                  key={t.value}
                  className={`card cursor-pointer relative overflow-hidden transition-all ${
                    form.tier === t.value ? "!border-accent-500 ring-2 ring-accent-500/40" : ""
                  }`}
                >
                  {form.tier === t.value && (
                    <div className={`absolute inset-0 bg-gradient-to-br ${t.accent} opacity-[0.08] pointer-events-none`} />
                  )}
                  <input
                    type="radio"
                    name="tier"
                    value={t.value}
                    checked={form.tier === t.value}
                    onChange={() => setForm((f) => ({ ...f, tier: t.value }))}
                    className="sr-only"
                  />
                  <div className="relative">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full bg-gradient-to-br ${t.accent}`} />
                      <span className="font-semibold">{t.label}</span>
                    </div>
                    <div className="text-sm text-slate-400 mt-1">{t.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </Reveal>

        {error && (
          <Reveal dir="up">
            <div className="card !border-danger/40 text-danger">{error}</div>
          </Reveal>
        )}

        <Reveal dir="up" delay={300}>
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={submitting} className="btn-primary px-6 py-3">
              {submitting ? "Creating…" : "Create & start research →"}
            </button>
            <button type="button" onClick={() => router.back()} className="btn-ghost">
              Cancel
            </button>
          </div>
        </Reveal>
      </form>
    </div>
  );
}
