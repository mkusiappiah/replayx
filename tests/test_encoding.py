from __future__ import annotations

import gzip
import json
import zlib

import httpx
import pytest

from replayx import Cassette, RecordMode
from replayx.encoding import encode_content


@pytest.mark.parametrize("encoding", ["gzip", "deflate"])
def test_record_keeps_decoded_body_and_replays_with_encoding(tmp_path, boom, encoding) -> None:
    path = tmp_path / "c.json"
    payload = {"hello": "world", "n": 42}
    decoded = json.dumps(payload).encode()
    encoded = encode_content(decoded, encoding)
    assert encoded is not None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-encoding": encoding, "content-type": "application/json"},
            content=encoded,
        )

    recorder = Cassette.load(path, record_mode=RecordMode.ONCE)
    with httpx.Client(
        transport=recorder.sync_transport(real=httpx.MockTransport(handler))
    ) as client:
        resp = client.get("https://api.example.com/data")
        assert resp.json() == payload
        assert resp.headers["content-encoding"] == encoding
    recorder.save()

    # The cassette stores the decoded body, so it reads cleanly.
    text = path.read_text()
    assert "hello" in text
    assert "content-encoding" in text.lower()

    # Replay reproduces both the body and the content-encoding header.
    player = Cassette.load(path, record_mode=RecordMode.NONE)
    with httpx.Client(transport=player.sync_transport(real=httpx.MockTransport(boom))) as client:
        resp = client.get("https://api.example.com/data")
        assert resp.json() == payload
        assert resp.headers["content-encoding"] == encoding


def test_unknown_encoding_degrades_gracefully(tmp_path, boom) -> None:
    path = tmp_path / "c.json"

    def handler(request: httpx.Request) -> httpx.Response:
        # httpx leaves an unknown content-encoding undecoded, so the body
        # stays as the raw bytes we send here.
        return httpx.Response(
            200,
            headers={"content-encoding": "made-up-codec"},
            content=b"plain-bytes",
        )

    recorder = Cassette.load(path, record_mode=RecordMode.ONCE)
    with httpx.Client(
        transport=recorder.sync_transport(real=httpx.MockTransport(handler))
    ) as client:
        client.get("https://api.example.com/x")
    recorder.save()

    player = Cassette.load(path, record_mode=RecordMode.NONE)
    with httpx.Client(transport=player.sync_transport(real=httpx.MockTransport(boom))) as client:
        resp = client.get("https://api.example.com/x")
        assert resp.content == b"plain-bytes"
        assert "content-encoding" not in resp.headers


def test_plain_response_still_works(tmp_path, boom) -> None:
    path = tmp_path / "c.json"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    recorder = Cassette.load(path, record_mode=RecordMode.ONCE)
    with httpx.Client(
        transport=recorder.sync_transport(real=httpx.MockTransport(handler))
    ) as client:
        client.get("https://api.example.com/plain")
    recorder.save()

    player = Cassette.load(path, record_mode=RecordMode.NONE)
    with httpx.Client(transport=player.sync_transport(real=httpx.MockTransport(boom))) as client:
        resp = client.get("https://api.example.com/plain")
        assert resp.json() == {"ok": True}
        assert "content-encoding" not in resp.headers


def test_encode_content_units() -> None:
    assert encode_content(b"abc", "identity") == b"abc"
    assert encode_content(b"abc", "") == b"abc"
    assert gzip.decompress(encode_content(b"abc", "gzip")) == b"abc"
    assert zlib.decompress(encode_content(b"abc", "deflate")) == b"abc"
    assert encode_content(b"abc", "made-up-codec") is None
