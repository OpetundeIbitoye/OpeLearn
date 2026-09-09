# Phase 4 — Condition engine — A1 and A3 appear

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
PATTERN = re.compile(r"[\"']A[123][\"']")

def test_no_arm_literals_outside_conditions():
    offenders = []
    for f in pathlib.Path("app").rglob("*.py"):
        if any(a in str(f) for a in ALLOWED):
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if PATTERN.search(line) and not line.strip().startswith("#"):
                offenders.append(f"{f}:{i}: {line.strip()}")
    assert not offenders, "arm literals outside conditions/:\n" + "\n".join(offenders)
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
