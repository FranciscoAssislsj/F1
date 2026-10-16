"""Exceções do domínio do pipeline."""


class TransientApiError(RuntimeError):
    """Falha temporária da API (timeout, 429, 5xx); pode ser repetida.

    Attributes:
        retry_after_s: Espera mínima pedida pela API (cabeçalho ``Retry-After``).
    """

    def __init__(self, message: str, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class PermanentApiError(RuntimeError):
    """Falha definitiva da API (4xx, resposta inválida); não deve ser repetida."""


class SchemaValidationError(ValueError):
    """Os dados não respeitam o schema esperado."""
