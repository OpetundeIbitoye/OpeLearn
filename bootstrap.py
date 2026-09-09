#!/usr/bin/env python3
"""Generate the modular vertical-slice scaffold for the scaffolded answer engine."""
from pathlib import Path
import textwrap, sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "scaffolded-answer-engine")

# Files that get real, load-bearing content.
FILES: dict[str, str] = {}


def add(path: str, body: str) -> None:
    FILES[path] = textwrap.dedent(body).lstrip("\n")


# ---------------------------------------------------------------- root

add("README.md", '''
    # Scaffolded Answer Engine

    A retrieval + synthesis system that doubles as a controlled research instrument
    for a study on **student type x level of support**.

    ## Structure

    Organised as **vertical slices**, not horizontal layers. Each module under
    `backend/app/` owns its own schemas, persistence, logic and routes. The only
    shared code is `kernel/`, which contains no domain logic.

    | Slice | Owns |
    |---|---|
    | `corpus/` | ingestion, parsing, chunking, embedding |
    | `retrieval/` | dense + sparse search, fusion, rerank, external sources |
    | `synthesis/` | prompt assembly, generation, citation mapping, streaming |
    | `scaffolding/` | process-prompt trigger rules |
    | `conditions/` | the manipulation: arm definitions, assignment |
    | `study/` | consent, participants, event log, surveys, export |
    | `ask/` | the orchestrator that runs one turn end to end |

    `conditions/` is imported by the others and imports none of them. That is
    deliberate: the manipulation is defined in exactly one place.

    ## Quick start

    ```bash
    cp .env.example .env          # fill in keys
    make up                       # postgres + redis + api + web
    make migrate                  # create schema
    make ingest PATH=./papers     # load a corpus
    ```

    ## The freeze list

    Four values are pinned before the first participant and recorded on every turn:

    1. embedding model ID
    2. reranker model ID
    3. generation model version string
    4. `config/arms.yaml` content hash

    See `backend/app/study/events.py`. Changing any of them mid-collection is a
    protocol deviation, not a patch.

    ## Build phases

    - [ ] **0** skeleton — compose up, one end-to-end request
    - [ ] **1** corpus + local hybrid retrieval
    - [ ] **2** grounded synthesis with citations (build arm A2 first)
    - [ ] **3** external retrieval + cache
    - [ ] **4** condition engine — A1 and A3 appear here
    - [ ] **5** study layer
    - [ ] **6** baseline phase + clustering
    - [ ] **7** pilot with manipulation check
''')

add(".gitignore", '''
    __pycache__/
    *.py[cod]
    .venv/
    .env
    .pytest_cache/
    .ruff_cache/
    node_modules/
    dist/
    .DS_Store

    # research data never goes in git
    analysis/exports/*
    !analysis/exports/.gitkeep
    data/
    *.parquet
''')

add(".env.example", '''
    # --- database -------------------------------------------------------------
    POSTGRES_USER=sae
    POSTGRES_PASSWORD=change-me
    POSTGRES_DB=sae
    DATABASE_URL=postgresql+asyncpg://sae:change-me@localhost:5432/sae
    REDIS_URL=redis://localhost:6379/0

    # --- models (THE FREEZE LIST — do not change mid-study) -------------------
    EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
    RERANKER_MODEL=BAAI/bge-reranker-v2-m3
    GENERATION_PROVIDER=anthropic          # anthropic | openai | vllm
    GENERATION_MODEL=claude-sonnet-5

    ANTHROPIC_API_KEY=
    OPENAI_API_KEY=
    VLLM_BASE_URL=http://localhost:8000/v1

    # --- external sources ----------------------------------------------------
    SEARXNG_URL=http://localhost:8080
    OPENALEX_MAILTO=you@university.edu
    SEMANTIC_SCHOLAR_KEY=
    CORE_API_KEY=

    # --- study ---------------------------------------------------------------
    STUDY_PHASE=development                # development | baseline | treatment
    RANDOMIZATION_SEED=20260909
    ARMS_CONFIG=config/arms.yaml
''')

add("docker-compose.yml", '''
    services:
      db:
        image: pgvector/pgvector:pg17
        environment:
          POSTGRES_USER: ${POSTGRES_USER}
          POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
          POSTGRES_DB: ${POSTGRES_DB}
        ports: ["5432:5432"]
        volumes: [pgdata:/var/lib/postgresql/data]
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
          interval: 5s
          retries: 10

      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

      searxng:
        image: searxng/searxng:latest
        ports: ["8080:8080"]
        environment:
          SEARXNG_BASE_URL: http://localhost:8080/
        volumes: [./config/searxng:/etc/searxng:rw]

      api:
        build: ./backend
        env_file: .env
        ports: ["8000:8000"]
        volumes: [./backend:/srv, ./config:/srv/config:ro]
        depends_on:
          db: {condition: service_healthy}
          redis: {condition: service_started}
        command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

      worker:
        build: ./backend
        env_file: .env
        volumes: [./backend:/srv, ./config:/srv/config:ro]
        depends_on:
          db: {condition: service_healthy}
        command: arq app.corpus.tasks.WorkerSettings

      web:
        build: ./frontend
        ports: ["5173:5173"]
        volumes: [./frontend:/srv, /srv/node_modules]
        command: npm run dev -- --host

    volumes:
      pgdata:
''')

add("Makefile", '''
    .PHONY: up down migrate revision ingest export test fmt

    up:        ; docker compose up -d --build
    down:      ; docker compose down
    logs:      ; docker compose logs -f api worker
    migrate:   ; docker compose exec api alembic upgrade head
    revision:  ; docker compose exec api alembic revision --autogenerate -m "$(M)"
    ingest:    ; docker compose exec api python -m scripts.ingest_corpus $(PATH)
    export:    ; docker compose exec api python -m scripts.export_dataset
    test:      ; docker compose exec api pytest -q
    fmt:       ; ruff format backend && ruff check --fix backend
''')

# ---------------------------------------------------------------- config

add("config/arms.yaml", '''
    # =============================================================================
    # THE MANIPULATION. Single source of truth for all three support conditions.
    #
    # This file is hashed at startup and the hash is recorded on every turn.
    # Once collection begins it does not change. If it must, that is a documented
    # protocol deviation.
    # =============================================================================

    version: "1.0.0"

    arms:
      A1:
        label: "Low support"
        answer:
          mode: passages_only        # no synthesised answer
          socratic_prompt: true
          max_tokens: 150
        sources:
          citations: none            # bare list at the end
          show_passages: false
          annotate_quality: false
        scaffolds:
          query_refinement: false
          source_comparison: false
          end_reflection: false
        retrieval:
          rewrite_query: false
          decompose: false
          passes: 1
          top_k: 10
          rerank: false

      A2:
        label: "Moderate support"
        answer:
          mode: reasoned             # answer with reasoning made explicit
          socratic_prompt: false
          max_tokens: 700
        sources:
          citations: inline          # numbered, linked to passage
          show_passages: false
          annotate_quality: false
        scaffolds:
          query_refinement: true     # fires below confidence threshold
          source_comparison: false
          end_reflection: false
        retrieval:
          rewrite_query: true
          decompose: false
          passes: 1
          top_k: 20
          rerank: true

      A3:
        label: "High support"
        answer:
          mode: direct               # bottom line first, confident register
          socratic_prompt: false
          max_tokens: 900
        sources:
          citations: inline
          show_passages: true
          annotate_quality: true     # relevance + recency annotation
        scaffolds:
          query_refinement: true
          source_comparison: true    # fires when sources conflict
          end_reflection: true
        retrieval:
          rewrite_query: true
          decompose: true
          passes: 3
          top_k: 30
          rerank: true

    # Baseline phase: everyone sees this before assignment. Clustering features
    # are extracted from behaviour here only. See design doc, Flag 01.
    baseline_arm: A2

    thresholds:
      low_confidence_rerank_score: 0.35
      conflict_detection_min_sources: 2
''')

for name in ("a1_low", "a2_moderate", "a3_high"):
    add(f"config/prompts/{name}.jinja", f'''
        {{# Prompt template for arm {name.split("_")[0].upper()}.
           The rendered output of this file IS the independent variable.
           Change nothing here after collection begins. #}}

        {{# TODO: system framing appropriate to this arm's answer.mode #}}

        {{% for chunk in chunks %}}
        [{{{{ loop.index }}}}] {{{{ chunk.text }}}}
        {{% endfor %}}

        Question: {{{{ query }}}}
    ''')

for inst in ("cognitive_load", "perceived_support", "trust"):
    add(f"config/instruments/{inst}.yaml", f'''
        # {inst.replace("_", " ").title()} instrument.
        # Reuse validated item wording; cite the source scale here.
        source: "TODO: citation"
        trigger: post_task          # post_task | post_session | baseline
        scale: {{min: 1, max: 7, anchors: ["TODO", "TODO"]}}
        items: []
    ''')

# ---------------------------------------------------------------- backend meta

add("backend/pyproject.toml", '''
    [project]
    name = "sae-backend"
    version = "0.1.0"
    requires-python = ">=3.12"
    dependencies = [
      "fastapi",
      "uvicorn[standard]",
      "pydantic>=2",
      "pydantic-settings",
      "sqlalchemy[asyncio]>=2",
      "asyncpg",
      "alembic",
      "pgvector",
      "arq",
      "redis",
      "httpx",
      "structlog",
      "jinja2",
      "pyyaml",
      "sentence-transformers",
      "docling",
      "polars",
    ]

    [dependency-groups]
    dev = ["pytest", "pytest-asyncio", "ruff", "scikit-learn"]

    [tool.ruff]
    line-length = 100
''')

add("backend/Dockerfile", '''
    FROM python:3.12-slim
    WORKDIR /srv
    RUN pip install --no-cache-dir uv
    COPY pyproject.toml .
    RUN uv pip install --system -r pyproject.toml
    COPY . .
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
''')

add("backend/alembic.ini", '''
    [alembic]
    script_location = migrations
    prepend_sys_path = .
''')

add("backend/app/main.py", '''
    """FastAPI entrypoint. Wires slices together; contains no domain logic."""
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    from app.ask.router import router as ask_router
    from app.conditions.loader import load_arms
    from app.corpus.router import router as corpus_router
    from app.kernel.config import settings
    from app.kernel.logging import configure_logging
    from app.retrieval.router import router as retrieval_router
    from app.study.router import router as study_router


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging()
        # Fail loudly at boot if the manipulation is malformed.
        app.state.arms = load_arms(settings.arms_config)
        yield


    app = FastAPI(title="Scaffolded Answer Engine", lifespan=lifespan)

    app.include_router(ask_router)
    app.include_router(study_router)
    app.include_router(corpus_router)
    app.include_router(retrieval_router)


    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "arms_hash": app.state.arms.content_hash}
''')

# ---------------------------------------------------------------- kernel

add("backend/app/kernel/config.py", '''
    """Settings. The freeze-list values live here and are logged on every turn."""
    from pydantic_settings import BaseSettings, SettingsConfigDict


    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

        database_url: str
        redis_url: str

        # --- freeze list ---
        embedding_model: str
        reranker_model: str
        generation_provider: str
        generation_model: str

        anthropic_api_key: str = ""
        openai_api_key: str = ""
        vllm_base_url: str = ""

        searxng_url: str = ""
        openalex_mailto: str = ""
        semantic_scholar_key: str = ""
        core_api_key: str = ""

        study_phase: str = "development"
        randomization_seed: int = 0
        arms_config: str = "config/arms.yaml"


    settings = Settings()  # type: ignore[call-arg]
''')

add("backend/app/kernel/db.py", '''
    """Async SQLAlchemy session factory and declarative base."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.orm import DeclarativeBase

    from app.kernel.config import settings

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


    class Base(DeclarativeBase):
        pass


    async def get_session():
        async with SessionLocal() as session:
            yield session
''')

add("backend/app/kernel/logging.py", '''
    """Application logging. NOT the study event log — that lives in study/events.py."""
    import structlog


    def configure_logging() -> None:
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ]
        )


    log = structlog.get_logger()
''')

# ---------------------------------------------------------------- conditions

add("backend/app/conditions/schemas.py", '''
    """Typed model of config/arms.yaml.

    This slice imports nothing else from the app. Every other slice imports it.
    """
    from enum import StrEnum
    from typing import Literal

    from pydantic import BaseModel, Field


    class ArmId(StrEnum):
        A1 = "A1"
        A2 = "A2"
        A3 = "A3"


    class AnswerConfig(BaseModel):
        mode: Literal["passages_only", "reasoned", "direct"]
        socratic_prompt: bool
        max_tokens: int


    class SourcesConfig(BaseModel):
        citations: Literal["none", "inline"]
        show_passages: bool
        annotate_quality: bool


    class ScaffoldsConfig(BaseModel):
        query_refinement: bool
        source_comparison: bool
        end_reflection: bool


    class RetrievalConfig(BaseModel):
        rewrite_query: bool
        decompose: bool
        passes: int = Field(ge=1)
        top_k: int = Field(ge=1)
        rerank: bool


    class Arm(BaseModel):
        label: str
        answer: AnswerConfig
        sources: SourcesConfig
        scaffolds: ScaffoldsConfig
        retrieval: RetrievalConfig


    class Thresholds(BaseModel):
        low_confidence_rerank_score: float
        conflict_detection_min_sources: int


    class ArmsConfig(BaseModel):
        version: str
        arms: dict[ArmId, Arm]
        baseline_arm: ArmId
        thresholds: Thresholds

        content_hash: str = ""

        def get(self, arm_id: ArmId | str) -> Arm:
            return self.arms[ArmId(arm_id)]
''')

add("backend/app/conditions/loader.py", '''
    """Load and hash the arm configuration. Called once at startup."""
    import hashlib
    from pathlib import Path

    import yaml

    from app.conditions.schemas import ArmsConfig


    def load_arms(path: str | Path) -> ArmsConfig:
        raw = Path(path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()[:16]
        cfg = ArmsConfig.model_validate(yaml.safe_load(raw))
        cfg.content_hash = digest
        return cfg
''')

add("backend/app/conditions/assignment.py", '''
    """Deterministic, seeded, stratified assignment.

    Stratification is by baseline cluster (see design doc, Flag 01): participants
    are clustered on baseline-phase behaviour BEFORE they are assigned, so the
    moderator is not downstream of the manipulation.

    Deterministic on (seed, participant_id) so any assignment can be reproduced
    from the recorded seed alone.
    """
    import hashlib
    from collections import Counter
    from collections.abc import Sequence

    from app.conditions.schemas import ArmId

    ARMS: tuple[ArmId, ...] = (ArmId.A1, ArmId.A2, ArmId.A3)


    def _stable_rank(seed: int, participant_id: str) -> int:
        h = hashlib.sha256(f"{seed}:{participant_id}".encode()).hexdigest()
        return int(h, 16)


    def assign(
        participant_id: str,
        cluster: str,
        seed: int,
        already_assigned: Sequence[tuple[str, ArmId]] = (),
    ) -> ArmId:
        """Return the arm for one participant, balancing within their cluster.

        `already_assigned` is [(cluster, arm), ...] for everyone enrolled so far.
        Picks the least-filled arm within this participant's stratum; ties broken
        deterministically by a hash of (seed, participant_id).
        """
        counts = Counter(arm for c, arm in already_assigned if c == cluster)
        fewest = min(counts.get(a, 0) for a in ARMS)
        candidates = [a for a in ARMS if counts.get(a, 0) == fewest]
        return candidates[_stable_rank(seed, participant_id) % len(candidates)]
''')

add("backend/app/conditions/registry.py", '''
    """Resolve the active arm for a request. TODO: wire to participant lookup."""
''')

# ---------------------------------------------------------------- retrieval

add("backend/app/retrieval/fusion.py", '''
    """Reciprocal rank fusion.

    Deliberately hand-written and dependency-free: the weights are part of the
    retrieval-assistance manipulation and must stay visible and loggable.
    """
    from collections import defaultdict
    from collections.abc import Iterable, Sequence


    def reciprocal_rank_fusion(
        ranked_lists: Iterable[Sequence[str]],
        k: int = 60,
        weights: Sequence[float] | None = None,
    ) -> list[tuple[str, float]]:
        """Fuse ranked ID lists. Returns [(id, score), ...] best first."""
        lists = list(ranked_lists)
        w = list(weights) if weights else [1.0] * len(lists)
        scores: dict[str, float] = defaultdict(float)
        for weight, ids in zip(w, lists, strict=True):
            for rank, doc_id in enumerate(ids, start=1):
                scores[doc_id] += weight / (k + rank)
        return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
''')

add("backend/app/retrieval/sources/base.py", '''
    """External source interface. Every provider returns the same shape so the
    pipeline never branches on which source it is talking to."""
    from abc import ABC, abstractmethod

    from pydantic import BaseModel


    class ExternalHit(BaseModel):
        source: str
        title: str
        url: str
        snippet: str
        full_text: str | None = None
        published: str | None = None


    class SourceProvider(ABC):
        name: str

        @abstractmethod
        async def search(self, query: str, limit: int = 10) -> list[ExternalHit]: ...
''')

# ---------------------------------------------------------------- synthesis

add("backend/app/synthesis/providers/base.py", '''
    """The LLM adapter interface.

    One interface, several implementations. Swapping provider is a config change,
    never an architecture change — which is what keeps the 'can student queries
    leave institutional infrastructure' question from blocking the build.

    Every implementation MUST report `version_string`, which is recorded on each
    turn as part of the freeze list.
    """
    from abc import ABC, abstractmethod
    from collections.abc import AsyncIterator

    from pydantic import BaseModel


    class Message(BaseModel):
        role: str
        content: str


    class GenerationProvider(ABC):
        name: str

        @property
        @abstractmethod
        def version_string(self) -> str:
            """Exact pinned model identifier, e.g. 'claude-sonnet-5'."""

        @abstractmethod
        async def stream(
            self, messages: list[Message], max_tokens: int, temperature: float = 0.0
        ) -> AsyncIterator[str]: ...
''')

# ---------------------------------------------------------------- ask

add("backend/app/ask/pipeline.py", '''
    """One turn, end to end. The ten steps from the design document.

    Steps 2 and 6 vary by arm. Everything else is constant across conditions —
    that is what keeps the manipulation clean. Do not add branching elsewhere
    without recording it in config/arms.yaml.
    """
    from app.conditions.schemas import Arm


    async def run_turn(query: str, arm: Arm, participant_id: str, session_id: str):
        # 01  open turn, resolve participant + arm, start timer
        # 02  query transformation            <- ARM VARIES (rewrite / decompose)
        # 03  parallel retrieval: dense + sparse + web + academic
        # 04  cache every external response by query hash
        # 05  reciprocal rank fusion
        # 06  cross-encoder rerank            <- ARM VARIES (skipped in A1)
        # 07  context assembly under token budget; hash the assembled prompt
        # 08  generate + stream, resolving citations to chunk IDs
        # 09  evaluate scaffold triggers
        # 10  persist full provenance (see study/events.py)
        raise NotImplementedError("Phase 2")
''')

# ---------------------------------------------------------------- study

add("backend/app/study/events.py", '''
    """The study event log. Append-only. This is research data, not telemetry.

    Distinct from kernel/logging.py: application logs may be discarded, these
    may not. Different table, different retention, different backup policy.
    """
    from pydantic import BaseModel


    class FreezeList(BaseModel):
        """Recorded on every single turn. If any of these differ across
        participants, the study has a problem that analysis cannot fix."""

        embedding_model: str
        reranker_model: str
        generation_model: str
        arms_hash: str


    # TODO: SQLAlchemy models for
    #   participant, session, turn, retrieval_result,
    #   interaction_event, survey_response, external_cache
''')

# ---------------------------------------------------------------- tests

add("backend/tests/test_conditions.py", '''
    """The arms must actually differ in the ways the design says they do.

    If this file passes and the manipulation still failed, the problem is the
    prompt templates, not the config.
    """
    from app.conditions.loader import load_arms
    from app.conditions.schemas import ArmId


    def test_arms_load():
        cfg = load_arms("config/arms.yaml")
        assert set(cfg.arms) == {ArmId.A1, ArmId.A2, ArmId.A3}
        assert cfg.content_hash


    def test_support_is_ordinal():
        """A1 < A2 < A3 on every dimension that defines 'level of support'."""
        cfg = load_arms("config/arms.yaml")
        a1, a2, a3 = (cfg.get(a) for a in (ArmId.A1, ArmId.A2, ArmId.A3))

        # retrieval assistance
        assert not a1.retrieval.rerank and a2.retrieval.rerank and a3.retrieval.rerank
        assert a1.retrieval.passes <= a2.retrieval.passes <= a3.retrieval.passes

        # source transparency
        assert a1.sources.citations == "none"
        assert a2.sources.citations == "inline"
        assert a3.sources.show_passages and not a2.sources.show_passages

        # process scaffolds — count of enabled scaffolds must be non-decreasing
        def n(arm):
            s = arm.scaffolds
            return sum([s.query_refinement, s.source_comparison, s.end_reflection])

        assert n(a1) < n(a2) < n(a3)
''')

add("backend/tests/test_assignment.py", '''
    """Randomisation must be deterministic and balanced within stratum."""
    from collections import Counter

    from app.conditions.assignment import assign


    def test_deterministic():
        a = assign("p001", cluster="c1", seed=42)
        b = assign("p001", cluster="c1", seed=42)
        assert a == b


    def test_balanced_within_cluster():
        assigned: list[tuple[str, str]] = []
        for i in range(90):
            arm = assign(f"p{i:03d}", cluster="c1", seed=42, already_assigned=assigned)
            assigned.append(("c1", arm))
        counts = Counter(arm for _, arm in assigned)
        assert max(counts.values()) - min(counts.values()) <= 1
''')

add("backend/tests/conftest.py", '''
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
''')

# ---------------------------------------------------------------- frontend

add("frontend/package.json", '''
    {
      "name": "sae-frontend",
      "private": true,
      "type": "module",
      "scripts": {
        "dev": "vite",
        "build": "tsc -b && vite build",
        "preview": "vite preview"
      },
      "dependencies": {
        "react": "^19.0.0",
        "react-dom": "^19.0.0",
        "@tanstack/react-query": "^5.0.0",
        "zustand": "^5.0.0"
      },
      "devDependencies": {
        "@vitejs/plugin-react": "^4.3.0",
        "typescript": "^5.6.0",
        "vite": "^6.0.0",
        "tailwindcss": "^4.0.0"
      }
    }
''')

add("frontend/src/conditions/affordances.ts", '''
    // Single map from arm to what the interface renders.
    //
    // Every conditional affordance in the UI reads from here. No component
    // should ever check `arm === "A3"` directly — if it does, the manipulation
    // has leaked out of config/arms.yaml and into the component tree.

    export type ArmId = "A1" | "A2" | "A3";

    export interface Affordances {
      showSynthesisedAnswer: boolean;
      showInlineCitations: boolean;
      showRetrievedPassages: boolean;
      showQualityAnnotations: boolean;
      showSocraticPrompt: boolean;
      allowQueryRefinement: boolean;
      showSourceComparison: boolean;
      showEndReflection: boolean;
    }

    // Fetched from GET /study/session at session start — never hardcoded per build.
    export function affordancesFor(arm: ArmId, config: Affordances): Affordances {
      return config;
    }
''')

add("frontend/src/features/telemetry/useEventLog.ts", '''
    // Interaction event capture. Deliberately NOT an analytics SDK: we need exact
    // timestamps, guaranteed delivery, and our own schema.
    //
    // Batches events and flushes on interval + visibilitychange (so a closed tab
    // does not silently drop the tail of a session).

    export type EventType =
      | "citation_click"
      | "passage_expand"
      | "scroll_depth"
      | "copy"
      | "query_revision"
      | "scaffold_shown"
      | "scaffold_accepted"
      | "scaffold_dismissed";

    export interface InteractionEvent {
      type: EventType;
      target?: string;
      dwellMs?: number;
      clientTs: number;
    }

    // TODO: implement buffer + flush to POST /study/events
''')

# ---------------------------------------------------------------- stubs

STUBS: dict[str, str] = {
    "backend/app/kernel/redis.py": "Redis client and the external-result hot cache.",
    "backend/app/kernel/errors.py": "Shared exception types.",
    "backend/app/kernel/types.py": "Shared primitives (IDs, pagination).",
    "backend/app/corpus/router.py": "Corpus admin endpoints (ingest, status).",
    "backend/app/corpus/schemas.py": "Document and chunk schemas.",
    "backend/app/corpus/models.py": "documents, chunks tables (chunk.embedding: halfvec).",
    "backend/app/corpus/service.py": "Ingestion orchestration.",
    "backend/app/corpus/parsing.py": "Docling wrapper. Preserves reading order and tables.",
    "backend/app/corpus/chunking.py": "Structure-aware chunking, ~400-600 tokens, 15% overlap.",
    "backend/app/corpus/embedding.py": "Embedding model wrapper. Model ID is on the freeze list.",
    "backend/app/corpus/tasks.py": "arq worker settings and ingestion jobs.",
    "backend/app/retrieval/router.py": "Retrieval debug endpoints (dev only).",
    "backend/app/retrieval/schemas.py": "Candidate, RetrievalResult.",
    "backend/app/retrieval/models.py": "retrieval_results table — one row per candidate per turn.",
    "backend/app/retrieval/service.py": "Orchestrates dense + sparse + external, applies arm config.",
    "backend/app/retrieval/dense.py": "pgvector HNSW search over halfvec embeddings.",
    "backend/app/retrieval/sparse.py": "Postgres FTS. NOTE: ts_rank is not true BM25.",
    "backend/app/retrieval/rerank.py": "Cross-encoder rerank. Skipped in A1 by design, not by accident.",
    "backend/app/retrieval/sources/openalex.py": "OpenAlex provider. Free, no key, send mailto.",
    "backend/app/retrieval/sources/semantic_scholar.py": "Semantic Scholar provider.",
    "backend/app/retrieval/sources/searxng.py": "Self-hosted SearXNG provider.",
    "backend/app/retrieval/sources/cache.py": "Permanent external_cache writes. Enables session replay.",
    "backend/app/synthesis/router.py": "Synthesis debug endpoints (dev only).",
    "backend/app/synthesis/schemas.py": "Answer, Citation, Claim.",
    "backend/app/synthesis/service.py": "Assembles prompt, calls provider, maps citations.",
    "backend/app/synthesis/prompts.py": "Jinja template loading from config/prompts/. Hashes output.",
    "backend/app/synthesis/citations.py": "Claim -> chunk ID resolution. Chunks, not documents.",
    "backend/app/synthesis/streaming.py": "SSE framing.",
    "backend/app/synthesis/providers/anthropic.py": "Anthropic provider.",
    "backend/app/synthesis/providers/openai.py": "OpenAI provider.",
    "backend/app/synthesis/providers/vllm.py": "Self-hosted vLLM provider (OpenAI-compatible).",
    "backend/app/scaffolding/schemas.py": "ScaffoldPrompt, TriggerContext.",
    "backend/app/scaffolding/service.py": "Evaluates triggers against a completed turn.",
    "backend/app/scaffolding/triggers.py": "Rule definitions: low confidence, source conflict, session end.",
    "backend/app/ask/router.py": "POST /ask — the single student-facing endpoint. Streams.",
    "backend/app/ask/schemas.py": "AskRequest, AskChunk (stream frame types).",
    "backend/app/study/router.py": "Consent, session, events, survey endpoints.",
    "backend/app/study/schemas.py": "Participant, Session, SurveyResponse.",
    "backend/app/study/models.py": "All study tables. Append-only.",
    "backend/app/study/consent.py": "Consent capture and versioning.",
    "backend/app/study/participants.py": "Pseudonymous enrolment. Linking key stored separately.",
    "backend/app/study/sessions.py": "Session lifecycle, phase marker (baseline | treatment).",
    "backend/app/study/surveys.py": "Instrument delivery at trigger points.",
    "backend/app/study/export.py": "Polars -> Parquet. Never analyse against the live DB.",
}

PY_HEADER = '"""{}\n\nTODO: implement.\n"""\n'
for path, doc in STUBS.items():
    add(path, PY_HEADER.format(doc))

TS_STUBS = {
    "frontend/src/main.tsx": "React entrypoint.",
    "frontend/src/App.tsx": "Routes: consent -> baseline/treatment session -> debrief.",
    "frontend/src/kernel/api.ts": "Typed fetch client. Types generated from FastAPI OpenAPI.",
    "frontend/src/kernel/store.ts": "Zustand: session, arm config, event buffer.",
    "frontend/src/conditions/ArmProvider.tsx": "Provides arm affordances to the tree.",
    "frontend/src/features/consent/ConsentGate.tsx": "Blocks all other routes until consent recorded.",
    "frontend/src/features/ask/AskPanel.tsx": "The student-facing surface.",
    "frontend/src/features/ask/AnswerStream.tsx": "Renders the SSE stream.",
    "frontend/src/features/ask/CitationChip.tsx": "Inline citation. Click is a logged event.",
    "frontend/src/features/ask/SourcePanel.tsx": "Source list; passages + annotations gated by arm.",
    "frontend/src/features/ask/useAsk.ts": "Streaming hook.",
    "frontend/src/features/scaffolds/ScaffoldPrompt.tsx": "Process prompt surface.",
    "frontend/src/features/survey/SurveyModal.tsx": "Instrument delivery at trigger points.",
}
for path, doc in TS_STUBS.items():
    add(path, f"// {doc}\n// TODO: implement.\n")

SCRIPTS = {
    "scripts/ingest_corpus.py": "Ingest a folder of PDFs into the corpus.",
    "scripts/assign_participants.py": "Run clustering on baseline logs, then assign arms.",
    "scripts/export_dataset.py": "Produce a timestamped Parquet analysis dataset.",
}
for path, doc in SCRIPTS.items():
    add(path, PY_HEADER.format(doc))

add("analysis/clustering/features.py", PY_HEADER.format(
    "Extract clustering features from BASELINE-PHASE events only.\n\n"
    "Using treatment-phase behaviour here reintroduces the confound the baseline\n"
    "phase exists to remove. See design doc, Flag 01."
))
add("analysis/clustering/cluster.py", PY_HEADER.format(
    "Fit clusters and select k. Preregister the selection procedure."
))

EMPTY_DIRS = [
    "backend/migrations/versions",
    "config/searxng",
    "analysis/notebooks",
    "analysis/exports",
    "frontend/public",
    "data",
]

# ---------------------------------------------------------------- write

for rel, body in FILES.items():
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)

for d in EMPTY_DIRS:
    p = ROOT / d
    p.mkdir(parents=True, exist_ok=True)
    (p / ".gitkeep").write_text("")

# python package markers
for pkg in ROOT.rglob("app"):
    for sub in [pkg, *[d for d in pkg.rglob("*") if d.is_dir()]]:
        (sub / "__init__.py").touch()
(ROOT / "backend/tests/__init__.py").touch()

print(f"created {len(FILES)} files under {ROOT}/")
