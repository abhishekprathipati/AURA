# AURA Environment Files Guide

> **FIX #37**: Documentation for the multiple `.env` files in the project root.

## Files Overview

| File | Purpose | Git-tracked? |
|------|---------|:---:|
| `.env.example` | Template with all available config keys and placeholder values. Copy this to `.env` to get started. | ✅ Yes |
| `.env` | **Your local config** — actual API keys, DB credentials, secrets. Never commit! | ❌ No |
| `.env.production` | Production-specific overrides (stricter settings). Used during deployment only. | ❌ No |

## Quickstart

```bash
# 1. Copy the example file
cp .env.example .env

# 2. Fill in your actual values
# At minimum, set: MONGODB_URI, SECRET_KEY, and at least one AI key (GEMINI_API_KEY recommended)

# 3. For production deployment
cp .env.example .env.production
# Set FLASK_ENV=production, SESSION_COOKIE_SECURE=true, RATELIMIT_STORAGE_URI=redis://...
```

## Key Configuration

| Variable | Required | Description |
|----------|:---:|-------------|
| `SECRET_KEY` | ✅ (prod) | Session encryption key. **App crash if missing in production.** Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `MONGODB_URI` | ✅ | MongoDB Atlas connection string |
| `GEMINI_API_KEY` | Recommended | Primary AI provider. Fallback chain: Gemini → DeepSeek → Groq → OpenAI → local |
| `RATELIMIT_STORAGE_URI` | ✅ (prod) | Must be `redis://...` in production. `memory://` only for development. |
| `SENTRY_DSN` | Optional | Enable Sentry error monitoring |
| `DEFAULT_TIMEZONE_OFFSET` | Optional | Default timezone offset in minutes from UTC (default: 330 = IST) |
