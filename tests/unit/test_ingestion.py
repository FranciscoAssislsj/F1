from datetime import date

import pytest

from f1.core.exceptions import PermanentApiError, TransientApiError
from f1.ingestion.extractors import Extractor
from f1.ingestion.retry import with_retry
from tests.conftest import FakeClient


def test_retry_succeeds_after_transient_failures() -> None:
    delays: list[float] = []
    outcomes = [TransientApiError("a"), TransientApiError("b"), "ok"]

    def fn() -> str:
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    assert with_retry(fn, attempts=3, base_delay_s=1.0, sleep=delays.append) == "ok"
    assert delays == [1.0, 2.0]


def test_retry_gives_up_after_attempts() -> None:
    calls: list[int] = []

    def fn() -> None:
        calls.append(1)
        raise TransientApiError("x")

    with pytest.raises(TransientApiError):
        with_retry(fn, attempts=3, sleep=lambda _: None)
    assert len(calls) == 3


def test_retry_does_not_retry_permanent_errors() -> None:
    calls: list[int] = []

    def fn() -> None:
        calls.append(1)
        raise PermanentApiError("404")

    with pytest.raises(PermanentApiError):
        with_retry(fn, attempts=3, sleep=lambda _: None)
    assert len(calls) == 1


def test_retry_rejects_invalid_attempts() -> None:
    with pytest.raises(ValueError):
        with_retry(lambda: 1, attempts=0)


def test_extractor_queries(fake_client: FakeClient) -> None:
    extractor = Extractor(fake_client, sleep=lambda _: None)
    extractor.meetings(2024, date(2024, 1, 1), date(2024, 12, 31))
    extractor.meetings(2024)
    extractor.meeting(1200)
    extractor.sessions_named(1200, "Race")
    extractor.session(9000)
    extractor.session_entity("laps", 9000)
    assert fake_client.calls == [
        (
            "meetings",
            {
                "year": 2024,
                "date_start>=": "2024-01-01",
                "date_end<=": "2024-12-31T23:59:59",
            },
        ),
        ("meetings", {"year": 2024}),
        ("meetings", {"meeting_key": 1200}),
        ("sessions", {"meeting_key": 1200, "session_name": "Race"}),
        ("sessions", {"session_key": 9000}),
        ("laps", {"session_key": 9000}),
    ]


def test_extractor_rejects_unknown_entity(fake_client: FakeClient) -> None:
    with pytest.raises(ValueError):
        Extractor(fake_client).session_entity("car_data", 1)


def test_extractor_retries_transient_failures() -> None:
    class Flaky:
        def __init__(self) -> None:
            self.calls = 0

        def get(self, endpoint: str, params: object = None) -> list[dict]:
            self.calls += 1
            if self.calls == 1:
                raise TransientApiError("503")
            return [{"ok": True}]

    flaky = Flaky()
    extractor = Extractor(flaky, base_delay_s=0, sleep=lambda _: None)
    assert extractor.session(1) == [{"ok": True}]
    assert flaky.calls == 2
