"""Modelos de dados do pipeline."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TransformStats:
    """Contagens de uma transformação.

    Attributes:
        rows_in: Linhas recebidas.
        rows_rejected: Linhas descartadas por chave nula.
        duplicates_dropped: Linhas descartadas por chave duplicada.
        values_coerced: Valores convertidos em nulo por tipo inesperado.
    """

    rows_in: int
    rows_rejected: int
    duplicates_dropped: int
    values_coerced: int

    @property
    def rows_out(self) -> int:
        """Linhas que seguem para validação."""
        return self.rows_in - self.rows_rejected - self.duplicates_dropped


@dataclass(frozen=True)
class EntityMetrics:
    """Volume processado de uma entidade em uma execução."""

    entity: str
    rows_read: int
    rows_rejected: int
    rows_written: int


@dataclass(frozen=True)
class RunReport:
    """Resultado da execução de uma sessão."""

    run_id: str
    session_key: int
    skipped: bool = False
    metrics: list[EntityMetrics] = field(default_factory=list)
