# 🔑 API Key Setup Guide

## Problem
Your Gemini API key was **leaked and disabled** by Google. You're getting error:
```
403 PERMISSION_DENIED: Your API key was reported as leaked. Please use another API key.
```

## Solution - Get a New Gemini API Key

### Step 1: Get New API Key
1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the new key (starts with `AIza...`)

### Step 2: Update .env File
Open `D:\AURA\.env` and replace the old key:

```env
GEMINI_API_KEY=YOUR_NEW_KEY_HERE
```

**Example:**
```env
GEMINI_API_KEY=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567
```

### Step 3: Restart Server
```powershell
# Stop server (Ctrl+C in terminal)
# Then restart:
D:\AURA\.venv\Scripts\python.exe app.py
```

### Step 4: Test
1. Open http://127.0.0.1:5000/student/chat/mental
2. Send message: "hi"
3. You should get a proper AI response (not generic fallback)

## Alternative: Use Free Groq API (Llama)

If you want a free alternative:

1. Visit [Groq Console](https://console.groq.com/keys)
2. Sign up and create API key
3. Add to `.env`:
```env
GROQ_API_KEY=gsk_your_groq_key_here
```

AURA will automatically use Groq if Gemini fails.

## Security Tips

✅ **DO:**
- Keep `.env` file local only
- Use `.env.template` for sharing code
- Verify `.env` is in `.gitignore`

❌ **DON'T:**
- Commit `.env` to Git
- Share API keys in screenshots
- Paste keys in public forums

## Current Status

Your API linkage is **working correctly** - the code is properly connected:
- ✅ Frontend → `/api/chat/mental` endpoint
- ✅ Backend → `services/ai_service.py`
- ✅ Gemini client initialization
- ❌ API key is disabled (needs replacement)

Once you add a new key, the AI will work immediately!
