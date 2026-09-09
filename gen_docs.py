#!/usr/bin/env python3
"""Add AGENTS.md + phase instruction files to the scaffold."""
from pathlib import Path
import textwrap, sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "scaffolded-answer-engine")
F: dict[str, str] = {}


def add(p: str, b: str) -> None:
    F[p] = textwrap.dedent(b).lstrip("\n")


# =============================================================== AGENTS.md

add("AGENTS.md", '''
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
''')

# =============================================================== phase index

add("docs/phases/README.md", '''
    # Build phases

    Feed these to your coding agent **one at a time**, in order. Each is scoped so
    that a single agent session can finish and verify it.

    | Phase | Objective | Ends when |
    |---|---|---|
    | [0](phase-0.md) | Skeleton | `make up` healthy, `/health` returns arms hash |
    | [1](phase-1.md) | Corpus + local hybrid retrieval | ingest PDFs, search returns fused ranked chunks |
    | [2](phase-2.md) | Grounded synthesis (arm A2 only) | `/ask` streams an answer with working citations |
    | [3](phase-3.md) | External retrieval + cache | web + academic sources, every response replayable |
    | [4](phase-4.md) | Condition engine | A1 and A3 exist; arms provably differ |
    | [5](phase-5.md) | Study layer | consent, event log, surveys, export; schema freezes |
    | [6](phase-6.md) | Baseline + clustering | baseline phase, clustering, stratified assignment |
    | [7](phase-7.md) | Pilot | manipulation check passes; dataset is analysable |

    ## Suggested prompt

    ```
    Read AGENTS.md, then docs/phases/phase-0.md.
    Implement exactly that phase. Do not build anything listed under Non-goals.
    When done, run the acceptance checks and paste the actual output.
    If any check fails, stop and tell me why rather than changing the check.
    ```

    Replace `phase-0` each time. Do not paste more than one phase per session —
    agents given all eight at once reliably build a shallow version of all of them.
''')

# =============================================================== phases

PHASES = [
    # ---------------------------------------------------------------- 0
    ("phase-0", "Skeleton", '''
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
    '''),

    # ---------------------------------------------------------------- 1
    ("phase-1", "Corpus and local hybrid retrieval", '''
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

    curl -s -X POST localhost:8000/retrieval/search \\
      -H 'content-type: application/json' \\
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
    '''),

    # ---------------------------------------------------------------- 2
    ("phase-2", "Grounded synthesis — arm A2 only", '''
    ## Objective

    `POST /ask` streams a synthesised answer with inline citations that resolve to
    real chunks. **Build arm A2 (moderate) only** — it is the middle case, and the
    other two are defined relative to it.

    ## Preconditions

    Phase 1 green.

    ## Deliverables

    - `synthesis/providers/anthropic.py` (or whichever provider is configured)
      implementing `GenerationProvider`. `version_string` returns the exact pinned
      model ID from settings.
    - `synthesis/prompts.py` — loads `config/prompts/a2_moderate.jinja`, renders it,
      and returns both the rendered string and its SHA-256 hash
    - `synthesis/citations.py` — parse `[n]` markers from the model output and map
      each to the chunk ID that occupied position n in the assembled context.
      A marker that cannot be resolved is an error, not a warning.
    - `synthesis/streaming.py` — SSE frames. Frame types: `token`, `citation`,
      `sources`, `done`, `error`.
    - `ask/router.py`, `ask/pipeline.py` — steps 1, 3, 5, 7, 8 wired (skip 2, 4, 6,
      9 for now; 10 writes a minimal turn row)
    - `frontend/src/features/ask/` — `AskPanel`, `AnswerStream`, `CitationChip`,
      `SourcePanel`, `useAsk`

    ## Fill in the prompt template

    `config/prompts/a2_moderate.jinja` is currently a stub. Write the real A2
    template: synthesised answer, reasoning made explicit, hedges preserved where
    sources disagree, inline `[n]` citations. Match `arms.yaml` A2 exactly —
    `answer.mode: reasoned`, `max_tokens: 700`.

    ## Acceptance checks

    ```bash
    curl -N -X POST localhost:8000/ask \\
      -H 'content-type: application/json' \\
      -d '{"query":"<question answerable from your corpus>"}'
    ```

    - Tokens stream (not one blob at the end)
    - Every `[n]` in the answer appears in the `sources` frame
    - Every cited chunk ID exists in the `chunks` table
    - The `turns` row records `prompt_hash`, `generation_model`, `latency_ms`,
      input and output token counts

    In the browser at `localhost:5173`: ask a question, watch it stream, click a
    citation, see the passage.

    Add `backend/tests/test_citations.py`: an answer citing `[3]` maps to the chunk
    that was third in the assembled context; an unresolvable marker raises.

    ## Non-goals

    No A1 or A3. No scaffolds. No reranking. No external sources. No consent flow,
    no participants, no event log beyond the minimal turn row.

    ## Done when

    A question against your corpus produces a streamed, cited answer whose
    citations open the correct passages.
    '''),

    # ---------------------------------------------------------------- 3
    ("phase-3", "External retrieval and cache", '''
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
    '''),

    # ---------------------------------------------------------------- 4
    ("phase-4", "Condition engine — A1 and A3 appear", '''
    ## Objective

    Make the three arms real, provably distinct, and driven entirely by
    `config/arms.yaml`.

    ## Preconditions

    Phase 3 green.

    ## Deliverables

    - `config/prompts/a1_low.jinja` — **no synthesised answer**. Return ranked
      passages verbatim plus one Socratic prompt. `max_tokens: 150`.
    - `config/prompts/a3_high.jinja` — direct answer, bottom line first, confident
      register, citations plus passage plus relevance/recency annotation.
    - `conditions/registry.py` — resolve the active arm for a request from the
      participant record (fall back to `baseline_arm` when unassigned)
    - `retrieval/rerank.py` — cross-encoder rerank, invoked only when
      `arm.retrieval.rerank` is true
    - `retrieval/service.py` — honour `rewrite_query`, `decompose`, `passes`,
      `top_k` from the arm config. Store **every** query variant.
    - `synthesis/service.py` — select template by `arm.answer.mode`; honour
      `max_tokens`
    - `scaffolding/triggers.py` — three rules, each gated by the arm's
      `scaffolds` config:
      - `query_refinement` when top rerank score < `thresholds.low_confidence_rerank_score`
      - `source_comparison` when >= `conflict_detection_min_sources` sources disagree
      - `end_reflection` at session end
    - `frontend/src/conditions/ArmProvider.tsx` — fetch affordances once at session
      start, provide to the tree
    - Wire `affordances.ts` into every conditional surface

    ## Acceptance checks

    ```bash
    make test    # test_conditions.py must still pass
    ```

    Add `backend/tests/test_arm_isolation.py` — **the guard test**:

    ```python
    import re, pathlib
    ALLOWED = {"app/conditions/", "tests/"}
    PATTERN = re.compile(r"[\\"']A[123][\\"']")

    def test_no_arm_literals_outside_conditions():
        offenders = []
        for f in pathlib.Path("app").rglob("*.py"):
            if any(a in str(f) for a in ALLOWED):
                continue
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if PATTERN.search(line) and not line.strip().startswith("#"):
                    offenders.append(f"{f}:{i}: {line.strip()}")
        assert not offenders, "arm literals outside conditions/:\\n" + "\\n".join(offenders)
    ```

    Add `backend/tests/test_prompt_goldens.py`: render all three templates against a
    fixed set of chunks, snapshot them, and assert they differ in exactly the ways
    `arms.yaml` says — A1 has no answer instruction, A2 has no passage display,
    A3 has annotation instructions.

    Manual: run the same query three times with the arm forced to A1, A2, A3.
    Confirm three visibly different experiences and that A1 issues no rerank call
    (check the logs).

    ## Non-goals

    No consent, participants, or event log yet. Arm is forced via a dev-only query
    parameter for now.

    ## Done when

    The guard test passes, the goldens differ correctly, and all three arms render.
    '''),

    # ---------------------------------------------------------------- 5
    ("phase-5", "Study layer — the instrument", '''
    ## Objective

    Turn the system into a research instrument. **The schema freezes at the end of
    this phase.**

    ## Preconditions

    Phase 4 green.

    ## Deliverables

    - `study/models.py` — all tables from the design doc: `participants`,
      `sessions`, `turns`, `retrieval_results`, `interaction_events`,
      `survey_responses`. Append-only: no `updated_at`, no soft deletes.
    - `study/consent.py` — versioned consent text; timestamp and version recorded.
      **Consent gates every other route.**
    - `study/participants.py` — pseudonymous IDs. The mapping from participant ID
      to any identifying information lives in a **separate table with separate
      access**, or outside the system entirely.
    - `study/sessions.py` — lifecycle, plus `phase` marker (`baseline` | `treatment`)
    - `study/events.py` — `POST /study/events` accepts batches; writes the
      `FreezeList` onto every turn
    - `study/surveys.py` — load instruments from `config/instruments/`, deliver at
      trigger points (`post_task`, `post_session`, `baseline`)
    - `study/export.py` — Polars to Parquet, one file per table, into
      `analysis/exports/<ISO timestamp>/`
    - Frontend: `ConsentGate`, `SurveyModal`, and a real `useEventLog` that batches
      and flushes on interval **and** on `visibilitychange`

    ## Fill in the instruments

    `config/instruments/*.yaml` are stubs. Populate with real item wording and cite
    the source scale in the `source` field. Do not invent items.

    ## Acceptance checks

    ```bash
    # consent gates everything
    curl -s -X POST localhost:8000/ask -d '{"query":"x"}' -H 'content-type: application/json'
    # -> 403 until consent recorded

    make test
    make export
    ls analysis/exports/*/
    python -c "import polars as pl; print(pl.read_parquet('analysis/exports/*/turns.parquet').columns)"
    ```

    Add `backend/tests/test_provenance.py` — **every turn row has all four freeze
    list values populated and non-empty.** This is the single most important test
    in the repo.

    Add `backend/tests/test_append_only.py`: attempting to update or delete a study
    event row raises.

    Manual: complete a session, close the tab mid-session, confirm the tail of
    events still arrives.

    ## Non-goals

    No clustering, no baseline phase logic, no assignment yet — arm still forced.

    ## Done when

    A full consented session writes complete provenance and exports cleanly.
    **Tag the commit `schema-freeze`.**
    '''),

    # ---------------------------------------------------------------- 6
    ("phase-6", "Baseline phase and clustering", '''
    ## Objective

    Implement the fix for the endogenous-moderator problem: cluster on
    **baseline-phase behaviour only**, then assign arms stratified by cluster.

    ## Background — read this before coding

    Student type is derived by clustering interaction behaviour. If that behaviour
    were collected while participants were already in different support arms, the
    clusters would partly reflect the treatment rather than the learner, and the
    type-by-support interaction would be uninterpretable.

    The fix: every participant first completes the **baseline phase** on an
    identical build (`baseline_arm` from `arms.yaml`, currently A2). Clustering
    features come from that phase and no other. Assignment happens after.

    ## Preconditions

    Phase 5 green and tagged `schema-freeze`.

    ## Deliverables

    - Session routing: a participant with no `baseline_cluster` is served
      `baseline_arm` and their session is marked `phase='baseline'`. After N
      baseline tasks (configurable, default 3) the participant is eligible for
      assignment.
    - `analysis/clustering/features.py` — extract per-participant features from
      `interaction_events` **filtered to `phase='baseline'`**. Suggested features:
      query length and revision count, citation click rate, passage expansion rate,
      mean dwell on sources, time to first query, session duration.
    - `analysis/clustering/cluster.py` — standardise, fit, select k by a
      **preregistered** procedure (silhouette or gap statistic — write which one in
      a docstring), emit cluster labels and a fit report
    - `scripts/assign_participants.py` — run clustering, write `baseline_cluster`,
      then call `conditions/assignment.assign()` for each unassigned participant
      using `RANDOMIZATION_SEED`
    - Record the seed and the clustering run ID on every participant row

    ## Acceptance checks

    ```bash
    python -m scripts.assign_participants --dry-run
    # prints cluster sizes, then the arm distribution within each cluster
    ```

    Add `backend/tests/test_baseline_isolation.py` — **the second guard test**:

    ```python
    def test_features_query_filters_baseline_only():
        """Feature extraction must never read treatment-phase events."""
        sql = inspect.getsource(features.build_feature_frame)
        assert "baseline" in sql, "feature extraction must filter phase='baseline'"
        assert "treatment" not in sql
    ```

    Better still, make `build_feature_frame` take a phase argument that defaults to
    `"baseline"` and assert it raises on `"treatment"`.

    Also verify:
    - assignment is balanced within every cluster (max - min <= 1)
    - re-running with the same seed produces identical assignments
    - a participant already assigned is never reassigned

    ## Non-goals

    No analysis of outcomes. No modelling. This phase produces cluster labels and
    arm assignments, nothing more.

    ## Done when

    Dry run shows balanced arms within each cluster, and rerunning is idempotent.
    '''),

    # ---------------------------------------------------------------- 7
    ("phase-7", "Pilot", '''
    ## Objective

    Prove the instrument works before it collects real data. **A failed
    manipulation check here is a finding, not a bug to hide.**

    ## Preconditions

    Phase 6 green.

    ## Deliverables

    - Manipulation check instrument: participants rate how much guidance they
      received. Add to `config/instruments/perceived_support.yaml` and deliver at
      `post_session`.
    - `scripts/replay_session.py` — reconstruct any past turn from
      `external_cache` + stored prompt + recorded model version. Prove the archive
      is sufficient.
    - `scripts/validate_dataset.py` — completeness report:
      - turns with any missing freeze-list value (must be 0)
      - turns with zero retrieval_results (must be 0)
      - sessions with no events (investigate)
      - participants with incomplete surveys
      - arm distribution overall and per cluster
    - A short `docs/pilot-report.md` template

    ## Run the pilot

    12-20 participants, ideally people who are not you. Full flow: consent,
    baseline phase, assignment, treatment session, surveys.

    ## Acceptance checks

    ```bash
    python -m scripts.validate_dataset
    ```

    All of these must hold:

    - **Manipulation check: mean perceived guidance A1 < A2 < A3.** If it does
      not, the manipulation failed. Stop, report it, and revisit the prompt
      templates and affordances — do not proceed to collection.
    - Zero turns missing any freeze-list value
    - Zero turns with no retrieval results
    - `replay_session.py` reproduces a month-old turn's context exactly
    - Export loads in Polars and every expected column is present and typed
    - No participant appears in more than one arm

    ## Non-goals

    No statistical analysis of outcomes — the pilot is not powered for it and
    looking will only tempt you.

    ## Done when

    The manipulation check passes, the dataset validates clean, and you can replay
    an arbitrary turn. The instrument is ready.
    '''),
]

for slug, title, body in PHASES:
    n = slug.split("-")[1]
    add(f"docs/phases/{slug}.md", f"# Phase {n} — {title}\n\n" + textwrap.dedent(body).strip() + "\n")

# =============================================================== write

for rel, body in F.items():
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)

print(f"wrote {len(F)} instruction files under {ROOT}/")
for k in sorted(F):
    print("  ", k)
