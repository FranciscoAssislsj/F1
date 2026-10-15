"""Transformação de registros brutos da API em DataFrames tipados."""

import pandas as pd

from f1.core.interfaces import Record
from f1.core.models import TransformStats
from f1.core.schemas import SCHEMAS
from f1.transformation.clean import (
    conform,
    drop_duplicates_by_key,
    drop_null_keys,
    parse_gap,
)


def _add_gap_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "gap_to_leader" not in df.columns:
        return df
    parsed = df["gap_to_leader"].map(parse_gap)
    return df.assign(
        gap_to_leader_s=parsed.map(lambda pair: pair[0]),
        laps_down=parsed.map(lambda pair: pair[1]),
    )


def transform(
    entity: str, records: list[Record]
) -> tuple[pd.DataFrame, TransformStats]:
    """Converte registros brutos de uma entidade no schema de carga.

    Aplica tipagem explícita, descarta linhas com chave nula e duplicados
    (mantém a última) e devolve as contagens do que foi afetado.

    Raises:
        KeyError: Se ``entity`` não tiver schema.
    """
    schema = SCHEMAS[entity]
    raw = pd.DataFrame.from_records(records)
    if entity == "session_result":
        raw = _add_gap_columns(raw)
    typed, coerced = conform(raw, schema)
    keyed = drop_null_keys(typed, schema.key)
    unique = drop_duplicates_by_key(keyed, schema.key)
    stats = TransformStats(
        rows_in=len(typed),
        rows_rejected=len(typed) - len(keyed),
        duplicates_dropped=len(keyed) - len(unique),
        values_coerced=coerced,
    )
    return unique, stats
