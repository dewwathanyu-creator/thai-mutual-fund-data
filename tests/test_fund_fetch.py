"""ตรวจการลองใหม่โดยไม่ยิง API จริง โดยเฉพาะกฎหยุดเมื่อ 429 ซ้ำ"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fund_fetch  # noqa: E402


class FakeClient:
    delay = 0.5

    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0

    def get(self, path, params, retries, raise_network):
        assert retries == 0 and raise_network is True
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(status_code=outcome, headers={})


def test_timeout_retries_without_counting_response(monkeypatch):
    monkeypatch.setattr(fund_fetch.time, "sleep", lambda _: None)
    client = FakeClient([requests.Timeout(), 200])
    state = fund_fetch.new_state()
    response = fund_fetch._get(client, "/test", {}, state)
    assert response.status_code == 200
    assert client.calls == 2
    assert state["calls"] == 2


def test_repeated_429_stops_after_two_responses(monkeypatch):
    monkeypatch.setattr(fund_fetch.time, "sleep", lambda _: None)
    client = FakeClient([429, 429, 200])
    state = fund_fetch.new_state()
    with pytest.raises(fund_fetch.RateLimited):
        fund_fetch._get(client, "/test", {}, state)
    assert client.calls == 2
    assert state["n429"] == 2


def test_repeated_timeout_stops_after_three_attempts(monkeypatch):
    monkeypatch.setattr(fund_fetch.time, "sleep", lambda _: None)
    client = FakeClient([requests.Timeout(), requests.Timeout(), requests.Timeout()])
    with pytest.raises(fund_fetch.NetworkError):
        fund_fetch._get(client, "/test", {}, fund_fetch.new_state())
    assert client.calls == 3
