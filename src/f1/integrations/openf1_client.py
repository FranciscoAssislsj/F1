"""Cliente HTTP da API OpenF1."""

import logging
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import requests

from f1.config.settings import Settings
from f1.core.exceptions import PermanentApiError, TransientApiError
from f1.core.interfaces import Params, Record

logger = logging.getLogger(__name__)

OPERATORS = (">=", "<=", ">", "<")
NO_RESULTS = "No results found"  # a OpenF1 responde 404 quando o filtro não casa


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return quote(str(value), safe=":")


def _parse_retry_after(value: str | None) -> float | None:
    """Converte ``Retry-After`` em segundos (só o formato numérico)."""
    try:
        return max(float(value), 0.0) if value else None
    except ValueError:
        return None


def build_query(params: Params | None) -> str:
    """Monta a query string no formato aceito pela OpenF1.

    Chaves terminadas em operador (``date>=``) viram ``date>=valor``; as demais
    viram ``chave=valor``. Valores em lista geram parâmetros repetidos.
    """
    parts: list[str] = []
    for key, raw in (params or {}).items():
        values = raw if isinstance(raw, list | tuple) else [raw]
        for value in values:
            separator = "" if key.endswith(OPERATORS) else "="
            parts.append(f"{key}{separator}{_format_value(value)}")
    return "&".join(parts)


class OpenF1Client:
    """Cliente de leitura da OpenF1 com timeout e erros classificados."""

    def __init__(
        self,
        base_url: str,
        timeout_s: float,
        rate_limit_delay_s: float = 0.0,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._delay_s = rate_limit_delay_s
        self._session = session or requests.Session()
        self._sleep = sleep

    @classmethod
    def from_settings(cls, settings: Settings) -> "OpenF1Client":
        """Cria o cliente a partir das configurações."""
        return cls(
            settings.base_url, settings.api_timeout_s, settings.rate_limit_delay_s
        )

    def get(self, endpoint: str, params: Params | None = None) -> list[Record]:
        """Consulta um endpoint e retorna a lista de registros.

        Raises:
            TransientApiError: Timeout, erro de conexão, 429 ou 5xx.
            PermanentApiError: Demais 4xx ou corpo que não seja uma lista JSON.
                Um 404 "sem resultados" não é erro: retorna ``[]``.
        """
        url = f"{self._base_url}/{endpoint}"
        query = build_query(params)
        if query:
            url = f"{url}?{query}"
        if self._delay_s:
            self._sleep(self._delay_s)
        try:
            response = self._session.get(url, timeout=self._timeout_s)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise TransientApiError(f"Falha de rede em {endpoint}: {exc}") from exc
        status = response.status_code
        if status == 429 or status >= 500:
            raise TransientApiError(
                f"HTTP {status} em {endpoint}",
                retry_after_s=_parse_retry_after(response.headers.get("Retry-After")),
            )
        if status == 404 and NO_RESULTS in response.text:
            return []
        if status >= 400:
            raise PermanentApiError(
                f"HTTP {status} em {endpoint}: {response.text[:200]}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise PermanentApiError(f"Resposta não é JSON em {endpoint}") from exc
        if not isinstance(data, list):
            raise PermanentApiError(f"Resposta inesperada em {endpoint}: {type(data)}")
        logger.debug(
            "consulta concluída", extra={"endpoint": endpoint, "rows": len(data)}
        )
        return data
