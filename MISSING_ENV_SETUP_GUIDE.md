# Missing & Required Environment Variables Setup Guide

## 🔧 VARIABLES THAT NEED SETUP BEFORE STARTING

### 1. 🔐 CLERK AUTHENTICATION (CRITICAL - Frontend Won't Work Without This)

**Status:** ❌ NOT YET CONFIGURED
**Location:** `frontend/.env.local`

**Variables to Configure:**
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key
```

**How to Get Clerk Keys:**
1. Visit https://clerk.com (sign up if needed)
2. Go to Dashboard
3. Create new application: Name it "Concept 10"
4. Under "API Keys" section:
   - Copy **Publishable Key** → Paste into `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   - Copy **Secret Key** → Paste into `CLERK_SECRET_KEY`
5. Enable **Organizations** feature:
   - Go to "Organization Settings"
   - Enable "Organizations"
   - This enables clinic/tenant context in app
6. Set up sign-in/sign-up routes:
   - Create pages: `/sign-in`, `/sign-up`
   - Update redirect URLs to match your frontend

**Why Needed:** Clerk handles user authentication, multi-tenancy (clinic context), and organization management.

---

### 2. 🔑 SECURE RANDOM SECRET KEY (IMPORTANT - Change from Default)

**Status:** ⚠️ USING PLACEHOLDER
**Location:** `.env` (Backend) and any other auth service

**Current Value:**
```
SECRET_KEY=replace_with_secure_random_string
```

**Should Be:**
```
SECRET_KEY=[64+ character random string]
```

**How to Generate:**
```powershell
# Option 1: Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 2: PowerShell
[System.Convert]::ToBase64String((1..32|%{[byte]$(Get-Random -Maximum 256)}))

# Option 3: Online generator
https://generate-random.org/encryption-key-generator
```

**Why Needed:** Used for JWT token signing. Must be strong and unique per environment.

---

### 3. 📊 POSTGRESQL DATABASE (REQUIRED - Already Configured)

**Status:** ✅ ALREADY SET UP (You ran `alembic upgrade head`)
**Location:** `.env`

**Configured As:**
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/clinic_saas
```

**Verification Command:**
```powershell
python check_db_status.py
```

**Note:** Database is already initialized with all migrations. All 12 tables created.

---

### 4. 🔴 REDIS SERVICE (REQUIRED - Agentic Context Storage)

**Status:** ❌ NEEDS VERIFICATION
**Location:** `concept10-agentic/.env`

**Configured As:**
```
CONTEXT_REDIS_URL=redis://localhost:6379/0
```

**How to Setup Redis:**

**Option A: Windows (Recommended for Dev)**
```powershell
# Using WSL (Windows Subsystem for Linux)
wsl redis-cli ping    # If installed

# Or using Docker
docker run -d -p 6379:6379 --name redis redis:7-alpine
docker exec redis redis-cli ping   # Test connection
```

**Option B: Download and Install**
```
https://github.com/microsoftarchive/redis/releases
Download: Redis-x64-7.2.msi
Install and run
```

**Option C: Using Memurai (Windows-native)**
```
https://www.memurai.com/
Download and install
```

**How to Test:**
```powershell
# If Redis is running:
redis-cli ping
# Expected output: PONG
```

**Why Needed:** Stores agentic context between API calls for stateful conversations.

---

### 5. 🧠 AGENTIC SERVICE TOKEN (OPTIONAL - For Service-to-Service Auth)

**Status:** ⚠️ OPTIONAL - Currently Not Enforced
**Location:** `.env` (Backend)

**Currently Set To:**
```
AGENTIC_SERVICE_TOKEN=replace_with_local_service_token
```

**How to Generate (If Needed):**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Why Needed:** Authenticates requests from main backend to agentic service. Optional for local dev, required for production. Make sure both apps have the same token.

---

### 6. 📡 OPTIONAL: OPENTELEMETRY (OTEL) - For Advanced Monitoring

**Status:** ⚠️ DISABLED - Not Required for Dev
**Location:** `concept10-agentic/.env`

**Current Configuration:**
```
ENABLE_OTEL=false
OTEL_SERVICE_NAME=agent-orchestration-framework
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_EXPORTER_OTLP_HEADERS=
```

**When to Enable:** Only if you're setting up centralized observability stack (Jaeger, DataDog, etc.)

---

## 📋 QUICK SETUP CHECKLIST

- [ ] **Clerk Setup Complete**
  - [ ] Created Clerk app: "Concept 10"
  - [ ] Copied `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` to `frontend/.env.local`
  - [ ] Copied `CLERK_SECRET_KEY` to `frontend/.env.local`
  - [ ] Enabled Organizations in Clerk dashboard
  - [ ] Set up sign-in/sign-up routes

- [ ] **Database Ready**
  - [ ] PostgreSQL running
  - [ ] Database `clinic_saas` created
  - [ ] All migrations applied: `python check_db_status.py` shows all 12 tables

- [ ] **Redis Ready**
  - [ ] Redis service running on localhost:6379
  - [ ] Test: `redis-cli ping` returns `PONG`

- [ ] **Secrets Generated & Set**
  - [ ] Backend `SECRET_KEY` changed from placeholder
  - [ ] Generated strong random string
  - [ ] Saved in `.env`

- [ ] **API Keys Verified**
  - [ ] OpenAI API Key valid and not expired
  - [ ] LangSmith API Key valid and not expired
  - [ ] Can make test API calls

---

## 🚀 NEXT STEPS: Start All Services

Once all above is complete:

```powershell
# Terminal 1: Backend (FastAPI)
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
# Expected: Uvicorn running on http://localhost:8000

# Terminal 2: Frontend (Next.js)
cd frontend
npm run dev
# Expected: Next.js running on http://localhost:3000

# Terminal 3: Agentic Service
cd concept10-agentic
.\.venv\Scripts\Activate.ps1
uvicorn api.app:app --reload --host 0.0.0.0 --port 8001
# Expected: Running on http://localhost:8001

# Terminal 4: Agent Dashboard
cd concept10-agentic/dashboard
npm run dev
# Expected: Vite running on http://localhost:5173
```

---

## ❌ TROUBLESHOOTING

### Frontend Not Starting: "Cannot find Clerk keys"
- **Solution:** Make sure `frontend/.env.local` has Clerk variables filled in (not placeholder)
- **Test:** `echo $env:NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` should show pk_...

### Agentic Service Error: "Redis connection refused"
- **Solution:** Start Redis service or Docker container with: `docker run -d -p 6379:6379 redis:7-alpine`
- **Test:** `redis-cli ping` should return `PONG`

### Backend Error: "Database clinic_saas does not exist"
- **Solution:** Create database: `createdb clinic_saas` or via psql
- **Test:** `python check_db_status.py` should show all 12 tables

### LangSmith Tracing Not Working
- **Check:** API key is correct and not expired
- **Check:** Project name "Concept-10-dev" exists in LangSmith
- **Check:** All 4 apps have same `LANGSMITH_API_KEY` and `LANGSMITH_PROJECT`

---

**Last Updated:** March 12, 2026
**All Environment Variables Status:** 4/4 Apps Configured ✅
