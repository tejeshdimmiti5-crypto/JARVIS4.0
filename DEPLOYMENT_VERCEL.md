# Vercel deployment checklist (review branch)

This guide prepares JARVIS4.0 for a Vercel Services deployment. It does not deploy the project, create cloud accounts, or store secrets in Git.

## Current branch

Use `review/vercel-free-hosting` for review. Do not merge into `main` until the build, database migration, and smoke tests pass.

## Free-tier services to create

1. **Neon PostgreSQL** for accounts, notes, chat history, subjects, tasks, flashcards, and analytics.
   - Create a PostgreSQL project on the Free plan.
   - Copy its pooled/runtime connection string from the Neon dashboard.
   - Set it as Vercel's `DATABASE_URL`. Do not commit the URL.
   - Current Neon Free plan information lists 1 GB storage per project and 100 compute-hours per month; check the pricing page for current quotas before relying on them.

2. **Qdrant Cloud Free** for durable PDF semantic-search vectors.
   - Create a free cluster, then copy the cluster HTTPS URL and a cluster API key.
   - Configure `QDRANT_URL` and `QDRANT_API_KEY` in Vercel.
   - Set `QDRANT_COLLECTION=jarvis_documents` (or leave it unset).
   - The app creates the collection on the first successful indexing operation.
   - Qdrant's free cluster can suspend after one week of inactivity and may be deleted after four weeks if not reactivated. It is free, but not a substitute for backups.

## Vercel project settings

1. Import this repository in Vercel, selecting branch `review/vercel-free-hosting` for review.
2. In **Settings → Build and Deployment**, set the project framework to **Services**. The root `vercel.json` will not activate multi-service builds if the dashboard framework is left on Vite or another framework.
3. Keep the root directory at the repository root so Vercel can see `vercel.json`.
4. Do not add a paid add-on or upgrade the Vercel plan. If Services is unavailable on the account, stop and report that rather than changing the architecture or upgrading.

## Environment variables

Add these through Vercel's Environment Variables UI. Use Production and Preview scopes deliberately; never put values in source control.

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Neon PostgreSQL connection string (use the pooled URL for runtime if Neon recommends it) |
| `JWT_SECRET` | A newly generated random secret with at least 32 characters |
| `GEMINI_API_KEY` | Your Gemini API key; add this yourself |
| `GEMINI_MODEL` | A currently supported Gemini model available to your account |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` unless your Gemini account uses a different supported embedding model |
| `AI_ENGINE` | `auto` |
| `QDRANT_URL` | Qdrant cluster HTTPS URL |
| `QDRANT_API_KEY` | Qdrant cluster API key |
| `QDRANT_COLLECTION` | `jarvis_documents` |

Do not share the Gemini key, database URL, JWT secret, or Qdrant key in chat. Add them only in the provider's secret/environment-variable UI. If a key was ever committed to Git, rotate it.

## Database initialization

The Vercel service does not run the Docker `entrypoint.sh` automatically. Initialize the newly created database once, from a trusted local terminal with the server dependencies installed and `DATABASE_URL` set in that terminal:

```bash
cd server
alembic upgrade head
```

Never paste the connection string into a public issue, commit, or build log. Do not point this command at an existing production database unless you have verified the migration plan and a backup.

## Smoke-test checklist before production

- [ ] Vercel Services build completes for both services.
- [ ] `GET /api/health` returns `status: ok`, `database: true`, and `vector_store: qdrant`.
- [ ] Register a test account and log in.
- [ ] Create a note, refresh, and verify it remains.
- [ ] Upload a small text-based PDF, verify indexed chunks are non-zero, and run a document-specific search.
- [ ] Confirm requests use same-origin `/api/...` paths in the production frontend.
- [ ] Review logs for missing environment variables, dependency/bundle-size errors, and database connection failures.
- [ ] Confirm no secret is present in the branch diff.

## Known limitations to verify

- Vercel's Functions request/response body limit is 4.5 MB. PDF uploads larger than that may be rejected before FastAPI receives them, even though the app's own PDF parser currently allows larger files. Test small PDFs on Vercel; supporting larger PDFs requires a direct-to-object-storage upload flow or another backend host.
- FastAPI is bundled into a Vercel Python Function. The dependency bundle must stay within Vercel's documented limit (500 MB for Python functions). Build output is the evidence; do not assume it fits just because requirements install locally.
- Qdrant vector search requires both Qdrant variables. Without them, the API can start and text extraction can run, but vector indexing/search is disabled. Add the variables before testing semantic PDF retrieval.
- Database schema migrations must be applied before first use. Vercel does not automatically run the Docker entrypoint migration command.
- Vercel Services are billed like Vercel Functions and can consume usage quotas even on a free plan. Monitor usage; do not enable paid services.

## References

- Vercel Services: https://vercel.com/kb/guide/vercel-services
- Vercel FastAPI: https://vercel.com/docs/frameworks/backend/fastapi
- Vercel limits: https://vercel.com/docs/limits
- Neon pricing: https://neon.com/pricing
- Qdrant Cloud pricing: https://qdrant.tech/pricing/
