"""Load version-controlled instruments and append survey responses."""

from pathlib import Path
from typing import Any

import yaml

from app.kernel.db import SessionLocal
from app.study.models import SurveyResponse
from app.study.schemas import SurveySubmission

INSTRUMENT_DIRECTORY = Path("config/instruments")
TRIGGERS = {"post_task", "post_session", "baseline"}


def load_instruments(trigger: str) -> list[dict[str, Any]]:
    if trigger not in TRIGGERS:
        raise ValueError("Unknown survey trigger")
    instruments = []
    for path in sorted(INSTRUMENT_DIRECTORY.glob("*.yaml")):
        instrument = yaml.safe_load(path.read_text())
        if instrument["trigger"] == trigger:
            instruments.append({"id": path.stem, **instrument})
    return instruments


async def save_response(submission: SurveySubmission) -> None:
    known = {item["id"] for item in load_instruments(submission.trigger)}
    if submission.instrument not in known:
        raise ValueError("Instrument is not active for this trigger")
    async with SessionLocal() as session, session.begin():
        session.add(
            SurveyResponse(
                session_id=submission.session_id,
                instrument=submission.instrument,
                trigger=submission.trigger,
                responses=submission.responses,
            )
        )
