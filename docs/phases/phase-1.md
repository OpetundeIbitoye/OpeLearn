# Phase 1 — Corpus and local hybrid retrieval

## Objective

Ingest a folder of PDFs and retrieve from them with dense + sparse search
fused into one ranked list.

## Preconditions

Phase 0 green.

## Deliverables

- `corpus/models.py` — `documents`, `chunks`. `chunks.embedding` is
  `halfvec(N)` where N matches `EMBEDDING_MODEL`. Store `section_heading` and
  `page_number` on every chunk.
- `corpus/parsing.py` — Docling wrapper preserving reading order and tables
- `corpus/chunking.py` — split on section boundaries, target 400-600 tokens,
  ~15% overlap. Never split mid-table.
- `corpus/embedding.py` — model wrapper; the model ID comes from settings and
  is never hardcoded
- `corpus/tasks.py` — arq job for ingestion; `scripts/ingest_corpus.py` enqueues
- `retrieval/dense.py` — pgvector HNSW cosine search
- `retrieval/sparse.py` — Postgres FTS with a GIN index on a `tsvector` column.
  Add a comment noting `ts_rank` is not true BM25.
- `retrieval/service.py` — runs both, fuses with the existing
  `retrieval/fusion.py`, returns candidates with **per-retriever ranks and
  scores retained**
- `POST /retrieval/search` (dev-only) returning the full candidate list
- Migration for all of the above, including both indexes

## Acceptance checks

```bash
mkdir -p sample_papers   # put 5-10 open-access PDFs here
make ingest PATH=./sample_papers
docker compose exec db psql -U sae -d sae -c "SELECT count(*) FROM documents; SELECT count(*) FROM chunks;"

curl -s -X POST localhost:8000/retrieval/search \
  -H 'content-type: application/json' \
  -d '{"query":"<a phrase you know is in one paper>","top_k":10}' | jq
```

Every returned candidate must carry: `chunk_id`, `dense_score`, `sparse_score`,
`fused_score`, `dense_rank`, `sparse_rank`, `section_heading`, `page_number`.

Add `backend/tests/test_retrieval.py`:
- chunking never produces a chunk over the token ceiling
- chunking never splits a table across chunks
- fusion is order-independent w.r.t. input list order
- a known query returns its known chunk in the top 5

## Non-goals

No reranking. No web or academic sources. No LLM. No `/ask` endpoint.

## Done when

`make test` green and a known phrase reliably retrieves its source chunk.
