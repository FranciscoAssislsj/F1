"""Retry com backoff exponencial para falhas transitórias."""

import logging
import time
from collections.abc import Callable

from f1.core.exceptions import TransientApiError

logger = logging.getLogger(__name__)


def with_retry[T](
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay_s: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Executa ``fn`` repetindo apenas em ``TransientApiError``.

    Erros permanentes e quaisquer outras exceções propagam imediatamente.

    Raises:
        TransientApiError: Se todas as tentativas falharem.
        ValueError: Se ``attempts`` for menor que 1.
    """
    if attempts < 1:
        raise ValueError("attempts deve ser >= 1")
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except TransientApiError as exc:
            if attempt == attempts:
                raise
            delay = max(base_delay_s * 2 ** (attempt - 1), exc.retry_after_s or 0.0)
            logger.warning(
                "falha transitória; nova tentativa: %s (espera %.1fs)",
                exc,
                delay,
                extra={"attempt": attempt, "delay_s": delay},
            )
            sleep(delay)
    raise AssertionError("inalcançável")  # pragma: no cover
