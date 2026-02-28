# Concept 10 FastAPI Backend

For full machine setup (backend + frontend), see [NEW_DEVELOPER_SETUP.md](NEW_DEVELOPER_SETUP.md).

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

## Notes

- Public route: `POST /api/v1/auth/login`
- Protected route example: `GET /api/v1/clinics/me`
- Middleware injects `request.state.user_id` and `request.state.clinic_id`
