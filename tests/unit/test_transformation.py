import pandas as pd
import pytest

from f1.core.schemas import SCHEMAS
from f1.transformation.clean import parse_gap
from f1.transformation.entities import transform
from f1.validation.checks import validate
from tests.conftest import load_fixture


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, (None, None)),
        (0, (0.0, None)),
        (12.5, (12.5, None)),
        ("3.2", (3.2, None)),
        ("+1 LAP", (None, 1)),
        ("+2 LAPS", (None, 2)),
        ("abc", (None, None)),
        ([1.0, 2.0], (None, None)),
    ],
)
def test_parse_gap(value: object, expected: tuple) -> None:
    assert parse_gap(value) == expected


@pytest.mark.parametrize("entity", sorted(SCHEMAS))
def test_fixtures_transform_and_validate(entity: str) -> None:
    df, stats = transform(entity, load_fixture(f"{entity}.json"))
    validate(df, SCHEMAS[entity])
    assert list(df.columns) == list(SCHEMAS[entity].columns)
    assert stats.rows_out == len(df)


@pytest.mark.parametrize("entity", sorted(SCHEMAS))
def test_empty_input_yields_valid_empty_frame(entity: str) -> None:
    df, stats = transform(entity, [])
    validate(df, SCHEMAS[entity])
    assert df.empty
    assert stats.rows_in == 0


def test_laps_duplicates_nulls_and_extra_columns() -> None:
    df, stats = transform("laps", load_fixture("laps.json"))
    assert stats.rows_in == 4
    assert stats.duplicates_dropped == 1
    assert stats.rows_rejected == 0
    assert "segments_sector_1" not in df.columns
    kept = df[(df.driver_number == 1) & (df.lap_number == 2)]
    assert kept.lap_duration.iloc[0] == 95.7  # mantém a última ocorrência
    first = df[(df.driver_number == 1) & (df.lap_number == 1)].iloc[0]
    assert pd.isna(first.lap_duration)
    assert str(df.i1_speed.dtype) == "Int64"
    assert str(df.date_start.dtype).endswith(", UTC]")


def test_session_result_gap_normalization() -> None:
    df, _ = transform("session_result", load_fixture("session_result.json"))
    leader = df[df.driver_number == 1].iloc[0]
    lapped = df[df.driver_number == 44].iloc[0]
    assert leader.gap_to_leader_s == 0 and pd.isna(leader.laps_down)
    assert pd.isna(lapped.gap_to_leader_s) and lapped.laps_down == 1


def test_pit_ignores_deprecated_and_keeps_missing_stop_duration() -> None:
    df, _ = transform("pit", load_fixture("pit.json"))
    assert "pit_duration" not in df.columns
    assert df.stop_duration.isna().sum() == 1


def test_null_keys_are_rejected_and_unexpected_types_coerced() -> None:
    records = [
        {"session_key": 1, "driver_number": None, "lap_number": 1},
        {"session_key": 1, "driver_number": 5, "lap_number": 1, "lap_duration": "x"},
        {"session_key": 1, "driver_number": 5, "lap_number": "2.5"},
        {
            "session_key": 1,
            "driver_number": 5,
            "lap_number": 3,
            "is_pit_out_lap": "yes",
        },
    ]
    df, stats = transform("laps", records)
    validate(df, SCHEMAS["laps"])
    assert stats.rows_rejected == 2  # driver nulo e lap_number fracionário
    assert stats.values_coerced >= 2
    assert len(df) == 2
    assert df.is_pit_out_lap.tolist()[1] is True or bool(df.is_pit_out_lap.iloc[1])
    assert pd.isna(df.lap_duration.iloc[0])


def test_unknown_entity_raises() -> None:
    with pytest.raises(KeyError):
        transform("car_data", [])
