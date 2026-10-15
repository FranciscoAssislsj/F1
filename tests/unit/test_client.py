import pytest
import requests
import responses

from f1.core.exceptions import PermanentApiError, TransientApiError
from f1.integrations.openf1_client import OpenF1Client, build_query

BASE = "https://api.test/v1"


def make_client(delays: list[float] | None = None) -> OpenF1Client:
    sink = delays if delays is not None else []
    return OpenF1Client(BASE, 5.0, rate_limit_delay_s=0.2, sleep=sink.append)


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        (None, ""),
        ({"session_key": 9158}, "session_key=9158"),
        ({"driver_number": [4, 81]}, "driver_number=4&driver_number=81"),
        ({"lap_duration>=": 120}, "lap_duration>=120"),
        ({"date<": "2021-09-10T14:30:20+00:00"}, "date<2021-09-10T14:30:20%2B00:00"),
        ({"is_pit_out_lap": True}, "is_pit_out_lap=true"),
        ({"session_name": "Sprint Qualifying"}, "session_name=Sprint%20Qualifying"),
    ],
)
def test_build_query(params: dict | None, expected: str) -> None:
    assert build_query(params) == expected


@responses.activate
def test_get_success_applies_delay() -> None:
    responses.get(f"{BASE}/laps", json=[{"a": 1}])
    delays: list[float] = []
    assert make_client(delays).get("laps", {"session_key": 1}) == [{"a": 1}]
    assert delays == [0.2]
    assert responses.calls[0].request.url == f"{BASE}/laps?session_key=1"


@responses.activate
def test_get_sends_operator_filter() -> None:
    responses.get(f"{BASE}/meetings", json=[])
    make_client().get("meetings", {"date_start>=": "2024-01-01"})
    assert responses.calls[0].request.url.endswith("meetings?date_start%3E=2024-01-01")


@responses.activate
@pytest.mark.parametrize("status", [429, 500, 503])
def test_transient_statuses(status: int) -> None:
    responses.get(f"{BASE}/laps", status=status)
    with pytest.raises(TransientApiError):
        make_client().get("laps")


@responses.activate
def test_404_no_results_is_empty_list() -> None:
    responses.get(f"{BASE}/laps", status=404, json={"detail": "No results found."})
    assert make_client().get("laps") == []


@responses.activate
@pytest.mark.parametrize("status", [400, 401, 404])
def test_permanent_statuses(status: int) -> None:
    responses.get(f"{BASE}/laps", status=status, json={"detail": "x"})
    with pytest.raises(PermanentApiError):
        make_client().get("laps")


@responses.activate
@pytest.mark.parametrize(
    "error", [requests.Timeout("t"), requests.ConnectionError("c")]
)
def test_network_errors_are_transient(error: Exception) -> None:
    responses.get(f"{BASE}/laps", body=error)
    with pytest.raises(TransientApiError):
        make_client().get("laps")


@responses.activate
def test_non_json_body_is_permanent() -> None:
    responses.get(f"{BASE}/laps", body="<html>")
    with pytest.raises(PermanentApiError):
        make_client().get("laps")


@responses.activate
def test_non_list_json_is_permanent() -> None:
    responses.get(f"{BASE}/laps", json={"detail": "x"})
    with pytest.raises(PermanentApiError):
        make_client().get("laps")


@responses.activate
def test_timeout_is_passed_to_session() -> None:
    responses.get(f"{BASE}/laps", json=[])
    make_client().get("laps")
    assert responses.calls[0].request.req_kwargs["timeout"] == 5.0
