#!/usr/bin/env bash
# ============================================================================
# Biazmark one-liner installer (macOS / Linux)
#
# Usage:
#   curl -fsSL https://biazmark.vercel.app/install.sh | bash
# ============================================================================

set -euo pipefail

c_cyan="\033[36m"; c_green="\033[32m"; c_yellow="\033[33m"; c_red="\033[31m"; c_dim="\033[2m"; c_off="\033[0m"

step() { printf "\n${c_cyan}==> %s${c_off}\n" "$1"; }
ok()   { printf "  ${c_green}ok${c_off} %s\n" "$1"; }
warn() { printf "  ${c_yellow}!${c_off} %s\n" "$1"; }
err()  { printf "  ${c_red}x${c_off} %s\n" "$1"; }

has()  { command -v "$1" >/dev/null 2>&1; }

printf "\n${c_cyan}  Biazmark ${c_off}— autonomous marketing installer\n\n"

# --- deps ---
step "Checking dependencies"
for cmd in git docker; do
  if has "$cmd"; then
    ok "$cmd already installed"
  else
    err "$cmd is required — install it and re-run."
    exit 1
  fi
done
if ! docker compose version >/dev/null 2>&1; then
  err "'docker compose' not found — ensure Docker Desktop / compose plugin is installed."
  exit 1
fi
ok "docker compose available"

# --- clone ---
install_dir="${HOME}/biazmark"
step "Installing to $install_dir"
if [ -d "$install_dir/.git" ]; then
  ok "Directory exists — pulling latest"
  (cd "$install_dir" && git pull --quiet --ff-only)
else
  git clone --depth 1 https://github.com/biazmark/biazmark.git "$install_dir"
  ok "Cloned"
fi

# --- env ---
env_file="${install_dir}/.env"
if [ ! -f "$env_file" ]; then
  cp "${install_dir}/.env.example" "$env_file"
  ok "Created .env from template"

  printf "  %bPaste your ANTHROPIC_API_KEY (Enter to skip): %b" "$c_dim" "$c_off"
  read -r anth_key || true
  if [ -n "${anth_key:-}" ]; then
    # Use a temp file for cross-platform sed safety.
    tmp="$(mktemp)"
    sed "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=${anth_key}|" "$env_file" > "$tmp"
    mv "$tmp" "$env_file"
    ok "API key saved"
  else
    warn "No API key — will run on Free tier (local LLM only)"
  fi
else
  ok ".env already present — skipping"
fi

# --- docker up ---
step "Starting stack (docker compose)"
(cd "$install_dir" && docker compose up -d --build)
ok "All services up"

# --- wait for backend ---
step "Waiting for backend to be ready"
ready=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 2 http://localhost:8000/api/health >/dev/null 2>&1; then
    ready=1; break
  fi
  sleep 2
done
if [ "$ready" = "1" ]; then ok "Backend healthy"; else warn "Backend not ready yet — run: docker compose logs -f"; fi

# --- open browser ---
printf "\n${c_green}  Done ${c_off}— opening dashboard\n"
printf "    Frontend: http://localhost:3000\n"
printf "    API:      http://localhost:8000/docs\n\n"

case "$(uname -s)" in
  Darwin) open "http://localhost:3000" 2>/dev/null || true ;;
  Linux)  xdg-open "http://localhost:3000" 2>/dev/null || true ;;
esac
