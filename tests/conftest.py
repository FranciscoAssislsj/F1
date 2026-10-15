"""Fixtures compartilhadas."""

import json
from pathlib import Path

import pytest

from f1.core.interfaces import Params, Record

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> list[Record]:
    """Lê uma amostra JSON de ``tests/fixtures``."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeClient:
    """Cliente em memória: devolve registros por endpoint e guarda as chamadas."""

    def __init__(self, data: dict[str, list[Record]]) -> None:
        self.data = data
        self.calls: list[tuple[str, Params | None]] = []

    def get(self, endpoint: str, params: Params | None = None) -> list[Record]:
        self.calls.append((endpoint, params))
        return list(self.data.get(endpoint, []))


@pytest.fixture
def api_data() -> dict[str, list[Record]]:
    """Dados de uma corrida (session_key=9000) a partir das fixtures."""
    names = [
        "meetings",
        "sessions",
        "drivers",
        "laps",
        "stints",
        "pit",
        "weather",
        "session_result",
    ]
    return {name: load_fixture(f"{name}.json") for name in names}


@pytest.fixture
def fake_client(api_data: dict[str, list[Record]]) -> FakeClient:
    return FakeClient(api_data)
