"""Testes contra a API OpenF1 real; fora do gate padrão do CI."""

import pytest

from f1.config.settings import Settings
from f1.ingestion.extractors import Extractor
from f1.integrations.openf1_client import OpenF1Client

pytestmark = pytest.mark.integration


@pytest.fixture
def extractor() -> Extractor:
    return Extractor(OpenF1Client.from_settings(Settings.from_env()))


def test_meetings_and_race_session(extractor: Extractor) -> None:
    meetings = extractor.meetings(2024)
    assert meetings
    sessions = [
        s
        for m in meetings
        for s in extractor.sessions_named(int(m["meeting_key"]), "Race")
    ]
    assert sessions and all(s["session_name"] == "Race" for s in sessions)


def test_unknown_session_returns_empty(extractor: Extractor) -> None:
    assert extractor.session(1) == []
