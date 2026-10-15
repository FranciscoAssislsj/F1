"""Contratos entre as camadas (sem I/O)."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

Params = Mapping[str, Any]
Record = dict[str, Any]


class ApiClient(Protocol):
    """Cliente de leitura da API."""

    def get(self, endpoint: str, params: Params | None = None) -> list[Record]:
        """Retorna os registros de um endpoint."""
        ...


class Sink(Protocol):
    """Destino de carga particionado."""

    def write(self, entity: str, partition: str, df: pd.DataFrame) -> Path:
        """Grava a partição substituindo qualquer conteúdo anterior."""
        ...

    def exists(self, entity: str, partition: str) -> bool:
        """Indica se a partição já foi gravada."""
        ...
