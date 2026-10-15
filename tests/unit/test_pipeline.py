import logging
from pathlib import Path

import pandas as pd
import pytest

from f1.core.exceptions import PermanentApiError, SchemaValidationError
from f1.core.interfaces import Record
from f1.core.schemas import SCHEMAS
from f1.ingestion.extractors import Extractor
from f1.integrations.parquet_sink import ParquetSink
from f1.pipelines.cli import main
from f1.pipelines.race_pipeline import run_session_key, run_year
from tests.conftest import FakeClient

SESSION_PART = Path("session_key=9000") / "part.parquet"


def snapshot(base: Path) -> dict[str, pd.DataFrame]:
    return {
        str(p.relative_to(base)): pd.read_parquet(p)
        for p in sorted(base.rglob("*.parquet"))
    }


def make_extractor(client: FakeClient) -> Extractor:
    return Extractor(client, sleep=lambda _: None)


def test_sink_write_is_atomic_and_overwrites(tmp_path: Path) -> None:
    sink = ParquetSink(tmp_path)
    first = pd.DataFrame({"a": [1, 2]})
    assert not sink.exists("e", "p=1")
    path = sink.write("e", "p=1", first)
    sink.write("e", "p=1", pd.DataFrame({"a": [9]}))
    assert sink.exists("e", "p=1")
    assert pd.read_parquet(path)["a"].tolist() == [9]
    assert [p.name for p in path.parent.iterdir()] == ["part.parquet"]


def test_run_session_key_writes_all_entities(
    fake_client: FakeClient, tmp_path: Path
) -> None:
    report = run_session_key(
        9000, make_extractor(fake_client), ParquetSink(tmp_path), "r1"
    )
    written = {m.entity: m.rows_written for m in report.metrics}
    assert written == {
        "meetings": 1,
        "sessions": 1,
        "drivers": 2,
        "laps": 3,
        "stints": 2,
        "pit": 2,
        "weather": 2,
        "session_result": 2,
    }
    for entity in ("drivers", "laps", "session_result"):
        assert (tmp_path / entity / SESSION_PART).is_file()
    assert (tmp_path / "meetings" / "meeting_key=1200" / "part.parquet").is_file()
    assert (tmp_path / "sessions" / SESSION_PART).is_file()


def test_pipeline_is_idempotent(fake_client: FakeClient, tmp_path: Path) -> None:
    sink = ParquetSink(tmp_path)
    run_session_key(9000, make_extractor(fake_client), sink, "r1")
    first = snapshot(tmp_path)
    run_session_key(9000, make_extractor(fake_client), sink, "r2")
    second = snapshot(tmp_path)
    assert first.keys() == second.keys()
    for name in first:
        pd.testing.assert_frame_equal(first[name], second[name])


def test_skip_existing(fake_client: FakeClient, tmp_path: Path) -> None:
    sink = ParquetSink(tmp_path)
    run_session_key(9000, make_extractor(fake_client), sink, "r1")
    fake_client.calls.clear()
    report = run_session_key(
        9000, make_extractor(fake_client), sink, "r2", skip_existing=True
    )
    assert report.skipped and report.metrics == []
    assert [c[0] for c in fake_client.calls] == ["sessions", "meetings"]


def test_unknown_session_fails_fast(tmp_path: Path) -> None:
    extractor = make_extractor(FakeClient({}))
    with pytest.raises(PermanentApiError):
        run_session_key(1, extractor, ParquetSink(tmp_path), "r")


def test_missing_meeting_fails_fast(
    api_data: dict[str, list[Record]], tmp_path: Path
) -> None:
    api_data["meetings"] = []
    with pytest.raises(PermanentApiError):
        run_session_key(
            9000, make_extractor(FakeClient(api_data)), ParquetSink(tmp_path), "r"
        )


def test_invalid_data_is_not_written(
    api_data: dict[str, list[Record]], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = dict(SCHEMAS)
    broken["laps"] = SCHEMAS["laps"].__class__(
        "laps", {**SCHEMAS["laps"].columns, "extra": "int"}, SCHEMAS["laps"].key
    )
    monkeypatch.setattr("f1.pipelines.race_pipeline.SCHEMAS", broken)
    with pytest.raises(SchemaValidationError):
        run_session_key(
            9000, make_extractor(FakeClient(api_data)), ParquetSink(tmp_path), "r"
        )
    assert not (tmp_path / "laps").exists()


def test_run_year_skips_cancelled_and_collects_failures(
    api_data: dict[str, list[Record]], tmp_path: Path
) -> None:
    cancelled = {**api_data["meetings"][0], "meeting_key": 1, "is_cancelled": True}
    api_data["meetings"] = [cancelled, api_data["meetings"][0]]
    sink = ParquetSink(tmp_path)
    reports, failed = run_year(
        2024, make_extractor(FakeClient(api_data)), sink, "r", session_names=("Race",)
    )
    assert [r.session_key for r in reports] == [9000] and failed == []

    api_data["laps"] = [{"session_key": 9000, "driver_number": 1, "lap_number": 1}]
    sessions = [
        {**api_data["sessions"][0], "session_key": 9000},
        {**api_data["sessions"][0], "session_key": 9001},
    ]
    api_data["sessions"] = sessions

    class Failing(FakeClient):
        def get(self, endpoint: str, params: object = None) -> list[Record]:
            if params == {"session_key": 9001} and endpoint == "drivers":
                raise PermanentApiError("404")
            return super().get(endpoint, params)

    reports, failed = run_year(
        2024, make_extractor(Failing(api_data)), sink, "r", session_names=("Race",)
    )
    assert [r.session_key for r in reports] == [9000]
    assert failed == [9001]


def test_cli_session_key_and_exit_codes(
    fake_client: FakeClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    extractor = make_extractor(fake_client)
    assert main(["--session-key", "9000"], extractor=extractor) == 0
    assert (tmp_path / "laps" / SESSION_PART).is_file()
    assert main(["--year", "2024", "--skip-existing"], extractor=extractor) == 0
    assert main(["--session-key", "1"], extractor=make_extractor(FakeClient({}))) == 1


def test_cli_rejects_window_without_year(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--session-key", "1", "--start", "2024-01-01"])
    assert "--year" in capsys.readouterr().err


def test_cli_year_with_failed_session_returns_one(
    api_data: dict[str, list[Record]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    class Broken(FakeClient):
        def get(self, endpoint: str, params: object = None) -> list[Record]:
            if endpoint == "weather":
                raise PermanentApiError("HTTP 400")
            return super().get(endpoint, params)

    code = main(["--year", "2024"], extractor=make_extractor(Broken(api_data)))
    assert code == 1


def test_logs_carry_run_id(
    fake_client: FakeClient, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO):
        run_session_key(
            9000, make_extractor(fake_client), ParquetSink(tmp_path), "rid42"
        )
    steps = [r for r in caplog.records if getattr(r, "step", "") == "load"]
    assert len(steps) == 8 and all(r.run_id == "rid42" for r in steps)


def test_run_year_queries_each_session_name(
    fake_client: FakeClient, tmp_path: Path
) -> None:
    run_year(2024, make_extractor(fake_client), ParquetSink(tmp_path), "r")
    names = [
        p["session_name"]
        for endpoint, p in fake_client.calls
        if endpoint == "sessions" and "session_name" in p
    ]
    assert names == ["Race", "Qualifying"]


def test_cli_session_name_option(
    fake_client: FakeClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    argv = ["--year", "2024", "--session-name", "Qualifying"]
    assert main(argv, extractor=make_extractor(fake_client)) == 0
    names = [p.get("session_name") for e, p in fake_client.calls if e == "sessions"]
    assert names == ["Qualifying"]


def test_run_years_reports_progress_and_covers_each_year(
    fake_client: FakeClient, tmp_path: Path
) -> None:
    from f1.pipelines.race_pipeline import run_years

    events: list[tuple[int, int, str]] = []
    reports, failed = run_years(
        [2023, 2024],
        make_extractor(fake_client),
        ParquetSink(tmp_path),
        "r",
        session_names=("Race",),
        progress=lambda done, total, label: events.append((done, total, label)),
    )
    assert failed == []
    assert [e[:2] for e in events] == [(0, len(reports))] + [
        (i, len(reports)) for i in range(1, len(reports) + 1)
    ]
    assert events[0][2] == "" and "Test Grand Prix" in events[-1][2]
    assert {
        y for c, p in fake_client.calls if c == "meetings" for y in [p["year"]]
    } == {
        2023,
        2024,
    }


def test_cli_accepts_several_years_and_all_years(
    fake_client: FakeClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    extractor = make_extractor(fake_client)
    assert main(["--year", "2023", "--year", "2024"], extractor=extractor) == 0
    years = {p["year"] for c, p in fake_client.calls if c == "meetings"}
    assert years == {2023, 2024}
    fake_client.calls.clear()
    assert main(["--all-years"], extractor=extractor) == 0
    asked = {p["year"] for c, p in fake_client.calls if c == "meetings"}
    assert {2023, 2024} <= asked
