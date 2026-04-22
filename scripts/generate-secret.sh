#!/usr/bin/env bash
# Emit a strong random SECRET_KEY for production.
# Usage: ./scripts/generate-secret.sh
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
