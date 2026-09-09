# Phase 6 — Baseline phase and clustering

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
