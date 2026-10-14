# Pilot report

## Pilot record

- Date range:
- Build commit:
- Schema-freeze tag:
- Arms configuration hash:
- Embedding model:
- Reranker model:
- Generation model:
- Randomisation seed:
- Clustering run ID:
- Participants enrolled:
- Participants completing baseline, treatment, and surveys:

## Instrument flow

Record whether consent, baseline tasks, clustering and assignment, treatment sessions, event
delivery, and surveys completed as designed. List operational deviations without rewriting or
removing study records.

## Manipulation check

| Arm | N | Mean perceived guidance | SD |
| --- | ---: | ---: | ---: |
| A1 |  |  |  |
| A2 |  |  |  |
| A3 |  |  |  |

Preregistered criterion: **A1 < A2 < A3**. Record PASS or FAIL. A failure stops progression to
collection and must be reported as a pilot finding.

## Dataset completeness

- Turns missing freeze-list values:
- Turns with zero retrieval results:
- Sessions with no events and investigation outcome:
- Missing required survey responses:
- Participants appearing in more than one arm:
- Export schema validation:

Attach the complete output of `python -m scripts.validate_dataset`.

## Replay evidence

- Replayed turn ID:
- Original turn timestamp:
- Replay date:
- Recorded generation model:
- Stored prompt hash matched:
- Retrieval result count:
- External cache record count:
- Exact context reconstruction result:

Attach the output from `python -m scripts.replay_session <turn-id> --output <path>` and retain the
generated replay record with the pilot archive.

## Decision

- Ready for collection: YES / NO
- Required remediation or protocol deviations:
- Reviewer and date:
