"use client";

import { useState } from "react";
import FloatingOrbs from "@/components/FloatingOrbs";
import Reveal from "@/components/Reveal";
import CopyButton from "@/components/CopyButton";
import IconBadge from "@/components/IconBadge";

type Platform = "windows" | "mac" | "linux" | "android" | "docker" | "vercel";

const CMDS: Record<Platform, { label: string; desc: string; cmd: string; hint?: string }> = {
  windows: {
    label: "Windows",
    desc: "PowerShell one-liner",
    cmd: `iwr -useb https://biazmark.vercel.app/install.ps1 | iex`,
    hint: "Opens PowerShell, downloads the installer, and runs it. Installs Git + Docker via winget if missing.",
  },
  mac: {
    label: "macOS",
    desc: "Terminal one-liner",
    cmd: `curl -fsSL https://biazmark.vercel.app/install.sh | bash`,
    hint: "Paste into Terminal. Requires Docker Desktop running.",
  },
  linux: {
    label: "Linux",
    desc: "bash one-liner",
    cmd: `curl -fsSL https://biazmark.vercel.app/install.sh | bash`,
    hint: "Requires docker + docker-compose-plugin.",
  },
  android: {
    label: "Android",
    desc: "Signed APK — install directly",
    cmd: `https://biazmark.vercel.app/Biazmark.apk`,
    hint: "Download, then open the file on your phone. Enable 'Install from unknown sources' for your browser when prompted. 3 MB.",
  },
  docker: {
    label: "Docker",
    desc: "Manual compose",
    cmd: `git clone https://github.com/biazmark/biazmark.git
cd biazmark
cp .env.example .env
# edit .env — at least set ANTHROPIC_API_KEY
docker compose up -d`,
    hint: "Full control. Edit .env before bringing the stack up.",
  },
  vercel: {
    label: "Vercel + Railway",
    desc: "Production deploy",
    cmd: `# 1. Frontend → Vercel
vercel --cwd frontend
# 2. Backend → Railway (or Fly / Render)
cd backend && railway up
# 3. In Vercel project settings:
#    BIAZMARK_BACKEND_URL = <your Railway URL>`,
    hint: "Zero-ops production setup. Vercel runs the UI, Railway runs the Python backend + worker.",
  },
};

export default function InstallPage() {
  const [active, setActive] = useState<Platform>(detectPlatform());

  const current = CMDS[active];
  const oneliner = current.cmd.split("\n")[0];

  return (
    <div className="space-y-10">
      {/* Hero */}
      <section className="relative text-center py-12 rounded-3xl overflow-hidden">
        <div className="aurora aurora-1" />
        <div className="aurora aurora-2" />
        <FloatingOrbs count={6} seed={2} />
        <div className="relative z-10">
          <Reveal dir="up">
            <div className="inline-flex items-center gap-2 rounded-full glass px-3 py-1 text-xs text-slate-300 mb-4">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              One-click install
            </div>
            <h1 className="text-4xl md:text-5xl font-bold mb-3">
              Get running in{" "}
              <span className="text-gradient">under 2 minutes</span>
            </h1>
            <p className="text-slate-400 max-w-xl mx-auto">
              Copy one line into your terminal, or download the installer and double-click.
              That's it.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Platform tabs */}
      <section>
        <div className="flex flex-wrap gap-2 justify-center mb-5">
          {(Object.keys(CMDS) as Platform[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setActive(p)}
              className={`btn ${
                active === p ? "btn-primary" : "btn-secondary"
              }`}
            >
              {CMDS[p].label}
            </button>
          ))}
        </div>

        <Reveal dir="up" key={active}>
          <div className="card max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <IconBadge kind="code" color="indigo" size={32} />
                  <div>
                    <div className="font-semibold">{current.label}</div>
                    <div className="text-xs text-slate-400">{current.desc}</div>
                  </div>
                </div>
              </div>
              <CopyButton text={current.cmd} label="Copy" variant="primary" />
            </div>

            {current.hint && (
              <div className="text-xs text-slate-500 mb-3">{current.hint}</div>
            )}

            <div className="relative group">
              <pre className="bg-ink-900 border border-ink-700 rounded-xl p-4 overflow-x-auto text-sm font-mono text-slate-200">
                <code>{current.cmd}</code>
              </pre>
              <div className="absolute top-2 right-2">
                <CopyButton text={current.cmd} label="" variant="minimal" />
              </div>
            </div>

            {/* Quick actions */}
            <div className="flex flex-wrap gap-2 mt-4">
              {active === "windows" && (
                <>
                  <OpenTerminalButton cmd={oneliner} platform="windows" />
                  <a
                    href="/install.bat"
                    download="biazmark-install.bat"
                    className="btn-secondary"
                  >
                    <DownloadIcon /> Download .bat (double-click)
                  </a>
                  <a
                    href="/install.ps1"
                    download="biazmark-install.ps1"
                    className="btn-ghost"
                  >
                    .ps1 script
                  </a>
                </>
              )}
              {(active === "mac" || active === "linux") && (
                <>
                  <OpenTerminalButton cmd={oneliner} platform={active} />
                  <a
                    href="/install.sh"
                    download="biazmark-install.sh"
                    className="btn-secondary"
                  >
                    <DownloadIcon /> Download .sh
                  </a>
                </>
              )}
              {active === "android" && (
                <>
                  <a
                    href="/Biazmark.apk"
                    download="Biazmark.apk"
                    className="btn-primary"
                  >
                    <DownloadIcon /> Download APK (3 MB)
                  </a>
                  <a
                    href="/Biazmark.apk"
                    className="btn-secondary"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Install directly
                  </a>
                </>
              )}
              {active === "docker" && (
                <a
                  href="https://github.com/biazmark/biazmark"
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary"
                >
                  <GitHubIcon /> View on GitHub
                </a>
              )}
              {active === "vercel" && (
                <a
                  href="https://vercel.com/new/clone?repository-url=https://github.com/biazmark/biazmark&root-directory=frontend"
                  target="_blank"
                  rel="noreferrer"
                  className="btn-secondary"
                >
                  Deploy to Vercel →
                </a>
              )}
            </div>
          </div>
        </Reveal>
      </section>

      {/* What happens next */}
      <section className="max-w-3xl mx-auto">
        <Reveal dir="up">
          <h2 className="text-xl font-semibold mb-4">What happens</h2>
        </Reveal>
        <div className="grid md:grid-cols-3 gap-3">
          {[
            { n: "1", title: "Download + deps", desc: "Clones repo, installs Docker + Git via winget if needed" },
            { n: "2", title: "Configure", desc: "Creates .env from template; prompts for your Anthropic API key" },
            { n: "3", title: "Launch", desc: "Brings up Postgres + Redis + backend + worker + UI, opens the dashboard" },
          ].map((s, i) => (
            <Reveal key={s.n} dir="up" delay={i * 100}>
              <div className="card">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-semibold mb-3"
                  style={{ background: "linear-gradient(135deg, #6366f1, #a855f7)" }}
                >
                  {s.n}
                </div>
                <div className="font-semibold">{s.title}</div>
                <div className="text-sm text-slate-400 mt-1">{s.desc}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Troubleshooting */}
      <section className="max-w-3xl mx-auto">
        <Reveal dir="up">
          <h2 className="text-xl font-semibold mb-4">Troubleshooting</h2>
        </Reveal>
        <div className="card space-y-4 text-sm">
          <details>
            <summary className="cursor-pointer font-medium text-slate-200">
              The .ps1 file opens in Notepad instead of running
            </summary>
            <div className="text-slate-400 mt-2 pl-4 space-y-2">
              <p>
                That's Windows' default: <code className="text-accent-400">.ps1</code> files
                aren't executed on double-click for security. Two fixes:
              </p>
              <ul className="list-disc list-inside space-y-1">
                <li>Use the <strong>one-liner</strong> above — it pipes the script straight into PowerShell, no file lands on disk.</li>
                <li>Or download <strong>install.bat</strong> — that's a real launcher, double-click works.</li>
              </ul>
            </div>
          </details>
          <details>
            <summary className="cursor-pointer font-medium text-slate-200">
              "execution of scripts is disabled on this system"
            </summary>
            <div className="text-slate-400 mt-2 pl-4">
              The one-liner bypasses execution policy. If you downloaded the .ps1, right-click → <strong>Run with PowerShell</strong> — or run:
              <pre className="bg-ink-900 border border-ink-700 rounded-lg p-2 mt-2 text-xs font-mono">
                powershell -ExecutionPolicy Bypass -File install.ps1
              </pre>
            </div>
          </details>
          <details>
            <summary className="cursor-pointer font-medium text-slate-200">
              Parser error: <code>'$InstallDir:'</code>
            </summary>
            <div className="text-slate-400 mt-2 pl-4">
              A stray <code>$var:</code> inside double-quoted strings gets parsed as a
              drive reference. Our installer avoids this (wraps variables in
              <code> ${"{...}"}</code>). If you see it in someone else's installer — it's a bug in their script, not yours.
            </div>
          </details>
          <details>
            <summary className="cursor-pointer font-medium text-slate-200">
              Docker says "Cannot connect to the Docker daemon"
            </summary>
            <div className="text-slate-400 mt-2 pl-4">
              Docker Desktop isn't running. Start it from the Start menu (Windows) or
              Applications (Mac), wait until the whale icon goes green, then re-run.
            </div>
          </details>
        </div>
      </section>
    </div>
  );
}

function detectPlatform(): Platform {
  if (typeof navigator === "undefined") return "windows";
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes("mac")) return "mac";
  if (ua.includes("linux") && !ua.includes("android")) return "linux";
  return "windows";
}

function OpenTerminalButton({ cmd, platform }: { cmd: string; platform: Platform }) {
  const [status, setStatus] = useState<"idle" | "opened" | "copied">("idle");

  async function onClick() {
    // Copy first — this is the fallback if protocol handler isn't registered.
    try {
      await navigator.clipboard.writeText(cmd);
      setStatus("copied");
    } catch {}

    // Attempt protocol-based open. On Windows 11 `wt://` can launch Windows
    // Terminal but requires a profile + registered handler — usually present.
    // On mac, iTerm has an x-callback-url, but Terminal.app does not.
    // The safest path: open a hidden anchor to the protocol URI and immediately
    // show a "paste it" hint if nothing happens.
    try {
      if (platform === "windows") {
        // Not all Windows systems have this handler. We optimistically try.
        window.location.href =
          `ms-shell:::{871C5380-42A0-1069-A2EA-08002B30309D}\\Windows PowerShell`;
      }
    } catch {}
    setTimeout(() => setStatus("idle"), 2500);
  }

  return (
    <button type="button" onClick={onClick} className="btn-secondary">
      <TerminalIcon />
      {status === "copied"
        ? "Copied — paste in terminal"
        : status === "opened"
          ? "Terminal opened"
          : "Copy + open terminal"}
    </button>
  );
}

function DownloadIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function TerminalIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
      aria-hidden="true"
    >
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-4 h-4"
      aria-hidden="true"
    >
      <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.42c.58.11.79-.25.79-.56v-2c-3.22.7-3.9-1.54-3.9-1.54-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 1.03 1.77 2.72 1.26 3.38.96.1-.75.41-1.26.74-1.55-2.57-.29-5.28-1.28-5.28-5.7 0-1.26.45-2.29 1.19-3.1-.12-.3-.52-1.48.11-3.07 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.78 0c2.2-1.49 3.17-1.18 3.17-1.18.64 1.59.24 2.77.12 3.07.74.81 1.19 1.84 1.19 3.1 0 4.44-2.72 5.4-5.3 5.69.42.36.8 1.08.8 2.18v3.23c0 .31.21.68.8.56A11.5 11.5 0 0 0 12 .5z" />
    </svg>
  );
}
