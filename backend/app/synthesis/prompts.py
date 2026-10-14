"""The single prompt assembly path: render and hash the exact sent string."""

import hashlib
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.conditions.schemas import Arm
from app.retrieval.schemas import Candidate

PROMPT_PATH = Path("config/prompts/a2_moderate.jinja")
PROMPT_DIRECTORY = Path("config/prompts")


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(PROMPT_DIRECTORY), undefined=StrictUndefined, autoescape=False
    )


def render_a2_prompt(query: str, chunks: list[Candidate]) -> tuple[str, str]:
    template = Environment(undefined=StrictUndefined, autoescape=False).from_string(
        PROMPT_PATH.read_text()
    )
    rendered = template.render(query=query, chunks=chunks).strip()
    return rendered, hashlib.sha256(rendered.encode()).hexdigest()


TEMPLATES = {
    "passages_only": "a1_low.jinja",
    "reasoned": "a2_moderate.jinja",
    "direct": "a3_high.jinja",
}


def render_prompt(query: str, chunks: list[Candidate], arm: Arm) -> tuple[str, str]:
    template = _environment().get_template(TEMPLATES[arm.answer.mode])
    rendered = template.render(query=query, chunks=chunks).strip() + "\n"
    return rendered, hashlib.sha256(rendered.encode()).hexdigest()
