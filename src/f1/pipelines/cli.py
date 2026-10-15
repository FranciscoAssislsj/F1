"""Linha de comando: ``python -m f1.pipelines.cli --year 2024``."""

import argparse
import logging
import sys
import time
from collections.abc import Sequence
from datetime import date

from f1.config.settings import Settings
from f1.core.exceptions import (
    PermanentApiError,
    SchemaValidationError,
    TransientApiError,
)
from f1.core.interfaces import Sink
from f1.ingestion.extractors import Extractor
from f1.integrations.openf1_client import OpenF1Client
from f1.integrations.parquet_sink import ParquetSink
from f1.pipelines.race_pipeline import (
    DEFAULT_SESSION_NAMES,
    FIRST_YEAR,
    run_session_key,
    run_years,
)
from f1.utils.logging import configure_logging, new_run_id

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos."""
    parser = argparse.ArgumentParser(description="Pipeline de corridas da OpenF1")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--year", type=int, action="append", help="Ano a processar (repetível)"
    )
    target.add_argument(
        "--all-years",
        action="store_true",
        help=f"Todos os anos disponíveis, de {FIRST_YEAR} até o atual",
    )
    target.add_argument("--session-key", type=int, help="Uma sessão específica")
    parser.add_argument("--start", type=date.fromisoformat, help="Início (AAAA-MM-DD)")
    parser.add_argument("--end", type=date.fromisoformat, help="Fim (AAAA-MM-DD)")
    parser.add_argument(
        "--session-name",
        action="append",
        dest="session_names",
        help="Tipo de sessão com --year (repetível; padrão: Race e Qualifying)",
    )
    parser.add_argument(
        "--skip-existing", action="store_true", help="Pula sessões já concluídas"
    )
    return parser


BAR_WIDTH = 30


def show_progress(done: int, total: int, label: str) -> None:
    """Barra de progresso em stderr (só em terminal interativo)."""
    if not sys.stderr.isatty():
        return
    filled = BAR_WIDTH * done // total if total else BAR_WIDTH
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    pct = 100 * done // total if total else 100
    sys.stderr.write(f"\r\x1b[K[{bar}] {pct:3d}% {done}/{total} {label}")
    sys.stderr.write("\n" if done == total else "")
    sys.stderr.flush()


def main(
    argv: Sequence[str] | None = None,
    extractor: Extractor | None = None,
    sink: Sink | None = None,
) -> int:
    """Executa o pipeline; retorna 0 em sucesso e 1 se houve falhas."""
    args = build_parser().parse_args(argv)
    if (args.start or args.end) and not args.year:
        build_parser().error("--start/--end exigem --year")
    configure_logging()
    settings = Settings.from_env()
    extractor = extractor or Extractor(OpenF1Client.from_settings(settings))
    sink = sink or ParquetSink(settings.data_dir)
    run_id = new_run_id()
    started = time.monotonic()
    logger.info("execução iniciada", extra={"run_id": run_id, "cli_args": vars(args)})
    try:
        if args.session_key is not None:
            reports = [
                run_session_key(
                    args.session_key, extractor, sink, run_id, args.skip_existing
                )
            ]
            failed: list[int] = []
        else:
            years = args.year or list(range(FIRST_YEAR, date.today().year + 1))
            reports, failed = run_years(
                years,
                extractor,
                sink,
                run_id,
                args.start,
                args.end,
                args.skip_existing,
                args.session_names or DEFAULT_SESSION_NAMES,
                show_progress,
            )
    except (TransientApiError, PermanentApiError, SchemaValidationError):
        logger.exception("execução abortada", extra={"run_id": run_id})
        return 1
    logger.info(
        "execução finalizada",
        extra={
            "run_id": run_id,
            "duration_s": round(time.monotonic() - started, 3),
            "sessions_ok": len(reports),
            "sessions_failed": failed,
        },
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
