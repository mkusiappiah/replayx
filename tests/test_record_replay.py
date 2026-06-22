from __future__ import annotations

import json

import httpx
import pytest

from replayx import Cassette, RecordMode, UnhandledRequestError, use_cassette


def test_explicit_transport_record_then_replay(tmp_path, echo_handler, boom) -> None:
    path = tmp_path / "c.json"
    calls: list[str] = []
    real = httpx.MockTransport(echo_handler(calls))

    # Record.
    recorder = Cassette.load(path, record_mode=RecordMode.ONCE)
    with httpx.Client(transport=recorder.sync_transport(real=real)) as client:
        resp = client.get("https://api.example.com/users")
        assert resp.status_code == 200
        assert resp.json()["path"] == "/users"
    assert recorder.save() is True
    assert calls == ["GET /users"]

    payload = json.loads(path.read_text())
    assert len(payload["interactions"]) == 1

    # Replay — the network must not be touched.
    player = Cassette.load(path, record_mode=RecordMode.NONE)
    with httpx.Client(transport=player.sync_transport(real=httpx.MockTransport(boom))) as client:
        resp = client.get("https://api.example.com/users")
        assert resp.json()["path"] == "/users"


def test_replay_miss_raises(tmp_path, echo_handler, boom) -> None:
    path = tmp_path / "c.json"
    real = httpx.MockTransport(echo_handler([]))
    recorder = Cassette.load(path, record_mode=RecordMode.ONCE)
    with httpx.Client(transport=recorder.sync_transport(real=real)) as client:
        client.get("https://api.example.com/users")
    recorder.save()

    player = Cassette.load(path, record_mode=RecordMode.NONE)
    with httpx.Client(transport=player.sync_transport(real=httpx.MockTransport(boom))) as client:
        with pytest.raises(UnhandledRequestError):
            client.get("https://api.example.com/not-recorded")


def test_use_cassette_patches_httpx(tmp_path, echo_handler, boom) -> None:
    path = tmp_path / "c.json"
    calls: list[str] = []
    real = httpx.MockTransport(echo_handler(calls))

    with use_cassette(path, record_mode="once", real_sync_transport=real):
        with httpx.Client() as client:  # no transport injected — interception is automatic
            resp = client.get("https://api.example.com/ping")
            assert resp.json()["path"] == "/ping"
    assert path.exists()
    assert calls == ["GET /ping"]

    with use_cassette(path, record_mode="none", real_sync_transport=httpx.MockTransport(boom)):
        with httpx.Client() as client:
            resp = client.get("https://api.example.com/ping")
            assert resp.json()["ok"] is True


def test_httpx_is_unpatched_after_block(tmp_path, echo_handler) -> None:
    original = httpx.Client._transport_for_url
    with use_cassette(
        tmp_path / "c.json",
        record_mode="all",
        real_sync_transport=httpx.MockTransport(echo_handler([])),
    ):
        with httpx.Client() as client:
            client.get("https://api.example.com/x")
    assert httpx.Client._transport_for_url is original


async def test_async_record_then_replay(tmp_path, echo_handler, boom) -> None:
    path = tmp_path / "c.json"
    calls: list[str] = []
    recorder = Cassette.load(path, record_mode=RecordMode.ONCE)
    real = httpx.MockTransport(echo_handler(calls))
    async with httpx.AsyncClient(transport=recorder.async_transport(real=real)) as client:
        resp = await client.get("https://api.example.com/async")
        assert resp.json()["path"] == "/async"
    recorder.save()
    assert calls == ["GET /async"]

    player = Cassette.load(path, record_mode=RecordMode.NONE)
    async with httpx.AsyncClient(
        transport=player.async_transport(real=httpx.MockTransport(boom))
    ) as client:
        resp = await client.get("https://api.example.com/async")
        assert resp.json()["path"] == "/async"


def test_new_episodes_appends(tmp_path, echo_handler) -> None:
    path = tmp_path / "c.json"
    calls: list[str] = []
    real = httpx.MockTransport(echo_handler(calls))

    first = Cassette.load(path, record_mode=RecordMode.ONCE)
    with httpx.Client(transport=first.sync_transport(real=real)) as client:
        client.get("https://api.example.com/a")
    first.save()

    second = Cassette.load(path, record_mode=RecordMode.NEW_EPISODES)
    with httpx.Client(transport=second.sync_transport(real=real)) as client:
        client.get("https://api.example.com/a")  # replayed
        client.get("https://api.example.com/b")  # newly recorded
    second.save()

    payload = json.loads(path.read_text())
    urls = {item["request"]["url"] for item in payload["interactions"]}
    assert urls == {"https://api.example.com/a", "https://api.example.com/b"}
    # Only /b should have hit the backend during the second pass.
    assert calls == ["GET /a", "GET /b"]
