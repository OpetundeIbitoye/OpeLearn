# Phase 7 — Pilot

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
