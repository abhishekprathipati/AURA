# 🚀 AURA Production Deployment Guide

## ✅ Pre-Deployment Checklist

- [x] Email system working (SMTP configured)
- [x] Stress alerts functional
- [x] OTP system operational
- [x] SECRET_KEY strong and unique
- [x] SESSION_COOKIE_SECURE enabled
- [x] FLASK_ENV set to production
- [x] MongoDB connected (remote)
- [x] AI providers configured
- [x] Tests passing

---

## 📋 Environment Variables Required

Set these on your hosting platform (Render, Heroku, AWS, etc.):

```bash
# Core
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=19204bcb3236188b10e814cbbcd40adddeed138819ff10c1c373473a34c69c0a

# Database
MONGODB_URI=mongodb+srv://auraadmin:AuraDB2024pass@cluster0.76fgwmv.mongodb.net/aura_db?retryWrites=true&w=majority&appName=Cluster0
MONGODB_DB_NAME=aura_db

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Session Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_LIFETIME_SECS=3600

# Rate Limiting (use Redis in production)
REDIS_URL=redis://your-redis-host:6379/0
RATELIMIT_STORAGE_URI=redis://your-redis-host:6379/0

# AI Providers (at least one required)
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
GROQ_API_KEY=your-groq-key
DEEPSEEK_API_KEY=your-deepseek-key

# SMS (Optional - Fast2SMS for OTP delivery)
FAST2SMS_API_KEY=your-fast2sms-key
SMS_ENABLED=true

# CORS (for cross-origin requests)
CORS_ORIGINS=https://yourdomain.com

# Error Monitoring (Optional - Sentry)
SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=production
```

---

## 🚀 Deploy on Render

### Step 1: Push to GitHub

```bash
cd d:/AURA
git add .
git commit -m "feat: production ready configuration"
git push origin main
```

### Step 2: Create Render Service

1. Go to https://render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo (abhiskprathipati/AURA)
4. Configure:
   - **Name**: aura-api
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Choose based on traffic

### Step 3: Add Environment Variables

In Render dashboard:
1. Go to service Settings
2. Click **"Environment"**
3. Add all variables from "Environment Variables Required" section above
4. **Save and Deploy**

### Step 4: Enable HTTPS

Render auto-generates HTTPS certificate 🔒

---

## 🐳 Alternative: Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
```

Deploy on:
- Docker Hub
- Google Cloud Run
- AWS ECS
- Digital Ocean App Platform

---

## ⚡ Production Server Setup (Self-Hosted)

If using VPS (DigitalOcean, Linode, AWS EC2):

### Install dependencies:

```bash
sudo apt update
sudo apt install python3.11 python3-pip redis-server nginx
```

### Setup AURA:

```bash
git clone https://github.com/abhiskprathipati/AURA.git
cd AURA
pip install -r requirements.txt
```

### Configure Gunicorn:

```bash
pip install gunicorn
gunicorn app:app --workers 4 --bind 127.0.0.1:5000
```

### Setup Nginx (reverse proxy):

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Enable HTTPS (Let's Encrypt):

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## 🔒 Security Checklist

- [ ] HTTPS/TLS enabled
- [ ] SESSION_COOKIE_SECURE=True
- [ ] CORS origins whitelisted
- [ ] API keys stored securely (not in git)
- [ ] Database credentials encrypted
- [ ] Rate limiting active
- [ ] CSRF protection enabled (done)
- [ ] Content Security Policy set (done)
- [ ] Sentry error tracking active
- [ ] Database backups configured
- [ ] WAF configured (optional)

---

## 📊 Post-Deployment

### Monitor

```bash
# Check logs
tail -f /var/log/aura.log

# Monitor resources
top
netstat -tuln | grep 5000
```

### Health Check

Visit: `https://yourdomain.com/health`

Should return:

```json
{
  "app": "ok",
  "mongodb": "ok",
  "ai_configured": {"gemini": true, "openai": true},
  "limiter_backend": "redis"
}
```

---

## 🎉 You're Live!

Your AURA system is now in production serving students, parents, and proctors 🚀

---

## 📧 Support

For questions or issues:
- Check logs: `GET /health`
- Monitor errors: Sentry dashboard
- Database stats: MongoDB Atlas

---

**Last Updated**: 2026-04-12
**Status**: Production Ready ✅
