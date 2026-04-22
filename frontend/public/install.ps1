# ============================================================================
# Biazmark one-liner installer (Windows PowerShell)
#
# Usage (paste into PowerShell):
#   iwr -useb https://biazmark.vercel.app/install.ps1 | iex
#
# What it does:
#   1. Checks that git + docker are installed (installs them via winget if not)
#   2. Clones the repo into $HOME\biazmark
#   3. Copies .env.example to .env (prompts for ANTHROPIC_API_KEY)
#   4. Runs `docker compose up -d`
#   5. Opens http://localhost:3000 in your browser
#
# Safe to re-run — idempotent.
# ============================================================================

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  ok $msg"   -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ! $msg"    -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  x $msg"    -ForegroundColor Red }

function Test-Cmd($name) { $null -ne (Get-Command $name -ErrorAction SilentlyContinue) }

function Install-Dep($id, $cmd) {
    if (Test-Cmd $cmd) { Write-Ok "$cmd already installed"; return }
    if (Test-Cmd "winget") {
        Write-Step "Installing $cmd via winget"
        winget install --id $id --silent --accept-package-agreements --accept-source-agreements | Out-Null
    } else {
        Write-Err "winget not found — install $cmd manually and re-run."
        exit 1
    }
}

Write-Host ""
Write-Host "  Biazmark  " -BackgroundColor DarkMagenta -ForegroundColor White -NoNewline
Write-Host " — autonomous marketing installer" -ForegroundColor White
Write-Host ""

# --- deps ---
Write-Step "Checking dependencies"
Install-Dep "Git.Git" "git"
Install-Dep "Docker.DockerDesktop" "docker"

# --- clone ---
$installDir = Join-Path $HOME "biazmark"
Write-Step "Installing to $installDir"
if (Test-Path $installDir) {
    Write-Ok "Directory exists — pulling latest"
    Push-Location $installDir
    git pull --quiet --ff-only
    Pop-Location
} else {
    git clone --depth 1 https://github.com/biazmark/biazmark.git $installDir
    Write-Ok "Cloned"
}

# --- env ---
$envFile = Join-Path $installDir ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $installDir ".env.example") $envFile
    Write-Ok "Created .env from template"

    $anthKey = Read-Host "Paste your ANTHROPIC_API_KEY (press Enter to skip)"
    if ($anthKey) {
        (Get-Content $envFile) -replace "^ANTHROPIC_API_KEY=.*", "ANTHROPIC_API_KEY=$anthKey" | Set-Content $envFile
        Write-Ok "API key saved"
    } else {
        Write-Warn "No API key — will run on Free tier (local LLM only)"
    }
} else {
    Write-Ok ".env already present — skipping"
}

# --- docker up ---
Write-Step "Starting stack (docker compose)"
Push-Location $installDir
try {
    docker compose up -d --build
    Write-Ok "All services up"
} catch {
    Write-Err "docker compose failed. Is Docker Desktop running?"
    Pop-Location
    exit 1
}
Pop-Location

# --- wait for backend ---
Write-Step "Waiting for backend to be ready"
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if ($ready) {
    Write-Ok "Backend healthy"
} else {
    Write-Warn "Backend not ready yet — check logs with: docker compose logs -f"
}

# --- done ---
Write-Host ""
Write-Host "  Done " -BackgroundColor DarkGreen -ForegroundColor White -NoNewline
Write-Host " — opening dashboard" -ForegroundColor White
Write-Host "    Frontend: http://localhost:3000"
Write-Host "    API:      http://localhost:8000/docs"
Write-Host ""
Start-Process "http://localhost:3000"
