# 🚀 Deploy to Railway Now — 5 Minutes

Quick checklist to get your app live in 5 minutes.

## Your Code is Ready ✅

All necessary files created:
- ✅ `Dockerfile` — Container configuration
- ✅ `railway.json` — Railway deployment config
- ✅ `.railwayignore` — Exclude unnecessary files
- ✅ `.git/` — Git repository initialized
- ✅ Code committed and ready to push

## Step 1: Create GitHub Repository (2 minutes)

Go to https://github.com/new and create a repo named `rag-pdf-chatbot`

Copy the commands shown (they'll look like):
```bash
git remote add origin https://github.com/YOUR_USERNAME/rag-pdf-chatbot.git
git branch -M main
git push -u origin main
```

## Step 2: Push Your Code (1 minute)

```bash
cd /Users/sanketsaxena/Documents/rag-pdf

# Replace YOUR_USERNAME in the URL below
git remote add origin https://github.com/YOUR_USERNAME/rag-pdf-chatbot.git
git branch -M main
git push -u origin main
```

Your code is now on GitHub! ✅

## Step 3: Deploy to Railway (1 minute)

1. Go to https://railway.app/dashboard
2. Click **+ New Project** → **Deploy from GitHub repo**
3. Select `rag-pdf-chatbot`
4. Click **Deploy**

Railway builds and deploys automatically. ✅

## Step 4: Add Environment Variables (1 minute)

While Railway is building, go to **Variables** tab and add:

```
ANTHROPIC_API_KEY=sk-ant-your-actual-key
VOYAGE_API_KEY=pa-your-actual-key
EMBEDDING_PROVIDER=voyage
CLAUDE_MODEL=claude-sonnet-5
CHROMA_DIR=/app/data/chroma
UPLOAD_DIR=/app/data/uploads
TOP_K=5
```

Save. Railway redeploys automatically. ✅

## Step 5: Add Persistent Volume (30 seconds)

Critical! Otherwise PDFs and embeddings are lost on restart.

1. Railway dashboard → Your project → **Settings**
2. Go to **Volumes**
3. Click **Add Volume**
4. Mount path: `/app/data`
5. Click **Create**

✅ Done!

## Access Your App

After deploy completes, Railway gives you a URL like:
```
https://rag-pdf-chatbot-production.up.railway.app
```

**Open it in browser and test!** 🎉

## Verify It Works

```bash
# Test health endpoint
curl https://rag-pdf-chatbot-production.up.railway.app/health

# Should return:
# {"status":"ok"}
```

Then:
1. Upload a PDF
2. Ask a question
3. See the answer with citations ✨

## If Something Goes Wrong

Check Railway logs:
```bash
# Via CLI (if installed)
railway logs

# Via Web UI
Dashboard → Your project → Logs tab
```

Common issues:
- **Build fails:** Check Dockerfile syntax
- **API key errors:** Verify Variables are set in Railway
- **Port error:** Already fixed in Dockerfile
- **Data lost after restart:** Add persistent volume

---

**That's it!** Your RAG chatbot is live on the internet! 🚀

Full details in `RAILWAY_DEPLOYMENT.md` if you need them.
