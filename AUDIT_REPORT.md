# AURA Project - Comprehensive Audit Report

## CRITICAL - Fix Immediately

### 1. Missing @login_required on chat.py routes
**File:** `routes/chat.py`
**Lines:** 94, 263, 272, 309, 355, 381, 414, 440, 466, 492, 552
**Risk:** Unauthenticated users can trigger AI API calls, access chat history, upload files
**Fix:** Add `@login_required` decorator to all 11 routes

### 2. Weak SECRET_KEY (if deployed)
**File:** `.env`
**Issue:** `SECRET_KEY=aura-secret-key-2024-change-this-later` is guessable
**Fix:** Generate cryptographically secure key for production

---

## HIGH - Fix Soon

### 3. .env.template naming mismatch
**File:** `.env.template` line 5
**Issue:** Uses `MONGO_URI` but `config.py` line 33 expects `MONGODB_URI`
**Impact:** New developers get broken DB connection
**Fix:** Rename to `MONGODB_URI` in template

### 4. Missing dark theme on 7 CSS files
**Files:**
- `static/css/style.css` - 0 dark theme rules
- `static/css/global.css` - 0 dark theme rules
- `static/css/login.css` - 0 dark theme rules
- `static/css/proctor_dashboard.css` - 0 dark theme rules
- `static/css/connect_hub.css` - 0 dark theme rules
- `static/css/chat.css` - 0 dark theme rules
- `static/css/sidebar.css` - 0 dark theme rules
**Impact:** Mixed theme when toggling dark mode
**Fix:** Add `[data-theme="dark"]` rules or use CSS variables

### 5. chat.css has zero hover/focus states
**File:** `static/css/chat.css`
**Impact:** No interactive feedback, accessibility issue
**Fix:** Add `:hover` and `:focus-visible` states to buttons

### 6. Vercel deployment will fail
**File:** `requirements.txt`
**Issue:** `torch==2.5.1+cpu` (~780MB) + `transformers` (~400MB) exceed 250MB limit
**Issue:** Flask-SocketIO cannot work serverless
**Fix:** Use external AI API or separate backend for heavy deps

---

## MEDIUM - Should Fix

### 7. Duplicate redis in requirements.txt
**File:** `requirements.txt` lines 18, 49
**Fix:** Remove duplicate

### 8. Dev dependencies in production requirements
**File:** `requirements.txt` lines 47-48
**Issue:** `pytest` and `ruff` with no version pins
**Fix:** Move to dev-requirements.txt or pin versions

### 9. z-index scale inconsistency
**Files:** 55+ z-index declarations across CSS
**Range:** -2 to 99999 with no shared tokens
**Fix:** Define z-index scale in CSS variables

### 10. Competing CSS variable schemes
- `--accent/--border` (style.css, global.css)
- `--h-*` (connect_hub.css)
- `--pd-*` (proctor_dashboard.css)
- `--bg-*/--text-*` (mental-chatbot.css, study-assistant.css)
- `--primary/--gradient-*` (login.css)
**Fix:** Consolidate into unified design tokens

### 11. 15 separate :root blocks
**Impact:** No single source of truth for design tokens
**Fix:** Create shared `variables.css` imported by all

### 12. Duplicate body/reset rules
**Count:** 14+ `*`, `html`, `body` declarations
**Fix:** Consolidate into single reset file

### 13. Near-identical chatbot CSS
**Files:** `mental-chatbot.css` and `study-assistant.css` share ~90% code
**Fix:** Extract shared styles to common file

### 14. Proctor test seed endpoint in production
**File:** `routes/proctor/audit.py` line 425
**Issue:** `POST /api/test/seed` has no environment check
**Fix:** Add `if app.debug:` guard

---

## LOW - Nice to Have

### 15. Unused gunicorn on Vercel
**File:** `requirements.txt` line 43
**Fix:** Remove or move to prod-only deps

### 16. Duplicate html declarations
**File:** `global.css` lines 14, 454
**Fix:** Remove duplicate

### 17. Inconsistent dark theme quotes
**Issue:** Some files use `[data-theme="dark"]`, others `[data-theme='light']`
**Fix:** Standardize on double quotes

---

## Summary

| Priority | Count | Status |
|----------|-------|--------|
| CRITICAL | 2 | Pending |
| HIGH | 4 | Pending |
| MEDIUM | 8 | Pending |
| LOW | 3 | Pending |
| **Total** | **17** | |

---

Generated: 2026-03-17
