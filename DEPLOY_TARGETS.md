# Deployment Targets

This file summarizes where each environment deploys, and which secrets are used.

## Dev Deployment
- Workflow: `.github/workflows/deploy-dev.yml`
- Trigger branch: `dev`
- Frontend deploy target: Vercel `preview`
- Backend deploy target: Railway environment `dev`
- Migration database secret: `DEV_DATABASE_URL`
- Backend health check secret: `DEV_BACKEND_URL`

## Prod Deployment
- Workflow: `.github/workflows/deploy-prod.yml`
- Trigger branch: `main`
- Frontend deploy target: Vercel `production` (`--prod`)
- Backend deploy target: Railway environment `production`
- Migration database secret: `PROD_DATABASE_URL`
- Backend health check secret: `PROD_BACKEND_URL`

## Shared Deployment Secrets
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `RAILWAY_TOKEN`
