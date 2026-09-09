# Phase 0 — Skeleton

## Objective

Every service starts, talks to its neighbours, and the manipulation config
loads and validates at boot. No domain logic yet.

## Preconditions

Fresh checkout. `.env` created from `.env.example`.

## Deliverables

- `backend/app/kernel/config.py` — settings load from `.env`, fail loudly on
  missing required values
- `backend/app/kernel/db.py` — async engine + session factory, `Base`
- `backend/app/kernel/redis.py` — async Redis client
- `backend/app/main.py` — lifespan loads and hashes `config/arms.yaml`;
  `GET /health` returns `{"status": "ok", "arms_hash": "<hash>"}`
- First Alembic migration: enable the `vector` extension, nothing else
- `frontend/src/main.tsx`, `App.tsx` — renders a page that fetches `/health`
  and displays the arms hash
- Working `backend/Dockerfile` and `frontend/Dockerfile`

## Acceptance checks

```bash
make up
make migrate
curl -s localhost:8000/health           # {"status":"ok","arms_hash":"f1e49fa9279fe83b"}
curl -s localhost:5173 | head -5        # serves
make test                               # test_conditions + test_assignment green
docker compose exec db psql -U sae -d sae -c "SELECT extname FROM pg_extension WHERE extname='vector';"
```

Then break it on purpose and confirm it fails loudly:

```bash
# temporarily set arms.yaml `passes: 0` for A1 -> API must refuse to start
```

## Non-goals

No retrieval. No embeddings. No LLM calls. No auth. No study tables. Do not
create tables for documents, chunks, or events yet.

## Done when

All checks above pass and a malformed `arms.yaml` prevents startup.
