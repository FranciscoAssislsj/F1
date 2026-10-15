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


DEFAULT_COLOUR = "#888888"
PACE_TOLERANCE = 1.07  # voltas > 107% da melhor são tratadas como ruído (SC, box)


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


def team_fastest_counts(table: pd.DataFrame) -> pd.DataFrame:
    """Quantas vezes cada equipe teve a volta mais rápida (``rank`` 1) nos GPs."""
    firsts = table[table["rank"].eq(1)]
    counts = firsts.groupby("team_name").size().reset_index(name="gps")
    return counts.sort_values(["gps", "team_name"], ascending=[False, True])


def session_laps(
    laps: pd.DataFrame, drivers: pd.DataFrame, session_key: int
) -> pd.DataFrame:
    """Voltas de uma sessão com nome do piloto, equipe, cor da equipe e ``mate``.

    ``mate`` (0, 1, ...) distingue pilotos da mesma equipe, que compartilham a cor.
    """
    people = drivers[drivers["session_key"].eq(session_key)].drop_duplicates(
        "driver_number"
    )[["driver_number", "full_name", "team_name", "team_colour"]]
    rows = laps[laps["session_key"].eq(session_key)].merge(
        people, on="driver_number", how="left"
    )
    rows["driver"] = rows["full_name"].fillna(rows["driver_number"].astype("string"))
    rows["team_name"] = rows["team_name"].fillna("Desconhecida")
    rows["colour"] = ("#" + rows["team_colour"]).fillna(DEFAULT_COLOUR)
    pairs = rows[["team_name", "driver"]].drop_duplicates().sort_values("driver")
    pairs["mate"] = pairs.groupby("team_name").cumcount()
    return rows.merge(pairs, on=["team_name", "driver"])


def pace_laps(rows: pd.DataFrame) -> pd.DataFrame:
    """Voltas cronometradas (sem saída dos boxes) até 107% da melhor da sessão."""
    valid = rows[rows["lap_duration"].notna() & ~rows["is_pit_out_lap"].fillna(False)]
    if valid.empty:
        return valid.assign(lap_duration=pd.Series(dtype="float64"))
    cutoff = valid["lap_duration"].min() * PACE_TOLERANCE
    kept = valid[valid["lap_duration"] <= cutoff].copy()
    kept["lap_duration"] = kept["lap_duration"].astype("float64")
    kept["lap_number"] = kept["lap_number"].astype("int64")
    return kept


def top_speeds(rows: pd.DataFrame) -> pd.DataFrame:
    """Maior velocidade final (``st_speed``, km/h) de cada piloto na sessão."""
    speeds = rows[rows["st_speed"].notna()]
    best = speeds.groupby(["driver", "team_name", "colour"], as_index=False)[
        "st_speed"
    ].max()
    best["st_speed"] = best["st_speed"].astype("int64")
    return best.sort_values("st_speed", ascending=False).reset_index(drop=True)
