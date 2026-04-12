"""
TEST 3: Production Deployment Readiness Check
==============================================
Validates configuration for production deployment.
"""

import os
from dotenv import load_dotenv
from flask import Flask
import sys

load_dotenv()

print("=" * 60)
print("TEST 3: PRODUCTION DEPLOYMENT READINESS")
print("=" * 60)
print()

issues = []
warnings = []
checks_passed = []

# 1. Check SECRET_KEY
print("[CHECK 1] SECRET_KEY (security)")
secret_key = os.getenv('SECRET_KEY', '').strip()
if secret_key and 'generate' not in secret_key.lower() and len(secret_key) >= 32:
    checks_passed.append("[OK] SECRET_KEY is set and strong")
else:
    issues.append("SECRET_KEY is missing or weak (need 32+ char random string)")
print()

# 2. Check FLASK_ENV
print("[CHECK 2] FLASK_ENV (mode)")
env = os.getenv('FLASK_ENV', '').strip().lower()
if env == 'production':
    checks_passed.append("[OK] FLASK_ENV=production")
else:
    warnings.append(f"FLASK_ENV={env or 'not set'} (should be 'production')")
print()

# 3. Check MONGODB_URI
print("[CHECK 3] MongoDB Connection")
mongo_uri = os.getenv('MONGODB_URI', '').strip()
if mongo_uri and 'localhost' not in mongo_uri:
    checks_passed.append("[OK] MongoDB remote connection configured")
else:
    warnings.append("MongoDB using localhost (only OK for testing)")
print()

# 4. Check Mail Configuration
print("[CHECK 4] Email Configuration")
mail_server = os.getenv('MAIL_SERVER', '').strip()
mail_user = os.getenv('MAIL_USERNAME', '').strip()
mail_pass = os.getenv('MAIL_PASSWORD', '').strip()
mail_sender = os.getenv('MAIL_DEFAULT_SENDER', '').strip()

if mail_server and mail_user and mail_pass and mail_sender:
    checks_passed.append("[OK] Email config complete (SMTP ready)")
else:
    issues.append("Email configuration incomplete or missing")
print()

# 5. Check AI Provider Keys
print("[CHECK 5] AI Provider Keys")
ai_keys = {
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', '').strip(),
    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', '').strip(),
    'GROQ_API_KEY': os.getenv('GROQ_API_KEY', '').strip(),
}
api_count = sum(1 for v in ai_keys.values() if v and 'your-' not in v.lower())
if api_count >= 1:
    checks_passed.append(f"[OK] {api_count} AI provider(s) configured")
else:
    warnings.append("No AI provider keys configured (chatbot will use fallback)")
print()

# 6. Check SMS Configuration
print("[CHECK 6] SMS Configuration (Fast2SMS)")
sms_key = os.getenv('FAST2SMS_API_KEY', '').strip()
sms_enabled = os.getenv('SMS_ENABLED', 'true').lower() in ('true', '1', 'yes')
if sms_key and 'your-' not in sms_key.lower():
    checks_passed.append("[OK] SMS configured (Fast2SMS)")
else:
    warnings.append("SMS not configured or using placeholder (OTP fallback: email)")
print()

# 7. Check Rate Limiting
print("[CHECK 7] Rate Limiting (Redis)")
rate_limit = os.getenv('RATELIMIT_STORAGE_URI', '').strip()
if rate_limit and 'redis://' in rate_limit:
    checks_passed.append("[OK] Redis configured for rate limiting")
elif rate_limit and 'memory://' in rate_limit:
    warnings.append("Rate limiting using memory (OK for dev, NOT for production)")
else:
    warnings.append("Rate limiting not configured properly")
print()

# 8. Check Sentry (Error Monitoring)
print("[CHECK 8] Sentry (Optional Error Monitoring)")
sentry = os.getenv('SENTRY_DSN', '').strip()
if sentry and 'your-' not in sentry.lower():
    checks_passed.append("[OK] Sentry configured for error tracking")
else:
    warnings.append("Sentry not configured (recommended for production)")
print()

# 9. Check Session Security
print("[CHECK 9] Session Security")
session_secure = os.getenv('SESSION_COOKIE_SECURE', '').lower() in ('true', '1')
if session_secure:
    checks_passed.append("[OK] SESSION_COOKIE_SECURE=true (HTTPS enforced)")
else:
    issues.append("SESSION_COOKIE_SECURE not set (need HTTPS in production)")
print()

# 10. Check CORS
print("[CHECK 10] CORS Configuration")
cors_origins = os.getenv('CORS_ORIGINS', '').strip()
if cors_origins:
    checks_passed.append(f"[OK] CORS configured: {cors_origins[:30]}...")
else:
    warnings.append("CORS_ORIGINS not set (may default to wildcard)")
print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print()

print(f"[OK] Passed: {len(checks_passed)}")
for check in checks_passed:
    print(f"  {check}")
print()

if warnings:
    print(f"[WARN] Warnings: {len(warnings)}")
    for warn in warnings:
        print(f"  [WARN] {warn}")
    print()

if issues:
    print(f"[ERROR] Issues: {len(issues)}")
    for issue in issues:
        print(f"  [ERROR] {issue}")
    print()
    print("[BLOCKED] Cannot deploy with issues above")
    sys.exit(1)
else:
    print("[SUCCESS] [OK] ALL CHECKS PASSED")
    print("         Ready for production deployment!")
    print()
    print("NEXT STEPS:")
    print("  1. Ensure all environment variables are set on server")
    print("  2. Use a production WSGI server (gunicorn, uwsgi)")
    print("  3. Set up SSL/TLS (HTTPS)")
    print("  4. Configure database backups")
    print("  5. Set up monitoring and alerts")
    print()
