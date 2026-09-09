# Phase 5 — Study layer — the instrument

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
