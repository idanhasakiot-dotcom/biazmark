#!/usr/bin/env bash
# One-shot Fly.io deploy for the Biazmark backend.
#
# Prereqs (one-time):
#   1. `brew install flyctl` (or https://fly.io/docs/flyctl/install/)
#   2. `fly auth login`
#   3. Optional: pick a region -- default is `fra` in fly.toml
#
# What this script does:
#   - Creates the app if missing
#   - Provisions managed Postgres + attaches it
#   - Provisions Upstash Redis
#   - Sets secrets from your local .env
#   - Deploys
#
# Safe to re-run: every step is idempotent-ish.

set -euo pipefail

cd "$(dirname "$0")/.."

APP="${FLY_APP:-biazmark-backend}"
REGION="${FLY_REGION:-fra}"
ENV_FILE="${ENV_FILE:-.env}"

echo "→ App: $APP   Region: $REGION"

if ! command -v fly >/dev/null 2>&1 && ! command -v flyctl >/dev/null 2>&1; then
  echo "flyctl is not installed. See https://fly.io/docs/flyctl/install/"
  exit 1
fi
FLY="$(command -v flyctl || command -v fly)"

cd backend

# 1. Create app (ignore error if it already exists)
$FLY apps create "$APP" --org personal 2>/dev/null || echo "  (app already exists — continuing)"

# 2. Postgres — create if missing, attach
if ! $FLY postgres list 2>/dev/null | grep -q "${APP}-db"; then
  $FLY postgres create --name "${APP}-db" --region "$REGION" --initial-cluster-size 1 --vm-size shared-cpu-1x --volume-size 1
fi
$FLY postgres attach "${APP}-db" --app "$APP" 2>/dev/null || echo "  (postgres already attached)"

# 3. Redis (Upstash via Fly)
$FLY redis create --name "${APP}-redis" --region "$REGION" --no-replicas --plan free 2>/dev/null || echo "  (redis already exists)"
REDIS_URL=$($FLY redis status "${APP}-redis" --json 2>/dev/null | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('PrivateUrl',d.get('PublicUrl','')))") || true
if [ -n "${REDIS_URL:-}" ]; then
  $FLY secrets set --app "$APP" REDIS_URL="$REDIS_URL"
fi

# 4. Secrets from .env (skip blanks, skip local-only keys)
if [ -f "../$ENV_FILE" ]; then
  echo "→ Importing secrets from ../$ENV_FILE"
  ARGS=()
  while IFS='=' read -r k v; do
    [[ -z "$k" || "$k" =~ ^# ]] && continue
    [[ -z "$v" ]] && continue
    # Skip keys that should come from Fly directly.
    case "$k" in
      DATABASE_URL|REDIS_URL|API_HOST|API_PORT) continue ;;
    esac
    ARGS+=("${k}=${v}")
  done < <(grep -v '^[[:space:]]*$' "../$ENV_FILE" | grep -v '^#')
  if [ ${#ARGS[@]} -gt 0 ]; then
    $FLY secrets set --app "$APP" --stage "${ARGS[@]}"
  fi
fi

# 5. Also make sure OAUTH_REDIRECT_BASE is set to the public app URL.
PUBLIC_HOST="${APP}.fly.dev"
$FLY secrets set --app "$APP" --stage \
  OAUTH_REDIRECT_BASE="https://${PUBLIC_HOST}" \
  CORS_ORIGINS="${CORS_ORIGINS:-https://biazmark.vercel.app}"

# 6. Deploy
$FLY deploy --app "$APP"

echo
echo "✓ Deployed."
echo "  URL:     https://${PUBLIC_HOST}"
echo "  Health:  https://${PUBLIC_HOST}/healthz"
echo
echo "Next step: set BIAZMARK_BACKEND_URL=https://${PUBLIC_HOST} in Vercel."
