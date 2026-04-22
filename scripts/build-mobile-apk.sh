#!/usr/bin/env bash
# Build a signed Android APK that points at your live frontend.
#
# Usage:
#   BIAZMARK_URL=https://biazmark.vercel.app ./scripts/build-mobile-apk.sh
#
# The APK lands at:
#   mobile/android/app/build/outputs/apk/release/app-release.apk
#
# The keystore `mobile/biazmark-release.keystore` is already in the repo — the
# Android gradle config picks it up automatically.

set -euo pipefail

cd "$(dirname "$0")/.."

export BIAZMARK_URL="${BIAZMARK_URL:-https://biazmark.vercel.app}"

echo "→ BIAZMARK_URL=$BIAZMARK_URL"

cd mobile

if [ ! -d node_modules ]; then
  npm ci
fi

# Sync Capacitor — picks up capacitor.config.ts, which reads BIAZMARK_URL.
npx cap sync android

cd android
chmod +x gradlew 2>/dev/null || true
./gradlew assembleRelease

APK="app/build/outputs/apk/release/app-release.apk"
if [ -f "$APK" ]; then
  echo
  echo "✓ APK built: mobile/android/$APK"
  ls -lh "$APK"
fi
