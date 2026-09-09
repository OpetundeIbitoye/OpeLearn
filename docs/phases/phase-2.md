# Phase 2 — Grounded synthesis — arm A2 only

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
curl -N -X POST localhost:8000/ask \
  -H 'content-type: application/json' \
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
