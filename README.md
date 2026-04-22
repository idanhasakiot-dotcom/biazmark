# Biazmark — Autonomous Marketing System

מערכת פרסום אוטונומית, מקצה לקצה. מתחברת לרשתות החברתיות, מייצרת תוכן (פוסטים, מודעות, כתבות, אימיילים), מייצרת תמונות/וידאו, מפרסמת, מנתחת, ומשפרת את עצמה — כל הזמן.

An autonomous, end-to-end marketing system. Connects to every major platform, generates
content (posts, ads, articles, emails), generates images/video, publishes, analyses,
and improves itself continuously.

---

## 4 Tiers (חינמי → אנטרפרייז)

| Tier | LLM | Research | Connectors | Auto Loop |
|------|-----|----------|------------|-----------|
| **Free** | Local (Ollama) | Web scrape + Google Trends | Preview only | Manual approve |
| **Basic** | Claude Haiku | + Social listening | 1 platform live | Daily loop |
| **Pro** | Claude Sonnet | + Competitor intel API | 5 platforms live | Hourly loop |
| **Enterprise** | Claude Opus | + Premium data feeds | All + custom | Continuous + autonomous agents |

---

## What gets produced

For every business + strategy, Biazmark auto-generates and (optionally) auto-publishes:

- **Social posts** — Facebook, Instagram, LinkedIn, X (including threads), TikTok captions
- **Paid ads** — Meta Ads (campaigns + creatives + ad-sets), Google Responsive Search Ads (drafts)
- **Articles / blog posts** — 1500-2000 word SEO-optimised markdown → published to WordPress
- **Emails** — broadcast-ready subject + preview + HTML/plain body → Resend or SendGrid
- **Images** — generated via OpenAI DALL-E · Replicate (FLUX) · Stability · or SVG placeholder
- **Videos** — via Replicate (MiniMax) when configured; otherwise optional

Every piece of content is tied to a campaign and becomes a tracked variant with its own metrics.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Dashboard                           │
│  Onboard · Strategy · Content · Media · Connections · Opts   │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                          │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│  │Researcher│→│Strategist│→│ Creator  │→│ Article /    │    │
│  └──────────┘ └──────────┘ └──────────┘ │ Email Writers│    │
│                                ↓        └──────────────┘    │
│                         ┌──────────────┐       ↓             │
│                         │Media providers│→  Content variants │
│                         │OpenAI·Replicate│      ↓            │
│                         │Stability·SVG  │   Connectors       │
│                         └──────────────┘  (per-platform)     │
│                                              ↓                │
│  ┌──────────┐       ┌──────────┐         Live on Meta /      │
│  │Optimizer │ ←──── │ Analyst  │ ← Metrics WP / Email / …    │
│  └──────────┘       └──────────┘                              │
│       ↑________________ self-improvement loop ______________↓│
│                                                              │
│ OAuth (5 platforms) · Encrypted credential vault (Fernet)    │
└──────────────────────────────────────────────────────────────┘
                              │
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │ Postgres │  │  Redis   │  │  Worker  │
              └──────────┘  └──────────┘  └──────────┘
```

**Connectors** (`backend/app/connectors/`): Meta (posts + ads), LinkedIn, X, TikTok, Google Ads, Email (Resend/SendGrid), Blog (WordPress), Preview. Plus any you drop in — auto-registered.

**OAuth providers** (`backend/app/oauth/`): Meta, Google, LinkedIn, TikTok, X. One-click connect from the UI, tokens stored encrypted per business.

**Media providers** (`backend/app/media/`): OpenAI, Replicate, Stability, SVG placeholder. First configured provider is used.

---

## Quick start

```bash
cp .env.example .env
# At minimum: ANTHROPIC_API_KEY and SECRET_KEY
# Optional: add OAuth client credentials for each platform you want to connect

docker compose up -d
# Backend:  http://localhost:8000/docs
# Frontend: http://localhost:3000
```

### Connecting a platform (one-time per business)

1. Register a developer app on the platform (Meta for Developers, Google Cloud, LinkedIn Developers, …).
2. Paste the `client_id` + `client_secret` into your `.env` (e.g. `META_APP_ID`, `META_APP_SECRET`).
3. In the platform's dashboard, add this redirect URI:
   `http://localhost:8000/api/oauth/callback/<platform>` (or your prod domain).
4. Restart the backend, open the business dashboard → **Connections** → click **Connect** next to the platform.
5. Approve on the platform — you'll be redirected back with an encrypted token saved.

### Without Docker

```bash
# Backend
cd backend
pip install -e .
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev

# Worker (separate terminal)
cd backend
arq app.worker.WorkerSettings
```

---

## Usage flow

1. **Onboard** a business → paste URL/description, pick tier
2. **Connections** → connect the platforms you want to publish on
3. **Research agent** runs in background → competitors + trends + audience insights
4. **Strategist** generates a plan → review, edit, approve
5. **Creator / Article Writer / Email Writer** produce content + media → preview or publish
6. **Analyst + Optimizer** loop runs on the cadence your tier allows → kills losers, scales winners

Everything is exposed via REST (`/docs`) so you can also drive it headless.

---

## Extending

- **Add a new platform:** drop a file in `backend/app/connectors/` subclassing `BaseConnector` — auto-registers. Add an OAuth provider in `backend/app/oauth/` if the platform supports it.
- **Add a media provider:** subclass `BaseMediaProvider` in `backend/app/media/`. First configured provider wins.
- **Add a new content kind:** extend the Creator prompts in `app/prompts.py` + route it in `pipeline._create_variants_for_channel`.

---

## License

MIT.
