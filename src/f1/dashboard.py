"""Dashboard Streamlit: voltas mais rápidas por GP, a partir dos Parquet do pipeline.

Execução: ``poetry run streamlit run src/f1/dashboard.py``
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from f1.config.settings import Settings
from f1.integrations.parquet_reader import ParquetReader
from f1.transformation.metrics import fastest_laps, format_lap_time

TOP_LAPS = 5
ENTITIES = ("meetings", "sessions", "drivers", "laps")


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


def main() -> None:
    st.set_page_config(page_title="F1 — OpenF1", page_icon="🏎️", layout="wide")
    data_dir = str(Settings.from_env().data_dir)
    data = load_data(data_dir, ParquetReader(Path(data_dir)).last_modified_ns())
    sessions = data["sessions"]
    if sessions.empty or data["laps"].empty:
        st.title("🏎️ F1 — Voltas mais rápidas por circuito")
        st.info(
            f"Nenhum dado em `{data_dir}`. Rode antes: "
            "`poetry run python -m f1.pipelines.cli --year 2024`"
        )
        return

    st.sidebar.header("Filtros")
    year = st.sidebar.selectbox("Ano", sorted(sessions["year"].unique(), reverse=True))
    types = sorted(sessions.loc[sessions["year"] == year, "session_name"].unique())
    session_name = st.sidebar.selectbox("Tipo de sessão", types)

    st.title(f"🏎️ F1 — {TOP_LAPS} voltas mais rápidas por circuito")
    table = fastest_laps(
        data["laps"],
        data["drivers"],
        sessions,
        data["meetings"],
        int(year),
        session_name,
        TOP_LAPS,
    )
    if table.empty:
        st.warning("Sem voltas registradas para este filtro.")
        return
    for _, rows in table.groupby("session_key", sort=False):
        first = rows.iloc[0]
        label = (
            f"🏁 {first['meeting_name']} — {first['location']}, {first['country_name']}"
        )
        with st.expander(label):
            render_session(rows)


main()
