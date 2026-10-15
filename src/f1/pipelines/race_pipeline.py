"""Orquestração: ingestão -> transformação -> validação -> carga de sessões."""

import logging
import time
from collections.abc import Sequence
from datetime import date

from f1.core.exceptions import (
    PermanentApiError,
    SchemaValidationError,
    TransientApiError,
)
from f1.core.interfaces import Record, Sink
from f1.core.models import EntityMetrics, RunReport
from f1.core.schemas import SCHEMAS, SESSION_ENTITIES
from f1.ingestion.extractors import Extractor
from f1.transformation.entities import transform
from f1.validation.checks import validate

logger = logging.getLogger(__name__)

DEFAULT_SESSION_NAMES = ("Race", "Qualifying")

_RECOVERABLE = (TransientApiError, PermanentApiError, SchemaValidationError)


def process_entity(
    entity: str,
    records: list[Record],
    sink: Sink,
    partition: str,
    run_id: str,
) -> EntityMetrics:
    """Transforma, valida e grava os registros de uma entidade.

    Raises:
        SchemaValidationError: Se o resultado violar o schema (nada é gravado).
    """
    df, stats = transform(entity, records)
    validate(df, SCHEMAS[entity])
    sink.write(entity, partition, df)
    logger.info(
        "etapa concluída",
        extra={
            "run_id": run_id,
            "step": "load",
            "entity": entity,
            "partition": partition,
            "rows_in": stats.rows_in,
            "rows_rejected": stats.rows_rejected,
            "duplicates_dropped": stats.duplicates_dropped,
            "values_coerced": stats.values_coerced,
            "rows_out": len(df),
        },
    )
    return EntityMetrics(entity, stats.rows_in, stats.rows_rejected, len(df))


def run_session(
    session: Record,
    meeting: Record,
    extractor: Extractor,
    sink: Sink,
    run_id: str,
    skip_existing: bool = False,
) -> RunReport:
    """Processa uma sessão de corrida e seu fim de semana.

    Reexecutar sobrescreve as partições da sessão (idempotente). Com
    ``skip_existing``, sessões já concluídas são puladas.
    """
    session_key = int(session["session_key"])
    meeting_key = int(session["meeting_key"])
    session_part = f"session_key={session_key}"
    meeting_part = f"meeting_key={meeting_key}"
    started = time.monotonic()
    if skip_existing and sink.exists(SESSION_ENTITIES[-1], session_part):
        logger.info(
            "sessão já concluída; pulando",
            extra={"run_id": run_id, "session_key": session_key},
        )
        return RunReport(run_id, session_key, skipped=True)

    metrics = [
        process_entity("meetings", [meeting], sink, meeting_part, run_id),
        process_entity("sessions", [session], sink, session_part, run_id),
    ]
    for entity in SESSION_ENTITIES:
        records = extractor.session_entity(entity, session_key)
        metrics.append(process_entity(entity, records, sink, session_part, run_id))
    logger.info(
        "sessão concluída",
        extra={
            "run_id": run_id,
            "session_key": session_key,
            "duration_s": round(time.monotonic() - started, 3),
            "rows_written": sum(m.rows_written for m in metrics),
        },
    )
    return RunReport(run_id, session_key, metrics=metrics)


def run_session_key(
    session_key: int,
    extractor: Extractor,
    sink: Sink,
    run_id: str,
    skip_existing: bool = False,
) -> RunReport:
    """Processa uma sessão a partir do ``session_key``.

    Raises:
        PermanentApiError: Se a sessão ou o fim de semana não forem encontrados.
    """
    sessions = extractor.session(session_key)
    if not sessions:
        raise PermanentApiError(f"Sessão {session_key} não encontrada")
    meetings = extractor.meeting(int(sessions[0]["meeting_key"]))
    if not meetings:
        raise PermanentApiError(f"Fim de semana da sessão {session_key} não encontrado")
    return run_session(sessions[0], meetings[0], extractor, sink, run_id, skip_existing)


def run_year(
    year: int,
    extractor: Extractor,
    sink: Sink,
    run_id: str,
    start: date | None = None,
    end: date | None = None,
    skip_existing: bool = False,
    session_names: Sequence[str] = DEFAULT_SESSION_NAMES,
) -> tuple[list[RunReport], list[int]]:
    """Processa as sessões de ``session_names`` de um ano (ou janela ``start``-``end``).

    Uma sessão que falhe é registrada e não impede as demais.

    Returns:
        Os relatórios das sessões concluídas e os ``session_key`` que falharam.
    """
    reports: list[RunReport] = []
    failed: list[int] = []
    for meeting in extractor.meetings(year, start, end):
        if meeting.get("is_cancelled"):
            continue
        for session_name in session_names:
            sessions = extractor.sessions_named(
                int(meeting["meeting_key"]), session_name
            )
            for session in sessions:
                try:
                    reports.append(
                        run_session(
                            session, meeting, extractor, sink, run_id, skip_existing
                        )
                    )
                except _RECOVERABLE:
                    logger.exception(
                        "falha ao processar sessão",
                        extra={
                            "run_id": run_id,
                            "session_key": session["session_key"],
                        },
                    )
                    failed.append(int(session["session_key"]))
    return reports, failed
