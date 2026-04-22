# App icons + splash screens

Drop a 1024×1024 `icon.png` + 2732×2732 `splash.png` into this folder and run:

```bash
npx @capacitor/assets generate --iconBackgroundColor "#0b0d12" \
                                --splashBackgroundColor "#0b0d12"
```

Capacitor will auto-produce every density variant for Android + iOS and wire
them into the native projects.

Until you add real assets, Capacitor uses default placeholders.
