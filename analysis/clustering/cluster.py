"""Standardise baseline features and choose k by maximum silhouette score.

Preregistered procedure: evaluate k=2..min(6, n-1) with K-means using a fixed
seed and 20 initialisations. Select the highest silhouette score, breaking ties
in favour of the smaller k. Cohorts with fewer than three usable participants
are placed in one cluster because silhouette is undefined for them.
"""

from dataclasses import dataclass
from typing import Any

import polars as pl
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from analysis.clustering.features import FEATURE_COLUMNS


@dataclass(frozen=True)
class ClusterResult:
    labels: dict[str, str]
    report: dict[str, Any]


def fit_clusters(frame: pl.DataFrame, seed: int, max_k: int = 6) -> ClusterResult:
    """Fit deterministic clusters and return participant labels plus fit diagnostics."""

    participant_ids = frame.get_column("participant_id").to_list()
    sample_count = len(participant_ids)
    if sample_count < 3:
        return ClusterResult(
            labels={participant_id: "cluster_0" for participant_id in participant_ids},
            report={
                "selected_k": 1,
                "sample_count": sample_count,
                "silhouette_scores": {},
            },
        )

    matrix = frame.select(FEATURE_COLUMNS).to_numpy()
    scaled = StandardScaler().fit_transform(matrix)
    scores: dict[int, float] = {}
    models: dict[int, KMeans] = {}
    for k in range(2, min(max_k, sample_count - 1) + 1):
        model = KMeans(n_clusters=k, random_state=seed, n_init=20)
        labels = model.fit_predict(scaled)
        if len(set(labels)) < 2:
            continue
        scores[k] = float(silhouette_score(scaled, labels))
        models[k] = model

    if not scores:
        return ClusterResult(
            labels={participant_id: "cluster_0" for participant_id in participant_ids},
            report={
                "selected_k": 1,
                "sample_count": sample_count,
                "silhouette_scores": {},
            },
        )
    selected_k = max(sorted(scores), key=scores.get)  # type: ignore[arg-type]
    selected_labels = models[selected_k].labels_
    return ClusterResult(
        labels={
            participant_id: f"cluster_{int(label)}"
            for participant_id, label in zip(
                participant_ids, selected_labels, strict=True
            )
        },
        report={
            "selected_k": selected_k,
            "sample_count": sample_count,
            "silhouette_scores": scores,
        },
    )
