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
