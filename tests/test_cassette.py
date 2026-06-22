from __future__ import annotations

import json

import pytest

from replayx import Cassette, RecordedRequest, RecordedResponse, RecordMode
from replayx.cassette import Interaction, decode_body, encode_body
from replayx.errors import CassetteFormatError


@pytest.mark.parametrize(
    "raw",
    [b"", b"hello world", "café".encode(), bytes(range(256))],
)
def test_body_encode_roundtrip(raw: bytes) -> None:
    assert decode_body(encode_body(raw)) == raw


def test_empty_body_encodes_to_none() -> None:
    assert encode_body(b"") is None
    assert decode_body(None) == b""


def test_binary_body_uses_base64() -> None:
    encoded = encode_body(bytes([0, 1, 2, 255]))
    assert encoded is not None and "base64" in encoded


def test_decode_body_rejects_unknown_shape() -> None:
    with pytest.raises(CassetteFormatError):
        decode_body({"nope": "x"})


def test_interaction_dict_roundtrip() -> None:
    interaction = Interaction(
        request=RecordedRequest("GET", "https://x.test/a", [("accept", "*/*")], b""),
        response=RecordedResponse(200, [("content-type", "application/json")], b"{}"),
    )
    restored = Interaction.from_dict(interaction.to_dict())
    assert restored == interaction


def test_load_missing_file_starts_empty(tmp_path) -> None:
    cassette = Cassette.load(tmp_path / "new.json", record_mode=RecordMode.ONCE)
    assert cassette.interactions == []
    assert cassette.allow_record is True
    assert cassette.allow_replay is True


def test_save_only_when_dirty(tmp_path) -> None:
    path = tmp_path / "c.json"
    cassette = Cassette.load(path, record_mode=RecordMode.ONCE)
    assert cassette.save() is False
    assert not path.exists()

    cassette.record(
        RecordedRequest("GET", "https://x.test/"),
        RecordedResponse(200, body=b"hi"),
    )
    assert cassette.save() is True
    assert path.exists()
    payload = json.loads(path.read_text())
    assert payload["version"] == 1
    assert payload["recorded_with"].startswith("replayx/")
    assert len(payload["interactions"]) == 1


def test_none_mode_never_records(tmp_path) -> None:
    cassette = Cassette.load(tmp_path / "c.json", record_mode=RecordMode.NONE)
    assert cassette.allow_record is False
    assert cassette.allow_replay is True


def test_all_mode_ignores_existing(tmp_path) -> None:
    path = tmp_path / "c.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "interactions": [
                    {
                        "request": {
                            "method": "GET",
                            "url": "https://x.test/",
                            "headers": [],
                            "body": None,
                        },
                        "response": {"status_code": 200, "headers": [], "body": None},
                    }
                ],
            }
        )
    )
    cassette = Cassette.load(path, record_mode=RecordMode.ALL)
    assert cassette.interactions == []
    assert cassette.allow_replay is False
    assert cassette.allow_record is True


def test_invalid_json_raises(tmp_path) -> None:
    path = tmp_path / "c.json"
    path.write_text("{not json")
    with pytest.raises(CassetteFormatError):
        Cassette.load(path, record_mode=RecordMode.ONCE)
