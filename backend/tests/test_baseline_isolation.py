"""Baseline clustering must remain isolated from treatment behaviour."""

import inspect

import polars as pl
from analysis.clustering import features
from analysis.clustering.cluster import fit_clusters


def test_features_query_filters_baseline_only() -> None:
    """Feature extraction must never read treatment-phase events."""

    source = inspect.getsource(features.build_feature_frame)
    assert "baseline" in source, "feature extraction must filter phase='baseline'"
    assert "treatment" not in source


def test_clustering_is_reproducible() -> None:
    frame = pl.DataFrame(
        {
            "participant_id": [f"p{index}" for index in range(6)],
            "mean_query_length": [10.0, 11.0, 12.0, 80.0, 81.0, 82.0],
            "query_revision_count": [0.0, 0.0, 1.0, 5.0, 5.0, 6.0],
            "citation_click_rate": [0.0, 0.1, 0.0, 0.8, 0.9, 1.0],
            "passage_expansion_rate": [0.0, 0.0, 0.1, 0.7, 0.8, 0.9],
            "mean_source_dwell_ms": [0.0, 10.0, 20.0, 800.0, 900.0, 1000.0],
            "time_to_first_query_seconds": [2.0, 3.0, 4.0, 20.0, 21.0, 22.0],
            "session_duration_seconds": [60.0, 65.0, 70.0, 500.0, 510.0, 520.0],
        }
    )
    assert fit_clusters(frame, seed=42).labels == fit_clusters(frame, seed=42).labels
