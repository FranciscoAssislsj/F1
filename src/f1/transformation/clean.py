"""Funções puras de limpeza e tipagem de DataFrames."""

import re
from typing import Any

import pandas as pd

from f1.core.schemas import EntitySchema

_LAPS_DOWN = re.compile(r"^\+\s*(\d+)\s*LAPS?$", re.IGNORECASE)
_TRUE = {"true", "1", "yes"}
_FALSE = {"false", "0", "no"}


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool | list | dict):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
    return None


def _to_str(value: Any) -> str | None:
    if value is None or isinstance(value, list | dict):
        return None
    text = str(value).strip()
    return text or None


def parse_gap(value: Any) -> tuple[float | None, int | None]:
    """Separa ``gap_to_leader`` em (segundos, voltas de atraso).

    Números viram segundos; ``"+N LAP(S)"`` vira N voltas de atraso; qualquer
    outro valor (inclusive nulo e arrays de qualificação) vira ``(None, None)``.
    """
    if isinstance(value, str):
        match = _LAPS_DOWN.match(value.strip())
        if match:
            return None, int(match.group(1))
    return _to_float(value), None


def _cast(series: pd.Series, kind: str) -> pd.Series:
    if kind == "int":
        numbers = series.map(_to_float).astype("Float64")
        return numbers.where(numbers == numbers.round()).astype("Int64")
    if kind == "float":
        return series.map(_to_float).astype("Float64")
    if kind == "str":
        return series.map(_to_str).astype("string")
    if kind == "bool":
        return series.map(_to_bool).astype("boolean")
    if kind == "datetime":
        return pd.to_datetime(series, utc=True, errors="coerce").astype(
            "datetime64[ns, UTC]"
        )
    raise ValueError(f"Tipo lógico desconhecido: {kind}")


def conform(df: pd.DataFrame, schema: EntitySchema) -> tuple[pd.DataFrame, int]:
    """Aplica os tipos do schema, mantendo só as colunas dele (ausentes viram nulas).

    Returns:
        O DataFrame tipado e a quantidade de valores não nulos que não puderam
        ser convertidos e viraram nulos.
    """
    out = pd.DataFrame(index=df.index)
    coerced = 0
    for column, kind in schema.columns.items():
        source = df[column] if column in df.columns else pd.Series(None, index=df.index)
        typed = _cast(source, kind)
        coerced += int((typed.isna() & source.notna()).sum())
        out[column] = typed
    return out, coerced


def drop_null_keys(df: pd.DataFrame, key: tuple[str, ...]) -> pd.DataFrame:
    """Remove linhas com qualquer coluna da chave nula."""
    return df.dropna(subset=list(key)).reset_index(drop=True)


def drop_duplicates_by_key(df: pd.DataFrame, key: tuple[str, ...]) -> pd.DataFrame:
    """Remove duplicados pela chave, mantendo a última ocorrência."""
    return df.drop_duplicates(subset=list(key), keep="last").reset_index(drop=True)
