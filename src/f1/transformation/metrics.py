"""Funções puras que preparam os dados carregados para análise."""

import pandas as pd

FASTEST_LAP_COLUMNS = [
    "session_key",
    "meeting_name",
    "location",
    "country_name",
    "date_start",
    "rank",
    "driver",
    "team_name",
    "lap_number",
    "lap_duration",
]


def format_lap_time(seconds: float) -> str:
    """Formata segundos como ``m:ss.mmm`` (ex.: ``92.608`` -> ``1:32.608``)."""
    minutes, rest = divmod(round(seconds * 1000), 60_000)
    return f"{minutes}:{rest / 1000:06.3f}"


def fastest_laps(
    laps: pd.DataFrame,
    drivers: pd.DataFrame,
    sessions: pd.DataFrame,
    meetings: pd.DataFrame,
    year: int,
    session_name: str,
    top: int = 5,
) -> pd.DataFrame:
    """As ``top`` voltas mais rápidas de cada sessão do ano e tipo informados.

    Voltas sem tempo são ignoradas. O resultado traz uma linha por volta,
    ordenado por data da sessão e depois por posição (``rank``, a partir de 1).
    """
    chosen = sessions[
        sessions["year"].eq(year).fillna(False)
        & sessions["session_name"].eq(session_name).fillna(False)
    ]
    if chosen.empty or laps.empty:
        return pd.DataFrame(columns=FASTEST_LAP_COLUMNS)

    names = meetings[["meeting_key", "meeting_name"]]
    info = chosen[
        ["session_key", "meeting_key", "location", "country_name", "date_start"]
    ].merge(names, on="meeting_key", how="left")
    info["meeting_name"] = info["meeting_name"].fillna("GP desconhecido")

    people = drivers[["session_key", "driver_number", "full_name", "team_name"]]
    ranked = (
        laps[laps["lap_duration"].notna()][
            ["session_key", "driver_number", "lap_number", "lap_duration"]
        ]
        .merge(info, on="session_key")
        .merge(people, on=["session_key", "driver_number"], how="left")
        .sort_values(["session_key", "lap_duration"])
    )
    ranked["driver"] = ranked["full_name"].fillna(
        ranked["driver_number"].astype("string")
    )
    ranked = ranked.groupby("session_key", sort=False).head(top)
    ranked["rank"] = ranked.groupby("session_key").cumcount() + 1
    return ranked.sort_values(["date_start", "rank"])[FASTEST_LAP_COLUMNS].reset_index(
        drop=True
    )
