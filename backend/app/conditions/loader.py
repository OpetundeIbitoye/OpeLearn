"""Load and hash the arm configuration. Called once at startup."""
import hashlib
from pathlib import Path

import yaml

from app.conditions.schemas import ArmsConfig


def load_arms(path: str | Path) -> ArmsConfig:
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    cfg = ArmsConfig.model_validate(yaml.safe_load(raw))
    cfg.content_hash = digest
    return cfg
