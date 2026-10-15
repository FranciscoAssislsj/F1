import os
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from f1.ingestion.extractors import Extractor
from f1.integrations.parquet_reader import ParquetReader
from f1.integrations.parquet_sink import ParquetSink
from f1.pipelines.race_pipeline import run_session_key
from f1.transformation.metrics import (
    fastest_laps,
    format_lap_time,
    pace_laps,
    session_laps,
    team_fastest_counts,
    top_speeds,
)
from tests.conftest import FakeClient

DASHBOARD = Path(__file__).parents[2] / "src" / "f1" / "dashboard.py"


@pytest.fixture
def loaded(fake_client: FakeClient, tmp_path: Path) -> ParquetReader:
    run_session_key(
        9000, Extractor(fake_client, sleep=lambda _: None), ParquetSink(tmp_path), "r"
    )
    return ParquetReader(tmp_path)


def laps_for(reader: ParquetReader, year: int = 2024, name: str = "Race", top: int = 5):
    return fastest_laps(
        reader.read_all("laps"),
        reader.read_all("drivers"),
        reader.read_all("sessions"),
        reader.read_all("meetings"),
        year,
        name,
        top,
    )


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (92.608, "1:32.608"),
        (59.9, "0:59.900"),
        (125.0, "2:05.000"),
        (59.9996, "1:00.000"),
    ],
)
def test_format_lap_time(seconds: float, expected: str) -> None:
    assert format_lap_time(seconds) == expected


def test_reader_read_and_read_all(loaded: ParquetReader, tmp_path: Path) -> None:
    assert len(loaded.read("laps", "session_key=9000")) == 3
    assert loaded.read("laps", "session_key=1").empty
    assert len(loaded.read_all("drivers")) == 2
    assert ParquetReader(tmp_path / "vazio").read_all("laps").empty


def test_fastest_laps_ranks_by_time_and_skips_laps_without_time(
    loaded: ParquetReader,
) -> None:
    table = laps_for(loaded)
    # 4 voltas na fixture: 1 sem tempo e 1 duplicada (a última é mantida)
    assert table["driver"].tolist() == ["Ana Silva", "Bob Lee"]
    assert table["lap_duration"].tolist() == [95.7, 101.2]
    assert table["rank"].tolist() == [1, 2]
    assert table["meeting_name"].iloc[0] == "Test Grand Prix"
    assert table["team_name"].tolist() == ["Alpha", "Beta"]


def test_fastest_laps_respects_top(loaded: ParquetReader) -> None:
    assert len(laps_for(loaded, top=1)) == 1


@pytest.mark.parametrize(("year", "name"), [(2023, "Race"), (2024, "Qualifying")])
def test_fastest_laps_empty_for_other_filters(
    loaded: ParquetReader, year: int, name: str
) -> None:
    assert laps_for(loaded, year, name).empty


def test_fastest_laps_without_driver_or_meeting_info(loaded: ParquetReader) -> None:
    table = fastest_laps(
        loaded.read_all("laps"),
        pd.DataFrame(
            columns=["session_key", "driver_number", "full_name", "team_name"]
        ),
        loaded.read_all("sessions"),
        pd.DataFrame(columns=["meeting_key", "meeting_name"]),
        2024,
        "Race",
    )
    assert table["driver"].tolist() == ["1", "44"]
    assert table["meeting_name"].iloc[0] == "GP desconhecido"


def test_dashboard_renders_filters_and_expander(
    loaded: ParquetReader, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(DASHBOARD), default_timeout=30).run()
    assert not app.exception
    assert [s.label for s in app.sidebar.selectbox] == ["Ano", "Tipo de sessão"]
    assert app.sidebar.selectbox[1].options == ["Race"]
    assert app.expander[0].label == "🏁 Test Grand Prix — Testville, Testland"


def test_dashboard_without_data_shows_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "vazio"))
    app = AppTest.from_file(str(DASHBOARD), default_timeout=30).run()
    assert not app.exception
    assert "Nenhum dado" in app.info[0].value


def test_reader_last_modified_changes_with_writes(
    loaded: ParquetReader, tmp_path: Path
) -> None:
    before = loaded.last_modified_ns()
    assert before > 0
    assert ParquetReader(tmp_path / "vazio").last_modified_ns() == 0
    ParquetSink(tmp_path).write("laps", "session_key=1", pd.DataFrame({"a": [1]}))
    assert loaded.last_modified_ns() >= before


def test_dashboard_picks_up_new_data_without_clearing_cache(
    api_data: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    sink = ParquetSink(tmp_path)

    def load() -> None:
        extractor = Extractor(FakeClient(api_data), sleep=lambda _: None)
        run_session_key(9000, extractor, sink, "r")

    load()
    app = AppTest.from_file(str(DASHBOARD), default_timeout=30).run()
    assert app.expander[0].label.startswith("🏁 Test Grand Prix")

    for path in tmp_path.rglob("*.parquet"):  # garante mtime anterior ao novo
        os.utime(path, ns=(1, 1))
    api_data["meetings"][0]["meeting_name"] = "Novo GP"
    load()
    app.run()
    assert app.expander[0].label.startswith("🏁 Novo GP")


def test_team_fastest_counts(loaded: ParquetReader) -> None:
    counts = team_fastest_counts(laps_for(loaded))
    assert counts.to_dict("records") == [{"team_name": "Alpha", "gps": 1}]


def test_session_laps_pace_and_top_speeds(loaded: ParquetReader) -> None:
    rows = session_laps(loaded.read_all("laps"), loaded.read_all("drivers"), 9000)
    assert set(rows["driver"]) == {"Ana Silva", "Bob Lee"}
    assert rows["colour"].str.startswith("#").all()
    pace = pace_laps(rows)
    assert pace["lap_duration"].notna().all()
    assert pace["lap_duration"].dtype == "float64"
    speeds = top_speeds(rows)
    assert speeds["st_speed"].is_monotonic_decreasing
    assert set(speeds["driver"]) <= {"Ana Silva", "Bob Lee"}


def test_dashboard_renders_charts_tab(
    loaded: ParquetReader, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(DASHBOARD), default_timeout=30).run()
    assert not app.exception
    assert [t.label for t in app.tabs] == ["🏁 Tabelas", "📊 Gráficos"]
    assert app.selectbox(key="chart_gp").value == 9000
    assert len(app.get("vega_lite_chart")) >= 3


def test_dashboard_loader_runs_pipeline_with_progress(
    api_data: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        "f1.integrations.openf1_client.OpenF1Client.from_settings",
        classmethod(lambda cls, settings: FakeClient(api_data)),
    )
    monkeypatch.setattr("time.sleep", lambda _: None)
    app = AppTest.from_file(str(DASHBOARD), default_timeout=30).run()
    assert "Nenhum dado" in app.info[0].value
    app.sidebar.multiselect(key="load_years").set_value([2024])
    app.sidebar.button(key="load_run").click().run()
    assert not app.exception
    assert (tmp_path / "laps").exists()
    assert app.expander[0].label.startswith("🏁 Test Grand Prix")
