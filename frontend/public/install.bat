@echo off
:: ============================================================================
:: Biazmark one-click installer (Windows)
::
:: Double-click this file — it launches PowerShell, bypasses execution policy,
:: downloads and runs the real installer. No "opens as text" weirdness.
:: ============================================================================

setlocal
title Biazmark Installer
color 0D

echo.
echo   Biazmark installer
echo   ==================
echo.
echo   Launching PowerShell and fetching the installer...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "iwr -useb https://biazmark.vercel.app/install.ps1 | iex"

if errorlevel 1 (
  echo.
  echo   Installer exited with an error. See messages above.
  echo.
  pause
  exit /b 1
)

echo.
echo   Installation complete. Press any key to close this window.
pause >nul
