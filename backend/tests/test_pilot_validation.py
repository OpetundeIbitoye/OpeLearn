"""Pilot validation rules must remain explicit and strict."""

import polars as pl
from scripts.validate_dataset import manipulation_check

from app.study.export import TABLE_SCHEMAS, typed_frame


def test_manipulation_check_requires_strict_order_and_every_arm() -> None:
    assert manipulation_check({"A1": 2.0, "A2": 4.0, "A3": 6.0})
    assert not manipulation_check({"A1": 2.0, "A2": 2.0, "A3": 6.0})
    assert not manipulation_check({"A1": 2.0, "A2": 4.0})


def test_empty_export_frames_keep_declared_types() -> None:
    for table, schema in TABLE_SCHEMAS.items():
        frame = typed_frame(table, [])
        assert frame.schema == schema
        assert all(data_type != pl.Null for data_type in frame.schema.values())
