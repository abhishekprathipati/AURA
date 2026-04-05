# AURA Deployment Guide — Render

## Quick Start: Deploy to Render (5 minutes)

### Prerequisites
- GitHub account with AURA repo connected
- Render account (free tier available at render.com)
- MongoDB Atlas account (free cluster: mongodb.com/cloud/atlas)

---

## Step 1: Prepare MongoDB Atlas

1. Go to **[MongoDB Atlas Console](https://cloud.mongodb.com/)**
2. Create a **free M0 cluster** if you don't have one
3. Get your **connection string**:
   - Click "Connect" → "Connect your application"
   - Copy the URI: `mongodb+srv://username:password@cluster.mongodb.net/aura_db?retryWrites=true`
   - Save this — you'll need it in Step 3

---

## Step 2: Connect Render to GitHub

1. Go to **[Render Dashboard](https://dashboard.render.com/)**
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository:
   - Select **"GitHub"** (authorize if needed)
   - Choose **`abhishekprathipati/AURA`**
   - Click **"Connect"**

---

## Step 3: Configure Environment Variables

In the Render dashboard, fill in these **Environment Variables**:

| Variable | Value | Notes |
|----------|-------|-------|
| **FLASK_ENV** | `production` | Required |
| **DEBUG** | `false` | Must be false in production |
| **MONGODB_URI** | `mongodb+srv://...` | From Step 1 |
| **SECRET_KEY** | Generate below | Security critical |
| **REDIS_URL** | (Leave empty) | Render will provide |
| **OPENAI_API_KEY** | Your key | From OpenAI dashboard |
| **GEMINI_API_KEY** | Your key | From Google AI Studio |
| **GROQ_API_KEY** | Your key | From Groq console |
| **DEEPSEEK_API_KEY** | Your key | From DeepSeek |

### Generate SECRET_KEY

Run this locally:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output (32-character hex string) and paste into `SECRET_KEY` field.

---

## Step 4: Create the Web Service

1. **Name**: `aura-student-wellness`
2. **Environment**: `Python 3`
3. **Build Command**: (Auto-detected: `pip install -r requirements.txt`)
4. **Start Command**: (Auto-detected from `Procfile`)
5. **Plan**: Free (or Starter for better performance)
6. Click **"Create Web Service"**

Render will:
- 🔨 Install dependencies from `requirements.txt`
- 🚀 Start the app using `Procfile`
- 🔗 Assign you a live URL like `https://aura-student-wellness.onrender.com`

---

## Step 5: Enable Auto-Deploy (Optional)

1. In Render dashboard → **Settings** → **Auto-Deploy**
2. Enable "Auto-deploy new commits" from main branch
3. Now every `git push` triggers a rebuild automatically ✨

---

## Step 6: Monitor & Debug

### View Logs
- Render Dashboard → **Logs** tab
- Watch build and runtime errors in real-time

### Common Issues

| Error | Solution |
|-------|----------|
| **Import Error: torch** | torch is too large (780MB). Handled by Render's build optimization. If still fails, see "Alternative AI Services" below |
| **Database Connection Failed** | Check `MONGODB_URI` is correct and IP whitelist allows Render's servers (allow all: `0.0.0.0/0`) |
| **503 Service Unavailable** | App crashed. Check logs. May need more memory on paid plan. |
| **Cold Start Slow** | Free tier sleeps after 15 min inactivity. First request wakes it up (~30s). Upgrade to Starter for always-on. |

---

## Alternative: Use External AI API

If Render hits memory limits with torch/transformers, use API calls instead:

**Option A: Replace Heavy Libraries**
```python
# Instead of: from models.chat import ChatModel
# Use:
import openai
response = openai.ChatCompletion.create(...)
```

**Option B: Offload to Cloud Functions**
- Gemini API (Google Cloud)
- Groq API (cloud.groq.com)
- DeepSeek API
- All already integrated in your code!

---

## Production Checklist

- [ ] `FLASK_ENV=production` set in Render
- [ ] `DEBUG=false` set in Render
- [ ] Strong `SECRET_KEY` generated and set
- [ ] `MONGODB_URI` pointing to production MongoDB
- [ ] All AI API keys configured
- [ ] Render web service status shows "Live" (greenlight)
- [ ] Test homepage loads: `https://aura-student-wellness.onrender.com/`
- [ ] Test student dashboard works
- [ ] Test chat functionality
- [ ] Monitor logs daily for errors

---

## Scaling (When You Need It)

| Metric | Free Tier | Starter | Standard |
|--------|-----------|---------|----------|
| **Cost** | $0 | $7/mo | $25/mo |
| **RAM** | 512MB | 2GB | 4GB |
| **Always On** | ❌ (spins down after 15 min) | ✅ | ✅ |
| **Concurrent Users** | ~10 | ~100 | ~1000 |

Upgrade in Render Dashboard → **Settings** → **Plan**

---

## Support & Troubleshooting

- **Render Docs**: https://render.com/docs
- **GitHub Issues**: Report bugs at `abhishekprathipati/AURA/issues`
- **AURA Audit Report**: See `../reports/AUDIT_REPORT.md` for remaining TODOs

---

## Post-Deployment

After deployment succeeds:

1. **Verify all routes work**:
   - Homepage: `/`
   - Student Dashboard: `/student/dashboard`
   - Connect Hub: `/student/hub`
   - Chat: `/mental-chatbot`

2. **Set up monitoring** (optional):
   - Render → **Monitoring** tab
   - Set up alerts for errors

3. **Enable auto-deploy** if you haven't:
   - Every git push rebuilds instantly

4. **Share your URL** with testers:
   - `https://aura-student-wellness.onrender.com`

---

**Deployment complete! 🎉**

Your AURA app is now live and accessible 24/7 (with free tier auto-spindown).
