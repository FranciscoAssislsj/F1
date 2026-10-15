"""Schemas das entidades carregadas (tipagem e chaves definidas em um só lugar)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EntitySchema:
    """Schema de uma entidade.

    Attributes:
        name: Nome da entidade (igual ao endpoint de origem).
        columns: Coluna -> tipo lógico (``int``, ``float``, ``str``, ``bool`` ou
            ``datetime``), na ordem de saída.
        key: Colunas que identificam unicamente uma linha; nunca nulas.
    """

    name: str
    columns: dict[str, str]
    key: tuple[str, ...]


_KEYS = {"meeting_key": "int", "session_key": "int"}

MEETINGS = EntitySchema(
    "meetings",
    {
        "meeting_key": "int",
        "year": "int",
        "meeting_name": "str",
        "meeting_official_name": "str",
        "country_name": "str",
        "country_code": "str",
        "location": "str",
        "circuit_key": "int",
        "circuit_short_name": "str",
        "date_start": "datetime",
        "date_end": "datetime",
        "gmt_offset": "str",
        "is_cancelled": "bool",
    },
    key=("meeting_key",),
)

SESSIONS = EntitySchema(
    "sessions",
    {
        **_KEYS,
        "year": "int",
        "session_name": "str",
        "session_type": "str",
        "country_name": "str",
        "location": "str",
        "circuit_short_name": "str",
        "date_start": "datetime",
        "date_end": "datetime",
        "gmt_offset": "str",
        "is_cancelled": "bool",
    },
    key=("session_key",),
)

DRIVERS = EntitySchema(
    "drivers",
    {
        **_KEYS,
        "driver_number": "int",
        "full_name": "str",
        "broadcast_name": "str",
        "name_acronym": "str",
        "first_name": "str",
        "last_name": "str",
        "team_name": "str",
        "team_colour": "str",
        "headshot_url": "str",
    },
    key=("session_key", "driver_number"),
)

LAPS = EntitySchema(
    "laps",
    {
        **_KEYS,
        "driver_number": "int",
        "lap_number": "int",
        "date_start": "datetime",
        "lap_duration": "float",
        "duration_sector_1": "float",
        "duration_sector_2": "float",
        "duration_sector_3": "float",
        "i1_speed": "int",
        "i2_speed": "int",
        "st_speed": "int",
        "is_pit_out_lap": "bool",
    },
    key=("session_key", "driver_number", "lap_number"),
)

STINTS = EntitySchema(
    "stints",
    {
        **_KEYS,
        "driver_number": "int",
        "stint_number": "int",
        "compound": "str",
        "lap_start": "int",
        "lap_end": "int",
        "tyre_age_at_start": "int",
    },
    key=("session_key", "driver_number", "stint_number"),
)

PIT = EntitySchema(
    "pit",
    {
        **_KEYS,
        "driver_number": "int",
        "date": "datetime",
        "lap_number": "int",
        "lane_duration": "float",
        "stop_duration": "float",
    },
    key=("session_key", "driver_number", "date"),
)

SESSION_RESULT = EntitySchema(
    "session_result",
    {
        **_KEYS,
        "driver_number": "int",
        "position": "int",
        "number_of_laps": "int",
        "duration": "float",
        "gap_to_leader_s": "float",
        "laps_down": "int",
        "dnf": "bool",
        "dns": "bool",
        "dsq": "bool",
    },
    key=("session_key", "driver_number"),
)

WEATHER = EntitySchema(
    "weather",
    {
        **_KEYS,
        "date": "datetime",
        "air_temperature": "float",
        "track_temperature": "float",
        "humidity": "float",
        "pressure": "float",
        "rainfall": "int",
        "wind_direction": "int",
        "wind_speed": "float",
    },
    key=("session_key", "date"),
)

SCHEMAS: dict[str, EntitySchema] = {
    schema.name: schema
    for schema in (
        MEETINGS,
        SESSIONS,
        DRIVERS,
        LAPS,
        STINTS,
        PIT,
        SESSION_RESULT,
        WEATHER,
    )
}

# Entidades extraídas por ``session_key``. ``session_result`` vem por último:
# sua presença marca a sessão como concluída (usado por ``--skip-existing``).
SESSION_ENTITIES = (
    "drivers",
    "laps",
    "stints",
    "pit",
    "weather",
    "session_result",
)
