"""Dashboard Streamlit: voltas mais rápidas por GP, a partir dos Parquet do pipeline.

Execução: ``poetry run streamlit run src/f1/dashboard.py``
"""

from collections.abc import Callable
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from f1.config.settings import Settings
from f1.core.exceptions import (
    PermanentApiError,
    SchemaValidationError,
    TransientApiError,
)
from f1.ingestion.extractors import Extractor
from f1.integrations.openf1_client import OpenF1Client
from f1.integrations.parquet_reader import ParquetReader
from f1.integrations.parquet_sink import ParquetSink
from f1.pipelines.race_pipeline import FIRST_YEAR, run_years
from f1.transformation.metrics import (
    DEFAULT_COLOUR,
    fastest_laps,
    format_lap_time,
    pace_laps,
    session_laps,
    team_fastest_counts,
    top_speeds,
)
from f1.utils.logging import new_run_id

TOP_LAPS = 5
ENTITIES = ("meetings", "sessions", "drivers", "laps")
ACCENT = "#e10600"
DASHES = [[1, 0], [6, 4], [2, 2]]  # um traço por companheiro de equipe


@st.cache_data(show_spinner=False)
def load_data(data_dir: str, version: int) -> dict[str, pd.DataFrame]:
    """Lê os Parquet; ``version`` só serve de chave para invalidar o cache."""
    reader = ParquetReader(Path(data_dir))
    return {name: reader.read_all(name) for name in ENTITIES}


def render_session(rows: pd.DataFrame) -> None:
    table = pd.DataFrame(
        {
            "#": rows["rank"],
            "Piloto": rows["driver"],
            "Equipe": rows["team_name"],
            "Volta": rows["lap_number"],
            "Tempo": rows["lap_duration"].map(format_lap_time),
        }
    )
    st.dataframe(table, hide_index=True, width="stretch")


def colour_scale(frame: pd.DataFrame, key: str) -> alt.Scale:
    pairs = frame.drop_duplicates(key)
    return alt.Scale(domain=pairs[key].tolist(), range=pairs["colour"].tolist())


def team_chart(table: pd.DataFrame) -> alt.Chart:
    counts = team_fastest_counts(table)
    return (
        alt.Chart(counts)
        .mark_bar(color=ACCENT)
        .encode(
            y=alt.Y("team_name:N", sort="-x", title=None),
            x=alt.X(
                "gps:Q",
                title="GPs com a volta mais rápida",
                axis=alt.Axis(tickMinStep=1),
            ),
            tooltip=[
                alt.Tooltip("team_name:N", title="Equipe"),
                alt.Tooltip("gps:Q", title="GPs"),
            ],
        )
    )


def gap_chart(rows: pd.DataFrame, colours: dict[str, str]) -> alt.Chart:
    gaps = rows.assign(
        gap=rows["lap_duration"] - rows["lap_duration"].min(),
        tempo=rows["lap_duration"].map(format_lap_time),
        colour=rows["team_name"].map(colours).fillna(DEFAULT_COLOUR),
    )
    return (
        alt.Chart(gaps)
        .mark_bar()
        .encode(
            y=alt.Y("driver:N", sort=alt.EncodingSortField("rank"), title=None),
            x=alt.X("gap:Q", title="Diferença para a mais rápida (s)"),
            color=alt.Color(
                "driver:N", scale=colour_scale(gaps, "driver"), legend=None
            ),
            tooltip=[
                alt.Tooltip("driver:N", title="Piloto"),
                alt.Tooltip("team_name:N", title="Equipe"),
                alt.Tooltip("tempo:N", title="Tempo"),
                alt.Tooltip("gap:Q", title="Diferença (s)", format="+.3f"),
            ],
        )
    )


def pace_chart(pace: pd.DataFrame) -> alt.Chart:
    pace = pace.assign(tempo=pace["lap_duration"].map(format_lap_time))
    return (
        alt.Chart(pace)
        .mark_line(point=alt.OverlayMarkDef(size=18))
        .encode(
            x=alt.X("lap_number:Q", title="Volta", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y(
                "lap_duration:Q",
                title="Tempo de volta (s)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color(
                "driver:N", scale=colour_scale(pace, "driver"), title="Piloto"
            ),
            strokeDash=alt.StrokeDash(
                "mate:N", scale=alt.Scale(domain=[0, 1, 2], range=DASHES), legend=None
            ),
            tooltip=[
                alt.Tooltip("driver:N", title="Piloto"),
                alt.Tooltip("lap_number:Q", title="Volta"),
                alt.Tooltip("tempo:N", title="Tempo"),
            ],
        )
        .interactive()
    )


def speed_chart(speeds: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(speeds)
        .mark_bar()
        .encode(
            y=alt.Y("driver:N", sort="-x", title=None),
            x=alt.X(
                "st_speed:Q",
                title="Velocidade máxima (km/h)",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color(
                "driver:N", scale=colour_scale(speeds, "driver"), legend=None
            ),
            tooltip=[
                alt.Tooltip("driver:N", title="Piloto"),
                alt.Tooltip("team_name:N", title="Equipe"),
                alt.Tooltip("st_speed:Q", title="km/h"),
            ],
        )
    )


def render_charts(
    table: pd.DataFrame, data: dict[str, pd.DataFrame], suffix: str = ""
) -> None:
    st.subheader("Temporada")
    st.altair_chart(team_chart(table), width="stretch")

    st.subheader("Por Grande Prêmio")
    labels = {
        key: f"{rows.iloc[0]['meeting_name']} — {rows.iloc[0]['location']}"
        for key, rows in table.groupby("session_key", sort=False)
    }
    session_key = st.selectbox(
        "Grande Prêmio", list(labels), format_func=labels.get, key=f"chart_gp{suffix}"
    )
    rows = session_laps(data["laps"], data["drivers"], int(session_key))
    colours = (
        rows.drop_duplicates("team_name").set_index("team_name")["colour"].to_dict()
    )

    left, right = st.columns(2)
    with left:
        st.markdown(f"**{TOP_LAPS} voltas mais rápidas**")
        top = table[table["session_key"].eq(session_key)]
        st.altair_chart(gap_chart(top, colours), width="stretch")
    with right:
        st.markdown("**Velocidade máxima por piloto**")
        speeds = top_speeds(rows)
        if speeds.empty:
            st.caption("Sem dados de velocidade para esta sessão.")
        else:
            st.altair_chart(speed_chart(speeds), width="stretch")

    st.markdown("**Ritmo volta a volta**")
    pace = pace_laps(rows)
    if pace.empty:
        st.caption("Sem voltas cronometradas para esta sessão.")
        return
    order = pace.groupby("driver")["lap_duration"].min().sort_values().index.tolist()
    chosen = st.multiselect(
        "Pilotos", order, default=order[:5], key=f"pace_{session_key}{suffix}"
    )
    if chosen:
        st.altair_chart(pace_chart(pace[pace["driver"].isin(chosen)]), width="stretch")
    else:
        st.caption("Escolha ao menos um piloto.")


def loader_controls() -> tuple[list[int], bool, bool, DeltaGenerator]:
    """Controles da barra lateral; devolve anos, "pular", "carregar" e a barra."""
    years = list(range(date.today().year, FIRST_YEAR - 1, -1))
    with st.sidebar.expander("⬇️ Carregar dados da OpenF1"):
        chosen = st.multiselect("Anos", years, default=years[:1], key="load_years")
        skip = st.checkbox("Pular sessões já carregadas", value=True, key="load_skip")
        run = st.button("Carregar", disabled=not chosen, key="load_run")
        bar = st.empty()
    return chosen, skip, run, bar


def run_loader(
    settings: Settings,
    years: list[int],
    skip: bool,
    bar: DeltaGenerator,
    on_session: Callable[[int], None],
) -> None:
    """Roda o pipeline; ``on_session`` é chamado a cada sessão concluída."""

    def on_progress(done: int, total: int, label: str) -> None:
        text = f"{done}/{total} sessões — {label}" if done else "Listando sessões…"
        bar.progress(done / total if total else 1.0, text=text)
        if done:
            on_session(done)

    bar.progress(0.0, text="Listando sessões…")
    extractor = Extractor(OpenF1Client.from_settings(settings))
    try:
        reports, failed = run_years(
            sorted(years),
            extractor,
            ParquetSink(settings.data_dir),
            new_run_id(),
            skip_existing=skip,
            progress=on_progress,
        )
    except (TransientApiError, PermanentApiError, SchemaValidationError) as exc:
        bar.empty()
        st.sidebar.error(f"Carga interrompida: {exc}")
        return
    bar.progress(1.0, text=f"Concluído: {len(reports)} sessões")
    if failed:
        st.sidebar.warning(f"{len(failed)} sessões falharam: {failed}")
    else:
        st.rerun()


def render_content(
    data: dict[str, pd.DataFrame],
    data_dir: str,
    year: int | None,
    session_name: str | None,
    suffix: str = "",
) -> None:
    """Corpo da página; ``suffix`` evita chaves de widget repetidas ao redesenhar."""
    sessions = data["sessions"]
    if year is None or sessions.empty or data["laps"].empty:
        st.title("🏎️ F1 — Voltas mais rápidas por circuito")
        st.info(
            f"Nenhum dado em `{data_dir}`. Use **Carregar dados da OpenF1** na barra "
            "lateral ou rode `poetry run python -m f1.pipelines.cli --all-years`"
        )
        return
    st.title(f"🏎️ F1 — {TOP_LAPS} voltas mais rápidas por circuito")
    table = fastest_laps(
        data["laps"],
        data["drivers"],
        sessions,
        data["meetings"],
        year,
        session_name,
        TOP_LAPS,
    )
    if table.empty:
        st.warning("Sem voltas registradas para este filtro.")
        return
    tab_table, tab_charts = st.tabs(["🏁 Tabelas", "📊 Gráficos"])
    with tab_table:
        for _, rows in table.groupby("session_key", sort=False):
            first = rows.iloc[0]
            label = (
                f"🏁 {first['meeting_name']} — {first['location']}, "
                f"{first['country_name']}"
            )
            with st.expander(label):
                render_session(rows)
    with tab_charts:
        render_charts(table, data, suffix)


def live_filters(
    sessions: pd.DataFrame, year: int | None, name: str | None, loading: list[int]
) -> tuple[int, str] | None:
    """Ano e sessão exibidos durante a carga (o filtro, se estiver sendo carregado)."""
    if sessions.empty:
        return None
    available = {int(y) for y in sessions["year"].unique()}
    if year not in available or year not in loading:
        candidates = [y for y in loading if y in available]
        if not candidates:
            return None
        year = max(candidates)
    types = sorted(sessions.loc[sessions["year"] == year, "session_name"].unique())
    return year, name if name in types else types[0]


def main() -> None:
    st.set_page_config(page_title="F1 — OpenF1", page_icon="🏎️", layout="wide")
    settings = Settings.from_env()
    data_dir = str(settings.data_dir)
    reader = ParquetReader(Path(data_dir))
    years, skip, run, bar = loader_controls()
    data = load_data(data_dir, reader.last_modified_ns())
    sessions = data["sessions"]

    year: int | None = None
    session_name: str | None = None
    if not (sessions.empty or data["laps"].empty):
        st.sidebar.header("Filtros")
        year = int(
            st.sidebar.selectbox("Ano", sorted(sessions["year"].unique(), reverse=True))
        )
        types = sorted(sessions.loc[sessions["year"] == year, "session_name"].unique())
        session_name = st.sidebar.selectbox("Tipo de sessão", types)

    content = st.empty()
    with content.container():
        render_content(data, data_dir, year, session_name)
    if not run:
        return

    def refresh(done: int) -> None:
        """Redesenha o corpo da página com o que já foi gravado em disco."""
        fresh = load_data(data_dir, reader.last_modified_ns())
        view = live_filters(fresh["sessions"], year, session_name, years)
        if view is None or fresh["laps"].empty:
            return
        with content.container():
            render_content(fresh, data_dir, view[0], view[1], suffix=f"_live{done}")

    run_loader(settings, years, skip, bar, refresh)


main()
