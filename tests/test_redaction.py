from __future__ import annotations

from dataclasses import replace

import httpx

from replayx import Cassette, RecordedResponse, RecordMode


def test_filter_headers_and_query(tmp_path) -> None:
    path = tmp_path / "c.json"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True}, headers={"set-cookie": "session=abc"})

    cassette = Cassette.load(
        path,
        record_mode=RecordMode.ONCE,
        filter_headers=["authorization", "set-cookie"],
        filter_query_params=["token"],
    )
    with httpx.Client(
        transport=cassette.sync_transport(real=httpx.MockTransport(handler))
    ) as client:
        resp = client.get(
            "https://api.example.com/data?token=supersecret&page=2",
            headers={"authorization": "Bearer XYZ"},
        )
        # The live response is untouched.
        assert resp.headers["set-cookie"] == "session=abc"
    cassette.save()

    text = path.read_text()
    assert "supersecret" not in text
    assert "Bearer XYZ" not in text
    assert "session=abc" not in text
    assert "REDACTED" in text
    assert "page=2" in text  # unrelated params survive


def test_before_record_response_hook_scrubs_body(tmp_path) -> None:
    path = tmp_path / "c.json"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"secret": "value"})

    def scrub(response: RecordedResponse) -> RecordedResponse:
        return replace(response, body=b'{"secret": "REDACTED"}')

    cassette = Cassette.load(path, record_mode=RecordMode.ONCE, before_record_response=scrub)
    with httpx.Client(
        transport=cassette.sync_transport(real=httpx.MockTransport(handler))
    ) as client:
        resp = client.get("https://api.example.com/")
        assert resp.json()["secret"] == "value"  # live response unaffected
    cassette.save()

    assert "value" not in path.read_text()


def test_before_record_request_can_skip(tmp_path) -> None:
    path = tmp_path / "c.json"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    cassette = Cassette.load(
        path,
        record_mode=RecordMode.ONCE,
        before_record_request=lambda request: None,  # skip every interaction
    )
    with httpx.Client(
        transport=cassette.sync_transport(real=httpx.MockTransport(handler))
    ) as client:
        assert client.get("https://api.example.com/skip").status_code == 204
    assert cassette.save() is False
    assert cassette.interactions == []
