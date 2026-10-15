"""Leitura das partições Parquet gravadas por ``ParquetSink``."""

from pathlib import Path

import pandas as pd

from f1.integrations.parquet_sink import FILE_NAME


class ParquetReader:
    """Lê ``<base_dir>/<entity>/<partition>/part.parquet``."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def last_modified_ns(self) -> int:
        """Data de modificação (ns) do Parquet mais recente; 0 se não houver nenhum."""
        paths = self._base_dir.glob(f"*/*/{FILE_NAME}")
        return max((p.stat().st_mtime_ns for p in paths), default=0)

    def read(self, entity: str, partition: str) -> pd.DataFrame:
        """Lê uma partição; DataFrame vazio se ela não existir."""
        path = self._base_dir / entity / partition / FILE_NAME
        return pd.read_parquet(path) if path.is_file() else pd.DataFrame()

    def read_all(self, entity: str) -> pd.DataFrame:
        """Concatena todas as partições da entidade; vazio se não houver nenhuma."""
        paths = sorted((self._base_dir / entity).glob(f"*/{FILE_NAME}"))
        if not paths:
            return pd.DataFrame()
        return pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
