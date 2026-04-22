import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Biazmark mobile app — two modes:
 *
 *   1. Remote (default):  loads the live Vercel deploy.
 *      Set BIAZMARK_URL to override (e.g. https://yourdomain.com).
 *
 *   2. Bundled:  if BIAZMARK_STATIC=1, Capacitor serves a static export that the
 *      /frontend/scripts/build-mobile.sh script produces in /mobile/www.
 */

const REMOTE_URL = process.env.BIAZMARK_URL || "https://biazmark.vercel.app";

const config: CapacitorConfig = {
  appId: "com.biazmark.app",
  appName: "Biazmark",
  webDir: "www",
  backgroundColor: "#0b0d12",
  server: process.env.BIAZMARK_STATIC === "1"
    ? undefined
    : {
        url: REMOTE_URL,
        cleartext: false,
        allowNavigation: [
          "*.vercel.app",
          "*.biazmark.com",
          "*.anthropic.com",
          "graph.facebook.com",
          "api.linkedin.com",
          "api.twitter.com",
          "open.tiktokapis.com",
          "googleads.googleapis.com",
          "api.resend.com",
        ],
      },
  plugins: {
    SplashScreen: {
      launchShowDuration: 800,
      backgroundColor: "#0b0d12",
      showSpinner: false,
      androidSplashResourceName: "splash",
      iosSplashResourceName: "Splash",
    },
    StatusBar: {
      style: "DARK",
      backgroundColor: "#0b0d12",
      overlaysWebView: false,
    },
    Preferences: {
      group: "BiazmarkPrefs",
    },
  },
  android: {
    allowMixedContent: false,
    webContentsDebuggingEnabled: false,
    backgroundColor: "#0b0d12",
  },
  ios: {
    contentInset: "automatic",
    scrollEnabled: true,
    backgroundColor: "#0b0d12",
  },
};

export default config;
