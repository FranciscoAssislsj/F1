"""Validação de DataFrames contra o schema da entidade."""

from collections.abc import Callable

import pandas as pd
from pandas.api import types as pdt

from f1.core.exceptions import SchemaValidationError
from f1.core.schemas import EntitySchema

_DTYPE_CHECKS: dict[str, Callable[[object], bool]] = {
    "int": lambda dtype: str(dtype) == "Int64",
    "float": lambda dtype: str(dtype) == "Float64",
    "str": lambda dtype: pdt.is_string_dtype(dtype),
    "bool": lambda dtype: str(dtype) == "boolean",
    "datetime": lambda dtype: (
        pdt.is_datetime64_any_dtype(dtype) and getattr(dtype, "tz", None) is not None
    ),
}


def validate(df: pd.DataFrame, schema: EntitySchema) -> None:
    """Falha rápido se o DataFrame violar o schema.

    Verifica colunas presentes, tipos, chave sem nulos e chave única.

    Raises:
        SchemaValidationError: Com a lista de todas as violações encontradas.
    """
    errors: list[str] = []
    missing = [c for c in schema.columns if c not in df.columns]
    if missing:
        errors.append(f"colunas ausentes: {missing}")
    for column, kind in schema.columns.items():
        if column in df.columns and not _DTYPE_CHECKS[kind](df[column].dtype):
            errors.append(
                f"tipo inesperado em {column}: {df[column].dtype} (esperado {kind})"
            )
    if not missing:
        null_keys = [c for c in schema.key if df[c].isna().any()]
        if null_keys:
            errors.append(f"chave com nulos: {null_keys}")
        duplicated = int(df.duplicated(subset=list(schema.key)).sum())
        if duplicated:
            errors.append(f"{duplicated} linhas com chave duplicada {schema.key}")
    if errors:
        raise SchemaValidationError(f"{schema.name}: " + "; ".join(errors))
