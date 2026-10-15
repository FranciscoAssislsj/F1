"""Exceções do domínio do pipeline."""


class TransientApiError(RuntimeError):
    """Falha temporária da API (timeout, 429, 5xx); pode ser repetida."""


class PermanentApiError(RuntimeError):
    """Falha definitiva da API (4xx, resposta inválida); não deve ser repetida."""


class SchemaValidationError(ValueError):
    """Os dados não respeitam o schema esperado."""
