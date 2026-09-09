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
