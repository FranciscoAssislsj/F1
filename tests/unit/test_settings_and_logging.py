import json
import logging
from pathlib import Path

import pytest

from f1.config.settings import Settings
from f1.utils.logging import JsonFormatter, new_run_id


def test_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("OPENF1_BASE_URL", "API_TIMEOUT_S", "RATE_LIMIT_DELAY_S", "DATA_DIR"):
        monkeypatch.delenv(var, raising=False)
    assert Settings.from_env() == Settings()


def test_from_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENF1_BASE_URL", "http://x/v1/")
    monkeypatch.setenv("API_TIMEOUT_S", "5")
    monkeypatch.setenv("RATE_LIMIT_DELAY_S", "0")
    monkeypatch.setenv("DATA_DIR", "out")
    settings = Settings.from_env()
    assert settings == Settings("http://x/v1", 5.0, 0.0, Path("out"))


@pytest.mark.parametrize(
    ("var", "value"),
    [
        ("API_TIMEOUT_S", "abc"),
        ("API_TIMEOUT_S", "0"),
        ("RATE_LIMIT_DELAY_S", "-1"),
    ],
)
def test_from_env_invalid(
    monkeypatch: pytest.MonkeyPatch, var: str, value: str
) -> None:
    monkeypatch.setenv(var, value)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_new_run_id_is_unique() -> None:
    assert new_run_id() != new_run_id()


def test_json_formatter_includes_extra() -> None:
    record = logging.LogRecord("n", logging.INFO, "f", 1, "oi %s", ("x",), None)
    record.run_id = "abc"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "oi x"
    assert payload["run_id"] == "abc"
    assert payload["level"] == "INFO"
