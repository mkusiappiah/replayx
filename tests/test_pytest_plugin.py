from __future__ import annotations

import httpx


def test_plugin_fixture_records_and_replays(replayx_cassette, tmp_path, echo_handler, boom) -> None:
    calls: list[str] = []
    real = httpx.MockTransport(echo_handler(calls))
    path = tmp_path / "plugin.json"

    with replayx_cassette(path, record_mode="once", real_sync_transport=real):
        with httpx.Client() as client:
            resp = client.get("https://api.example.com/plugin")
            assert resp.json()["path"] == "/plugin"
    assert path.exists()
    assert calls == ["GET /plugin"]

    with replayx_cassette(path, record_mode="none", real_sync_transport=httpx.MockTransport(boom)):
        with httpx.Client() as client:
            resp = client.get("https://api.example.com/plugin")
            assert resp.json()["ok"] is True


def test_plugin_default_path_uses_test_name(replayx_cassette) -> None:
    # With no requests made, "none" mode just opens and closes cleanly. The
    # default cassette path is derived from the test's directory and name.
    with replayx_cassette(record_mode="none") as cassette:
        assert cassette.path.name == "test_plugin_default_path_uses_test_name.json"
        assert cassette.path.parent.name == "cassettes"
