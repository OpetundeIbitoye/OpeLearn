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
