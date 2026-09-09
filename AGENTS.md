# AGENTS.md

Instructions for any coding agent working in this repository (Codex, Cursor,
Claude Code). **Read this before every task.** These rules hold in all phases.

---

## What this project is

A retrieval + synthesis system ("answer engine") that is simultaneously a
**controlled research instrument** for a PhD study on student type x level of
support. It is not a product. Where product instincts and research instincts
conflict, research wins.

The practical consequence: **provenance and reproducibility outrank features,
performance, and elegance.** A slightly worse system whose every output can be
explained and replayed is correct. A better system that cannot be is useless.

---

## The seven rules

### 1. The manipulation lives in `config/arms.yaml`. Nowhere else.

Three support conditions (A1 low, A2 moderate, A3 high) differ across four
dimensions: answer directiveness, source transparency, process scaffolds,
retrieval assistance. All of it is declared in `config/arms.yaml` and typed in
`backend/app/conditions/schemas.py`.

**Never write `if arm == "A3"` in a service, router, or component.** Read the
arm's config object and branch on the *property*:

```python
# WRONG — manipulation has leaked into code
if arm_id == "A1":
    candidates = candidates[:10]

# RIGHT
candidates = candidates[: arm.retrieval.top_k]
if arm.retrieval.rerank:
    candidates = await rerank(query, candidates)
```

There is a test that greps for this. Do not defeat it.

### 2. `conditions/` imports nothing from other slices.

Every slice imports `conditions/`; `conditions/` imports only `kernel/`. This
keeps the manipulation acyclic and independently testable. If you find yourself
wanting `conditions/` to import `retrieval/`, the design is wrong — stop and
say so rather than adding the import.

### 3. The freeze list is recorded on every turn.

Four values, defined in `backend/app/study/events.py`:

1. embedding model ID
2. reranker model ID
3. generation model version string
4. `config/arms.yaml` content hash

Every `turn` row carries all four. If they differ across participants, the
study is compromised in a way analysis cannot repair. Never make any of them
implicit, defaulted, or inferred at read time.

### 4. Study data is not telemetry.

| | Application logs | Study event log |
|---|---|---|
| Where | `kernel/logging.py` | `study/events.py` |
| Table | none (stdout) | Postgres, append-only |
| May be dropped? | yes | **never** |
| Sampling | fine | **forbidden** |

Never add an analytics SDK, never sample study events, never `UPDATE` or
`DELETE` a study event row. Corrections are new rows.

### 5. Banned dependencies

- **LangChain / LlamaIndex / Haystack** — the exact prompt string is the
  independent variable; it must be assembled in code you can read.
- **Any hosted vector DB** — retrieval results must be joinable against the
  event log in one database.
- **Analytics/telemetry SDKs** (Segment, PostHog, GA) — see rule 4.
- **Any package that phones home or auto-updates a model.**

If a task seems to need one of these, say so and propose an alternative rather
than adding it.

### 6. Every phase ends green.

A phase is done when, from a clean checkout:

```bash
make up && make migrate && make test
```

all succeed, and the phase's own acceptance checks in `docs/phases/` pass. Do
not begin phase N+1 with phase N red. Do not delete or weaken a failing test to
make it pass — fix the code or report the problem.

### 7. Ask before these.

Stop and ask the human rather than deciding alone:

- Any edit to `config/arms.yaml` after Phase 4 is complete
- Any migration after Phase 5 is complete (the schema freezes there)
- Changing an embedding, reranker, or generation model ID
- Anything that would send participant text to a service not already in `.env.example`
- Adding a dependency not already in `pyproject.toml` / `package.json`

---

## Architecture: vertical slices

Organised by capability, not by technical layer. Each slice owns its own
schemas, models, service logic, and routes.

```
backend/app/
  kernel/       config, db, redis, logging      — no domain logic
  conditions/   arms config, assignment          — imports nothing
  corpus/       parsing, chunking, embedding
  retrieval/    dense, sparse, fusion, rerank, sources/
  synthesis/    prompts, citations, streaming, providers/
  scaffolding/  trigger rules
  study/        consent, participants, events, surveys, export
  ask/          pipeline.py — orchestrates one turn
```

Do not create `models/`, `services/`, or `schemas/` top-level folders. Do not
move code out of its slice to "share" it — if two slices need it, it belongs in
`kernel/` and must contain no domain logic.

---

## The turn pipeline

`backend/app/ask/pipeline.py` runs ten steps. Steps 2 and 6 vary by arm.
Everything else is constant across conditions — that is what keeps the
manipulation clean. **Do not add arm-dependent behaviour at any other step**
without adding it to `config/arms.yaml` first and updating the design doc.

```
01 open turn, resolve participant + arm, start timer
02 query transformation          <- ARM VARIES
03 parallel retrieval (dense, sparse, web, academic)
04 cache every external response by query hash
05 reciprocal rank fusion
06 cross-encoder rerank          <- ARM VARIES
07 context assembly; hash the assembled prompt
08 generate + stream with citations resolved to chunk IDs
09 evaluate scaffold triggers
10 persist full provenance
```

---

## Conventions

- Python 3.12, `ruff format` + `ruff check`, line length 100, full type hints.
- Async everywhere in the request path. Blocking model calls go in a thread
  pool or the arq worker, never inline in a route.
- Pydantic v2 for every boundary (HTTP, config files, provider responses).
- SQLAlchemy 2.0 async. Every schema change is an Alembic migration — never
  `create_all()`.
- Citations resolve to **chunk IDs**, never document IDs. A student must be
  able to see the exact passage.
- Frontend: no component reads the arm ID. Components read booleans from
  `frontend/src/conditions/affordances.ts`.
- Commit per phase step, message prefixed `phase-N:`.

---

## How to work a phase

1. Read `docs/phases/phase-N.md`.
2. Read this file's rules again — especially 1, 3, and 6.
3. Implement only what that phase lists. **Non-goals are binding**: building
   ahead creates untested surface that later phases assume works.
4. Run the phase's acceptance checks. Paste the real output.
5. If a check cannot pass, stop and explain why. Do not weaken the check.
