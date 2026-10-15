"""Extração de entidades da OpenF1 (o que buscar, não como)."""

import time
from collections.abc import Callable
from datetime import date

from f1.core.interfaces import ApiClient, Params, Record
from f1.core.schemas import SESSION_ENTITIES
from f1.ingestion.retry import with_retry


class Extractor:
    """Consulta a API com retry para falhas transitórias."""

    def __init__(
        self,
        client: ApiClient,
        attempts: int = 5,
        base_delay_s: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._attempts = attempts
        self._base_delay_s = base_delay_s
        self._sleep = sleep

    def _get(self, endpoint: str, params: Params) -> list[Record]:
        return with_retry(
            lambda: self._client.get(endpoint, params),
            attempts=self._attempts,
            base_delay_s=self._base_delay_s,
            sleep=self._sleep,
        )

    def meetings(
        self, year: int, start: date | None = None, end: date | None = None
    ) -> list[Record]:
        """Fins de semana do ano, opcionalmente dentro da janela ``start``-``end``."""
        params: dict[str, object] = {"year": year}
        if start:
            params["date_start>="] = start.isoformat()
        if end:
            params["date_end<="] = f"{end.isoformat()}T23:59:59"
        return self._get("meetings", params)

    def meeting(self, meeting_key: int) -> list[Record]:
        """Um fim de semana pelo ``meeting_key``."""
        return self._get("meetings", {"meeting_key": meeting_key})

    def sessions_named(self, meeting_key: int, session_name: str) -> list[Record]:
        """Sessões de um fim de semana com o ``session_name`` dado (ex.: ``Race``)."""
        return self._get(
            "sessions", {"meeting_key": meeting_key, "session_name": session_name}
        )

    def session(self, session_key: int) -> list[Record]:
        """Uma sessão pelo ``session_key``."""
        return self._get("sessions", {"session_key": session_key})

    def session_entity(self, entity: str, session_key: int) -> list[Record]:
        """Registros de uma entidade de sessão (ver ``SESSION_ENTITIES``).

        Raises:
            ValueError: Se ``entity`` não for uma entidade de sessão conhecida.
        """
        if entity not in SESSION_ENTITIES:
            raise ValueError(f"Entidade desconhecida: {entity}")
        return self._get(entity, {"session_key": session_key})
