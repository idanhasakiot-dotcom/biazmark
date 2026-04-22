# Deploying Biazmark

Three targets. Each is one command once set up.

```
Backend   →  Fly.io   (or Railway)   →  https://biazmark-backend.fly.dev
Frontend  →  Vercel                  →  https://biazmark.vercel.app
Mobile    →  signed Android APK      →  mobile/android/app/build/outputs/apk/release/
```

---

## 0. One-time prerequisites

```bash
# Generate a strong SECRET_KEY and save it — you'll paste it into env vars.
./scripts/generate-secret.sh

# Copy env template and fill in ANTHROPIC_API_KEY (mandatory for non-free tiers)
# plus whichever OAuth apps you want live (Meta, Google, LinkedIn, TikTok, X).
cp .env.example .env
```

Required per tier:

| Tier | Must-have env |
|------|---------------|
| `free` | nothing — uses local Ollama |
| `basic` / `pro` / `enterprise` | `ANTHROPIC_API_KEY`, `SECRET_KEY` |
| + live posting | the OAuth app pair(s) for each platform, e.g. `META_APP_ID` + `META_APP_SECRET` |

---

## 1. Backend — Fly.io (recommended)

### Automated

```bash
./scripts/deploy-backend-fly.sh
```

The script:
1. Creates the Fly app (`biazmark-backend` by default)
2. Provisions managed Postgres and attaches it → sets `DATABASE_URL`
3. Provisions Upstash Redis → sets `REDIS_URL`
4. Uploads every non-blank value from `.env` as a Fly secret
5. Sets `OAUTH_REDIRECT_BASE=https://<app>.fly.dev` and `CORS_ORIGINS=https://biazmark.vercel.app`
6. Runs `fly deploy`

Re-run it any time — each step is idempotent.

### Manual

```bash
cd backend
fly launch --no-deploy              # pick name/region
fly postgres create && fly postgres attach <name>
fly redis create
fly secrets set ANTHROPIC_API_KEY=... SECRET_KEY=$(../scripts/generate-secret.sh) \
                OAUTH_REDIRECT_BASE=https://<app>.fly.dev \
                CORS_ORIGINS=https://biazmark.vercel.app
fly deploy
```

### Verify

```bash
curl https://<app>.fly.dev/healthz           # {"status":"ok"}
curl https://<app>.fly.dev/readyz            # {"status":"ok","db":"ok"}
curl https://<app>.fly.dev/api/tier          # tier info
open  https://<app>.fly.dev/docs             # OpenAPI UI
```

---

## 1b. Backend — Railway (alternative)

```bash
cd backend
railway login
railway init
# In the Railway dashboard: add Postgres + Redis plugins (auto-wires DATABASE_URL + REDIS_URL).
# In the dashboard Variables tab: paste ANTHROPIC_API_KEY, SECRET_KEY, OAuth keys.
railway up
```

Then add a second service for the `arq` worker using the same image but with
`startCommand = "arq app.worker.WorkerSettings"`.

---

## 2. Frontend — Vercel

### First time

1. Push this repo to GitHub.
2. On vercel.com → **Add New → Project** → pick the repo.
3. **Root Directory:** `frontend`
4. Framework is auto-detected (Next.js).
5. **Environment Variables (Production):**

   | Name | Value |
   |------|-------|
   | `BIAZMARK_BACKEND_URL` | `https://biazmark-backend.fly.dev` (your step-1 URL) |
   | `NEXT_PUBLIC_API_URL` | *(leave blank)* |

6. **Deploy.**

After that every `git push` to `main` auto-redeploys. You can also trigger
from CLI:

```bash
cd frontend
vercel --prod
```

### Why `BIAZMARK_BACKEND_URL`?

`next.config.js` rewrites `/api/*` and `/media/*` from the Vercel edge through
to your FastAPI backend. The browser only ever sees your vercel.app origin,
so there's no CORS to configure.

---

## 3. Mobile — Android APK

```bash
BIAZMARK_URL=https://biazmark.vercel.app ./scripts/build-mobile-apk.sh
```

Output: `mobile/android/app/build/outputs/apk/release/app-release.apk` — signed
with `mobile/biazmark-release.keystore`, ready to upload to Google Play.

### iOS

Requires a Mac with Xcode:

```bash
cd mobile
npx cap add ios
npx cap open ios          # opens Xcode, hit Archive → App Store
```

---

## 4. Post-deploy checklist

- [ ] `GET /healthz` on backend returns 200
- [ ] `GET /readyz` on backend returns `"db":"ok"`
- [ ] Frontend loads and shows live data in the dashboard (no BackendBanner demo notice)
- [ ] Connect a test platform via OAuth — redirect URI on the platform side must be
      `https://<backend-domain>/api/oauth/callback/<platform>`
- [ ] Create a business, run research → strategy → publish (preview connector) end-to-end
- [ ] Worker is running (check `fly logs` / Railway logs for `arq` startup)

---

## 5. Custom domains (optional)

### Backend on `api.biazmark.com`

```bash
fly certs create api.biazmark.com
# Add the DNS records Fly prints to your registrar.
fly secrets set OAUTH_REDIRECT_BASE=https://api.biazmark.com
```

### Frontend on `biazmark.com`

1. Vercel → Project → Domains → Add `biazmark.com` + `www.biazmark.com`.
2. Point DNS as Vercel instructs.
3. Update backend: `fly secrets set CORS_ORIGINS=https://biazmark.com,https://www.biazmark.com`.

### Also update each OAuth app's redirect URI on the provider side.

---

## 6. CI / CD

`.github/workflows/ci.yml` runs on every push/PR:
- Backend: `ruff` + `pytest`
- Frontend: `npm ci` + `npm run build`
- Backend Docker: image builds successfully

`.github/workflows/deploy.yml` deploys on push to `main`:
- Backend → Fly (needs `FLY_API_TOKEN` secret in GitHub)
- Frontend → Vercel (needs `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`)
- Mobile → builds APK and uploads as artifact on every run

All deploy jobs **no-op gracefully** when their secrets aren't set, so the
workflow never fails before you're ready to wire them up.

Generate tokens:
- Fly: `fly auth token`
- Vercel: `vercel login` → `cat ~/.vercel/auth.json` (token) — org/project IDs are in `.vercel/project.json` after your first `vercel link`.

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Vercel deploy shows "demo mode" banner | `BIAZMARK_BACKEND_URL` not set on Vercel, or backend is down. |
| OAuth redirect fails with 400 | The redirect URI on the provider's app doesn't exactly match `${OAUTH_REDIRECT_BASE}/api/oauth/callback/<platform>`. |
| `psycopg`/asyncpg errors on Railway | The `DATABASE_URL` normalizer in `app/db.py` handles `postgres://` — redeploy if you upgraded mid-session. |
| APK opens to blank screen | `BIAZMARK_URL` wasn't set at build time, so it defaults to `biazmark.vercel.app`. Rebuild with your real URL. |
| Worker not running | Fly: add a `[processes]` section, or create a second app with `CMD ["arq", "app.worker.WorkerSettings"]`. Railway: add a second service. |
| 429 / rate-limited by Anthropic | Drop `biazmark_tier` one notch or wait out the limit — higher tiers call the LLM more aggressively. |

---

That's it. You should be live end-to-end in under 20 minutes.
