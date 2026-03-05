# 📖 Deployment Guide - Deep Research Agent V0.3

## Executive Summary

The Deep Research Agent is now **production-ready**. This guide walks through deploying to cloud platforms (Vercel + Railway/Render), configuring environments, and monitoring.

**Quick Timeline:**
- Local Setup: 15 minutes
- Backend Deployment: 10 minutes
- Frontend Deployment: 10 minutes
- Testing: 20 minutes
- **Total: ~1 hour**

---

## Part 1: Pre-Deployment Checklist

### 1.1 Local Verification

Before deploying, verify everything works locally:

```bash
# Terminal 1: Backend
cd backend
python verify_deployment.py
# Expected: ✅ All 25 checks pass

# Terminal 2: Frontend
cd frontend
npm run build
# Expected: ✓ Compiled successfully
```

### 1.2 Environment Variables

Copy the template and fill in API keys:

```bash
cp .env.example .env
```

Edit `.env` with required keys:
- [ ] `OPENROUTER_API_KEY` - [Get from](https://openrouter.ai/keys)
- [ ] `GROQ_API_KEY` - [Get from](https://console.groq.com/keys)
- [ ] `TAVILY_API_KEY` - (optional) [Get from](https://tavily.com)

### 1.3 Local Testing

```bash
# Terminal 1: Start backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Start frontend
cd frontend
npm run dev

# Terminal 3: Test
curl http://localhost:8000/health
# Should return: {"status": "ok"}

# Browser: http://localhost:3000
# Should see: Research interface with sidebar
```

---

## Part 2: Backend Deployment (Railway/Render)

### Option A: Railway.app (Recommended)

**Step 1: Create Railway Account**
- Go to https://railway.app
- Sign up with GitHub
- Authorize Railway access

**Step 2: Create New Service**
- Click "Create New Service"
- Select "Deploy from GitHub repo"
- Select your deep_research_agent repo
- Railway auto-detects Python project

**Step 3: Configure Environment**
- In Railway dashboard, click your service
- Open "Variables" tab
- Add these variables (paste from your .env):
  ```
  OPENROUTER_API_KEY=sk-...
  GROQ_API_KEY=gsk-...
  TAVILY_API_KEY=tvly-...
  DATABASE_URL=sqlite+aiosqlite:///./oracle.db
  BACKEND_PORT=8000
  ENVIRONMENT=production
  DEBUG=false
  ```

**Step 4: Configure Build & Start**
- Go to "Settings" tab
- Set Python version: 3.11
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker`

**Step 5: Deploy**
- Railway auto-deploys on push
- Check "Deployments" tab for status
- Wait for green checkmark (2-5 minutes)

**Step 6: Get Backend URL**
- Click "Networking" tab
- Copy publicly available URL (e.g., `https://deepresearch-api.railway.app`)
- This is your `BACKEND_URL`

### Option B: Render.com

**Step 1: Create Render Account**
- Go to https://render.com
- Sign up with GitHub

**Step 2: Create New Web Service**
- Dashboard → "New +" → "Web Service"
- Connect GitHub repo
- Authorize Render

**Step 3: Configure Service**
- **Name:** deep-research-backend
- **Environment:** Python 3
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker`

**Step 4: Add Environment Variables**
- Click "Environment" in left sidebar
- Add each variable from .env

**Step 5: Deploy**
- Click "Create Web Service"
- Wait for deployment complete (5-10 minutes)
- Copy service URL (e.g., `https://deepresearch-backend.onrender.com`)

---

## Part 3: Frontend Deployment (Vercel)

### Step 1: Create Vercel Account
- Go to https://vercel.com
- Sign up with GitHub
- Authorize Vercel

### Step 2: Import Project
- Dashboard → "Add New..." → "Project"
- Select your deep_research_agent repo
- Root directory: `frontend`

### Step 3: Configure Environment
- Click "Environment Variables"
- Add this variable:
  ```
  NEXT_PUBLIC_API_URL=<YOUR_BACKEND_URL>
  ```
  (Replace with Railway/Render URL from Part 2)

### Step 4: Build & Deploy
- Click "Deploy"
- Wait for build complete (2-3 minutes)
- Vercel assigns URL (e.g., `https://deepresearch.vercel.app`)

### Step 5: Test Deployed Frontend
- Visit your Vercel URL
- Should see: Research interface loading
- Check "Deployments" tab for logs if error

---

## Part 4: Database Configuration

### Option A: SQLite (Current - Simple)
Works out of the box. Data stored in `oracle.db` on server.

**Pros:**
- No setup needed
- Works offline
- Free

**Cons:**
- Only 1 concurrent write
- Data lost if server restarts (unless persistent storage)
- Not ideal for multiple servers

**For Railway/Render:**
- SQLite file stored in ephemeral filesystem
- Loss on deployment refresh
- **Upgrade to PostgreSQL for production**

### Option B: PostgreSQL (Recommended for Production)

**Create PostgreSQL Database:**

**On Railway.com:**
1. In dashboard, click service
2. "Infrastructure" tab
3. "Create new" → "PostgreSQL"
4. Copy auto-generated connection string

**On Render.com:**
1. Dashboard → "New +" → "PostgreSQL"
2. Fill in database name (e.g., deep-research)
3. Copy connection string

**Update Environment Variable:**
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

**Run Migrations:**
```bash
# Ensure database URL set
export DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# Create tables (if using Alembic)
alembic upgrade head

# Or run initialization script
python -c "from app.database import Base, engine; Base.metadata.create_all(engine)"
```

---

## Part 5: Testing Deployment

### 5.1 Backend API Tests

```bash
# Replace with your backend URL
BACKEND_URL="https://deepresearch-api.railway.app"

# Test health
curl $BACKEND_URL/health

# Test user creation
curl -X POST $BACKEND_URL/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"TestUser","is_anonymous":false}'

# Test answer endpoint
curl -X POST $BACKEND_URL/api/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question":"What is artificial intelligence?",
    "source_ids":[],
    "user_id":"test-user-123",
    "conversation_id":"test-conv-123"
  }'
```

### 5.2 Frontend Tests

1. **Visit deployed URL** (e.g., https://deepresearch.vercel.app)
2. **Test user creation:**
   - Should auto-create anonymous user
   - Check localStorage has `user_id`
3. **Test conversation:**
   - Click "New Conversation"
   - Ask a question
   - Response should stream in
4. **Test persistence:**
   - Refresh page
   - Conversation should still be there
   - Messages should still display

### 5.3 Integration Test

Complete flow:
```
1. Visit frontend URL
2. Auto-creates anonymous user ✓
3. Creates new conversation ✓
4. Asks question ✓
5. Backend processes through pipeline ✓
6. Response streams to frontend ✓
7. Message saved to database ✓
8. Sidebar shows conversation ✓
9. Refresh page
10. Data persists ✓
```

---

## Part 6: Post-Deployment Configuration

### 6.1 CORS Configuration

Add your frontend URL to CORS in backend:

**backend/app/main.py:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://deepresearch.vercel.app",  # Your Vercel URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then redeploy backend.

### 6.2 Error Tracking (Optional)

**Add Sentry for error monitoring:**

```bash
pip install sentry-sdk
```

In `backend/app/main.py`:
```python
import sentry_sdk

sentry_sdk.init(
    dsn="https://your-sentry-dsn@sentry.io/project",
    traces_sample_rate=0.1,
)
```

### 6.3 Performance Monitoring (Optional)

**Vercel automatically tracks:**
- Page speed
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Cumulative Layout Shift (CLS)

Dashboard available at: https://vercel.com/dashboard/analytics

---

## Part 7: Maintenance & Monitoring

### 7.1 Weekly Tasks
- [ ] Check error logs (Railway/Render dashboard)
- [ ] Monitor database size
- [ ] Check API key quota usage
- [ ] Review response times (Vercel Analytics)

### 7.2 Monthly Tasks
- [ ] Review cost metrics
- [ ] Update dependencies (`pip install -U -r requirements.txt`)
- [ ] Backup database
- [ ] Plan feature releases

### 7.3 As-Needed Tasks
- [ ] Redeploy on code changes (auto via GitHub)
- [ ] Update environment variables (via platform dashboard)
- [ ] Scale workers if needed (in Railway/Render settings)

---

## Part 8: Troubleshooting

### Backend won't start
```bash
# Check logs
railway logs  # or render logs

# Common issues:
# - Missing API keys in environment
# - Database connection string wrong
# - Port already in use

# Solution: Verify DATABASE_URL and API keys
```

### Frontend won't deploy
```bash
# Check Vercel logs
# Common issues:
# - NEXT_PUBLIC_API_URL not set
# - TypeScript errors in build
# - Wrong root directory (should be 'frontend')

# Solution: Check build logs, fix TypeScript errors
```

### Conversations not persisting
```bash
# Issues:
# - Using SQLite with ephemeral storage
# - Database not initialized
# - user_id/conversation_id not passed to API

# Solution:
# 1. Migrate to PostgreSQL
# 2. Run migrations: alembic upgrade head
# 3. Check that frontend sends user_id in requests
```

### Slow responses
```bash
# Check:
1. API rate limits (OpenRouter/Groq)
2. Database query performance
3. Network latency (use CDN)
4. LLM model response time

# Solutions:
1. Implement request caching
2. Use faster models
3. Add database indexes
4. Move to better region
```

---

## Part 9: Scaling & Performance

### When to Scale
- **Frontend:** Automatic with Vercel edge network
- **Backend:** When >100 concurrent users
  - Increase worker count in Railway/Render
  - Use PostgreSQL (SQLite has concurrency limits)
  - Add Redis for caching
- **Database:** When >10GB data
  - Migrate to managed PostgreSQL with replicas
  - Add read replicas for queries
  - Archive old conversations

### Performance Optimization
- [ ] Enable compression (automatic on Vercel/Railway)
- [ ] Implement response caching (Redis)
- [ ] Use faster API models (DeepSeek is cheaper)
- [ ] Add CDN in front (CloudFlare)

---

## Part 10: Next Steps

### Phase 4: Authentication (Recommended)
```
- Add email/password signup
- OAuth integration (Google, GitHub)
- Session tokens instead of localStorage IDs
- See QUICK_REFERENCE.md for implementation
```

### Phase 5: Advanced Features
```
- Conversation export (PDF/Markdown)
- Conversation sharing
- Custom system prompts
- Conversation search
```

### Phase 6: Analytics
```
- Usage dashboard
- Cost analytics
- Popular topics
- Quality metrics
```

---

## Deployment Checklist Summary

```
PRE-DEPLOYMENT
☑ Local verify passes (python verify_deployment.py)
☑ Frontend builds (npm run build)
☑ .env file filled with API keys

BACKEND DEPLOYMENT
☑ Railway/Render account created
☑ GitHub connected
☑ Environment variables set
☑ Build/start commands configured
☑ Service deployed (green status)
☑ Backend URL copied

FRONTEND DEPLOYMENT
☑ Vercel account created
☑ GitHub connected
☑ NEXT_PUBLIC_API_URL set to backend URL
☑ Build successful
☑ Deployed URL obtained

DATABASE
☑ SQLite working OR PostgreSQL configured
☑ Schema created
☑ Test connection works

TESTING
☑ Backend health check passes
☑ API endpoints respond
☑ Frontend loads
☑ Full flow tested (create user → conversation → message)
☑ Data persists after refresh

MONITORING
☑ Error tracking configured (optional)
☑ Performance monitoring enabled
☑ Backup strategy in place
☑ Team notified of deployment

GO LIVE
✅ All checks passed - Ready for production!
```

---

## Support & Resources

**Official Documentation:**
- Railway: https://docs.railway.app
- Render: https://render.com/docs
- Vercel: https://vercel.com/docs
- Next.js: https://nextjs.org/docs
- FastAPI: https://fastapi.tiangolo.com

**API Providers:**
- OpenRouter: https://openrouter.ai/docs
- Groq: https://console.groq.com/docs
- Tavily: https://tavily.com/docs

**Common Questions:**
- Q: How do I update the app after deployment?
  - A: Push to GitHub → Railway/Render auto-deploy → Vercel auto-deploy
- Q: How do I monitor errors?
  - A: Check platform dashboards (Railway/Render/Vercel logs)
- Q: How do I scale the backend?
  - A: Increase worker count in Railway/Render settings
- Q: How do I add a new feature?
  - A: Code locally → test → push → auto-deploy

---

**Deployment completed:** [Date]  
**Status:** ✅ Production-Ready  
**Version:** 0.3  

Questions? Check QUICK_REFERENCE.md or implementation docs.
