"""Carga em Parquet particionado com troca atômica."""

import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

FILE_NAME = "part.parquet"


class ParquetSink:
    """Grava ``<base_dir>/<entity>/<partition>/part.parquet``.

    A escrita vai para um arquivo temporário que substitui o definitivo de uma
    só vez; regravar a mesma partição é idempotente.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def _path(self, entity: str, partition: str) -> Path:
        return self._base_dir / entity / partition / FILE_NAME

    def write(self, entity: str, partition: str, df: pd.DataFrame) -> Path:
        """Grava a partição, substituindo o conteúdo anterior."""
        target = self._path(entity, partition)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".parquet.tmp")
        try:
            df.to_parquet(tmp, index=False)
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
        logger.debug("partição gravada", extra={"path": str(target), "rows": len(df)})
        return target

    def exists(self, entity: str, partition: str) -> bool:
        """Indica se a partição já foi gravada."""
        return self._path(entity, partition).is_file()
