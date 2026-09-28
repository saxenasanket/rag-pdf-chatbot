# Railway Deployment Guide

Complete step-by-step guide to deploy this RAG chatbot to Railway.

## Prerequisites

1. **GitHub Account** (free at github.com)
2. **Railway Account** (free at railway.app)
3. **GitHub CLI** (optional but recommended)

## Step 1: Create a GitHub Repository

### Option A: Using GitHub Web UI (Easiest)

1. Go to https://github.com/new
2. Enter repository name: `rag-pdf-chatbot`
3. Choose **Public** or **Private**
4. Click **Create repository**
5. You'll see commands to push your code

### Option B: Using GitHub CLI (Fastest)

```bash
# Install GitHub CLI (if not already installed)
# On macOS: brew install gh
# Then authenticate:
gh auth login

# Create repository
gh repo create rag-pdf-chatbot --source=. --remote=origin --push
```

## Step 2: Push Code to GitHub

```bash
cd /Users/sanketsaxena/Documents/rag-pdf

# Add GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/rag-pdf-chatbot.git

# Rename branch to main (Railway prefers main over master)
git branch -M main

# Push code to GitHub
git push -u origin main
```

You should see:
```
Counting objects: 22, done.
Delta compression using up to 8 threads.
Compressing objects: 100% (20/20), done.
Writing objects: 100% (22/22), ...
To https://github.com/YOUR_USERNAME/rag-pdf-chatbot.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

✅ Code is now on GitHub!

## Step 3: Deploy to Railway

### Option A: Using Railway Web UI (Recommended for First Deploy)

1. Go to https://railway.app/dashboard
2. Sign up or log in with GitHub
3. Click **+ New Project** → **Deploy from GitHub repo**
4. Select your `rag-pdf-chatbot` repository
5. Railway auto-detects the Dockerfile
6. Click **Deploy**

Railway will:
- Build the Docker image
- Start the container
- Assign a public URL

### Option B: Using Railway CLI (Faster)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# In your project directory
cd /Users/sanketsaxena/Documents/rag-pdf

# Initialize Railway project
railway init

# Deploy
railway up
```

## Step 4: Configure Environment Variables

**IMPORTANT:** Set your API keys in Railway!

### Via Railway Web UI:

1. Go to https://railway.app/dashboard
2. Select your `rag-pdf-chatbot` project
3. Click **Variables** tab
4. Add these variables:

```
ANTHROPIC_API_KEY=sk-ant-your-actual-key
VOYAGE_API_KEY=pa-your-actual-key
EMBEDDING_PROVIDER=voyage
CLAUDE_MODEL=claude-sonnet-5
CHROMA_DIR=/app/data/chroma
UPLOAD_DIR=/app/data/uploads
TOP_K=5
```

5. Click **Save**
6. Railway redeploys automatically

### Via Railway CLI:

```bash
railway variable add ANTHROPIC_API_KEY sk-ant-your-actual-key
railway variable add VOYAGE_API_KEY pa-your-actual-key
railway variable add EMBEDDING_PROVIDER voyage
railway variable add CLAUDE_MODEL claude-sonnet-5
```

## Step 5: Verify Deployment

Once deployed, Railway gives you a public URL like:
```
https://rag-pdf-chatbot-production.up.railway.app
```

**Test the health endpoint:**
```bash
curl https://rag-pdf-chatbot-production.up.railway.app/health
# Should return: {"status":"ok"}
```

**Open in browser:**
```
https://rag-pdf-chatbot-production.up.railway.app
```

You should see the RAG chatbot UI! 🎉

## Important Notes

### Data Persistence

⚠️ **Critical:** Railway containers are ephemeral. When you redeploy or the container restarts:
- `data/chroma/` is wiped (vector database lost)
- `data/uploads/` is wiped (PDFs lost)
- `data/documents.json` is wiped (registry lost)

**Solution:** Use Railway's **Persistent Volumes**

1. In Railway dashboard → Your project → Settings
2. Go to **Volumes**
3. Add volume `/app/data` (mount path)
4. Restart the service

Now `data/` persists across deploys!

### Environment Variables

Never commit `.env` to GitHub! Railway provides them securely:
- ✅ Set in Railway dashboard (secure)
- ❌ Never put in `.env` file (exposes keys)
- ❌ Never put in code (public repository)

### Scaling & Performance

**Railway Free Tier:**
- 500 free hours/month ($5/additional hour)
- Sufficient for small projects
- Auto-pause after 30 minutes of inactivity

**Upgrades:**
- Scale to multiple instances
- Higher memory/CPU if needed
- Scales as you go

## Monitoring & Troubleshooting

### View Logs

```bash
# Via CLI
railway logs

# Via Web UI
Dashboard → Your project → Logs tab
```

**Common Issues:**

**1. Dockerfile build fails**
```
Error: python:3.13-slim not found
```
→ Change `python:3.13` to `python:3.11` in Dockerfile (more stable)

**2. Port not exposed**
```
Error: Connection refused on port 8000
```
→ Railway automatically maps PORT env var, Dockerfile already has `--port 8000`

**3. API key errors**
```
RuntimeError: ANTHROPIC_API_KEY is required
```
→ Check Variables in Railway dashboard, make sure they're set

**4. Uploads lost after restart**
→ Add persistent volume at `/app/data`

## Continuous Deployment

Once set up, every time you push to GitHub:

```bash
git add -A
git commit -m "Update: [description]"
git push origin main
```

Railway automatically:
1. Detects the push
2. Rebuilds the Docker image
3. Redeploys the container
4. Keeps your volumes intact (if configured)

## Monitoring Costs

Railway charges by usage:
- **Compute:** $0.000463/minute per vCPU
- **Memory:** $0.000150/minute per GB

Rough estimate for this app:
- **Small project (< 100 PDFs, < 1000 queries/month):** ~$5-10/month
- **Medium (1000+ PDFs, 10K+ queries/month):** ~$20-50/month

Check costs in Railway dashboard → Billing.

## Troubleshooting Checklist

- [ ] GitHub repo created and code pushed
- [ ] Railway project created and connected to GitHub
- [ ] Environment variables set (ANTHROPIC_API_KEY, VOYAGE_API_KEY)
- [ ] Build logs show no errors
- [ ] Health endpoint responds (`/health`)
- [ ] Frontend loads in browser
- [ ] Persistent volume added for `data/` directory
- [ ] Test upload PDF and chat

## Next Steps

1. **Monitor the deployment** — Check Railway logs for any errors
2. **Test functionality** — Upload a PDF, ask a question
3. **Set up monitoring** — Enable Railway alerts for crashes
4. **Add custom domain** — Point your domain to Railway (optional)
5. **Scale if needed** — Upgrade plan if hitting limits

## Support

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **This Project Repo:** https://github.com/YOUR_USERNAME/rag-pdf-chatbot

---

**Your app is now live on the internet!** 🚀
