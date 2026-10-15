"""Configuração centralizada, lida de variáveis de ambiente."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Parâmetros de execução do pipeline.

    Attributes:
        base_url: URL base da API OpenF1.
        api_timeout_s: Timeout, em segundos, de cada chamada HTTP.
        rate_limit_delay_s: Pausa, em segundos, antes de cada chamada.
        data_dir: Diretório raiz onde os Parquet são gravados.
    """

    base_url: str = "https://api.openf1.org/v1"
    api_timeout_s: float = 30.0
    rate_limit_delay_s: float = 2.0
    data_dir: Path = Path("data")

    @classmethod
    def from_env(cls) -> "Settings":
        """Constrói as configurações a partir do ambiente.

        Raises:
            ValueError: Se algum valor numérico for inválido ou fora do intervalo.
        """
        defaults = cls()
        try:
            settings = cls(
                base_url=os.getenv("OPENF1_BASE_URL", defaults.base_url).rstrip("/"),
                api_timeout_s=float(
                    os.getenv("API_TIMEOUT_S", str(defaults.api_timeout_s))
                ),
                rate_limit_delay_s=float(
                    os.getenv("RATE_LIMIT_DELAY_S", str(defaults.rate_limit_delay_s))
                ),
                data_dir=Path(os.getenv("DATA_DIR", str(defaults.data_dir))),
            )
        except ValueError as exc:
            raise ValueError(f"Valor numérico inválido na configuração: {exc}") from exc
        if settings.api_timeout_s <= 0 or settings.rate_limit_delay_s < 0:
            raise ValueError("API_TIMEOUT_S deve ser > 0 e RATE_LIMIT_DELAY_S >= 0")
        return settings
