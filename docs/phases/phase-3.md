# Phase 3 — External retrieval and cache

## Objective

Add web and academic sources to the fan-out, and make every external response
permanently replayable.

## Preconditions

Phase 2 green.

## Deliverables

- `retrieval/sources/openalex.py` — send `mailto` from settings; map to
  `ExternalHit`
- `retrieval/sources/semantic_scholar.py`
- `retrieval/sources/searxng.py` — hits the local SearXNG container, JSON format
- `retrieval/sources/cache.py` — **two-tier**: Redis for the hot path, Postgres
  `external_cache` as the permanent record. Key on
  `sha256(provider + normalised_query)`. Store the raw payload and `fetched_at`.
- `retrieval/service.py` — fan out to corpus + all external providers
  concurrently with `asyncio.gather`; a provider that fails or times out is
  logged and skipped, never fatal
- Per-provider timeout from settings, default 5s
- Migration for `external_cache`

## Acceptance checks

```bash
# first call populates cache
time curl -s -X POST localhost:8000/retrieval/search -d '{"query":"transformer attention"}' -H 'content-type: application/json' > /tmp/a.json
# second call is served from cache and is byte-identical
time curl -s -X POST localhost:8000/retrieval/search -d '{"query":"transformer attention"}' -H 'content-type: application/json' > /tmp/b.json
diff /tmp/a.json /tmp/b.json && echo "REPLAY OK"

docker compose exec db psql -U sae -d sae -c "SELECT provider, count(*), min(fetched_at) FROM external_cache GROUP BY provider;"
```

Kill the SearXNG container and confirm `/ask` still answers from corpus +
academic sources rather than erroring.

Add `backend/tests/test_cache.py`: identical queries hit cache; a provider
raising an exception does not fail the request.

## Non-goals

No arm-dependent retrieval behaviour yet — every request still behaves like A2.

## Done when

Replay produces identical results and one dead provider cannot break a session.
