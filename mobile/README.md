# Biazmark Mobile

Native Android + iOS companion for the Biazmark web dashboard, built with Capacitor.

## What it does

- Shows a branded launch screen to pick which Biazmark instance to connect to
  (Vercel default, localhost for dev, or a self-hosted URL).
- Wraps the web dashboard in a native webview — full access to every feature
  (connections, OAuth flows, content gallery, optimization loop) with native
  status bar, splash, haptics, and share sheet.
- Stores the chosen instance URL in secure native preferences so the next
  launch goes straight in.

## Setup

```bash
# 1. Install Capacitor CLI + deps
cd mobile
npm install

# 2. Add platforms (one-time, requires Android Studio / Xcode installed)
npx cap add android
npx cap add ios

# 3. Sync web assets
npx cap sync
```

## Running

### Android

```bash
# Opens Android Studio — hit Run.
npm run open:android

# Or build a debug APK directly (requires JDK + Android SDK):
cd android && ./gradlew assembleDebug
# → android/app/build/outputs/apk/debug/app-debug.apk
```

### iOS

```bash
# Opens Xcode — hit Run. (macOS only)
npm run open:ios
```

## Pointing at your deploy

Edit [capacitor.config.ts](capacitor.config.ts) and change `REMOTE_URL` — or set
`BIAZMARK_URL` at build time:

```bash
BIAZMARK_URL=https://mybiazmark.com npx cap sync
```

To ship a fully-offline bundle (no server dependency for the shell — the pages
still call the backend), run:

```bash
BIAZMARK_STATIC=1 npx cap sync
# then `cap run android` etc.
```

## Building a release APK

```bash
# 1. Generate a keystore (one-time)
keytool -genkey -v -keystore biazmark-release.keystore \
        -alias biazmark -keyalg RSA -keysize 2048 -validity 10000

# 2. Configure in android/app/build.gradle (signingConfigs.release)

# 3. Build
cd android && ./gradlew assembleRelease
# → android/app/build/outputs/apk/release/app-release.apk
```

## Publishing

- **Google Play:** upload `app-release.aab` (`./gradlew bundleRelease`) to the
  Play Console. Fill out content rating, privacy policy URL, target API level 34+.
- **App Store:** archive in Xcode → distribute → App Store Connect.
