"""Local embedding model; provisioning pins a snapshot before runtime."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.kernel.config import settings


def model_manifest() -> dict[str, Any]:
    manifest = json.loads((Path(settings.model_directory) / "manifest.json").read_text())
    if manifest["model_id"] != settings.embedding_model:
        raise ValueError("Provisioned embedding model does not match EMBEDDING_MODEL")
    if not manifest["revision"] or not 0 < manifest["dimension"] <= 4000:
        raise ValueError("Invalid embedding snapshot manifest")
    return manifest


def embedding_dimension() -> int:
    return int(model_manifest()["dimension"])


@lru_cache(maxsize=1)
def get_model() -> Any:
    from sentence_transformers import SentenceTransformer

    manifest = model_manifest()
    model = SentenceTransformer(
        str(Path(settings.model_directory) / "embedding"),
        local_files_only=True,
        trust_remote_code=False,
        device="cpu",
    )
    if model.get_sentence_embedding_dimension() != manifest["dimension"]:
        raise ValueError("Model dimension differs from provisioned dimension")
    return model


def embed(texts: list[str], *, query: bool = False) -> list[list[float]]:
    model = get_model()
    method = model.encode_query if query else model.encode_document
    return method(texts, normalize_embeddings=True, batch_size=4, show_progress_bar=False).tolist()
