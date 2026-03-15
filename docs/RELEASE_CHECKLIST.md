# Release Checklist

## Before Merge

1. Confirm `git status` is clean.
2. Run `python scripts/tools/predeploy.py --base-url https://your-service.onrender.com` against the target environment.
3. Verify Render env vars are set: `MONGODB_URI`, `SECRET_KEY`, AI keys as needed, and Redis-backed limiter settings.
4. Review `render.yaml` changes for accidental config drift.
5. Check for duplicate `hub_activity` data with `python scripts/tools/dedupe_hub_activity.py --show 10`.

## Before Deploy

1. Ensure the latest commit is pushed to `main`.
2. Confirm Render build uses the expected Python version.
3. Confirm Redis is provisioned and `RATELIMIT_STORAGE_URI` resolves to the Redis connection string.
4. Confirm `/health` returns `app=ok` and `mongodb=ok` in the current deployment.

## After Deploy

1. Run `python scripts/tools/smoke_test.py --base-url https://your-service.onrender.com`.
2. Check `/health` for `limiter_backend` and AI-provider flags.
3. Verify login, dashboard APIs, and chat behavior from the browser.
4. Review Render logs for startup warnings, rate-limit backend, and index creation output.
5. If duplicate hub activity records reappear, run `python scripts/tools/dedupe_hub_activity.py --apply`.
