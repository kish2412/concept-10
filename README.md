# Concept 10 FastAPI Backend

For full machine setup (backend + frontend), see [NEW_DEVELOPER_SETUP.md](NEW_DEVELOPER_SETUP.md).
For MVP deployment (Vercel + Railway), see [DEPLOYMENT_MVP_OPTION1.md](DEPLOYMENT_MVP_OPTION1.md).

Multi-tenant FastAPI boilerplate with:

- Async PostgreSQL via SQLAlchemy 2.0
- Alembic migrations
- JWT auth middleware carrying `clinic_id` tenant context
- CORS configured for Next.js frontend origins
- `.env` settings via `pydantic-settings`

## Project Structure

```
app/
  api/
  core/
  models/
  schemas/
  services/
alembic/
```

## Quick Start

1. Create virtual environment and install deps:

   ```bash
   pip install -r requirements.txt
   ```

2. Create environment file:

   ```bash
   copy .env.example .env
   ```

3. Run migrations:

   ```bash
   alembic revision --autogenerate -m "init"
   alembic upgrade head
   ```

4. Start API:

   ```bash
   uvicorn app.main:app --reload
   ```

## Run Backend and Frontend Together

Use two terminals during daily development.

1. Start backend (Terminal A, repo root):

   ```powershell
   Set-Location "c:\Users\kisho\Desktop\Concept 10 - New Project"
   .\.venv\Scripts\Activate.ps1
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

   Backend runs at `http://localhost:8000`.

2. Start frontend (Terminal B):

   ```powershell
   Set-Location "c:\Users\kisho\Desktop\Concept 10 - New Project\frontend"
   npm.cmd install
   npm.cmd run dev
   ```

   Frontend runs at `http://localhost:3000`.

For first-time machine setup (including env files and Clerk config), use `NEW_DEVELOPER_SETUP.md`.

## Git Workflow (dev -> main)

### Step 1: Commit Current Code to `dev`

1. Make sure your local `dev` is up to date:

   ```powershell
   git checkout dev
   git pull origin dev
   ```

2. Create a feature branch from `dev`:

   ```powershell
   git checkout -b feature/short-description
   ```

3. Commit your current changes:

   ```powershell
   git add .
   git commit -m "feat: short description"
   ```

4. Push the feature branch:

   ```powershell
   git push -u origin feature/short-description
   ```

5. Open a Pull Request: `feature/short-description` -> `dev`.

6. After approval, merge PR to `dev` and confirm the dev deployment is healthy.

### Step 2: After Testing Dev, Merge `dev` to `main`

1. Sync both branches:

   ```powershell
   git checkout dev
   git pull origin dev
   git checkout main
   git pull origin main
   ```

2. Open a Pull Request: `dev` -> `main`.

3. After approval, merge PR to `main`.

4. Pull latest `main` locally:

   ```powershell
   git checkout main
   git pull origin main
   ```

5. Confirm production deployment is successful.

If `dev` changes while you are still working on a feature branch, merge or rebase latest `dev` into your branch before final review.

## Notes

- Public route: `POST /api/v1/auth/login`
- Protected route example: `GET /api/v1/clinics/me`
- Middleware injects `request.state.user_id` and `request.state.clinic_id`
