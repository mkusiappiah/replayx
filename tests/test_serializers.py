from __future__ import annotations

import httpx
import pytest

from replayx import Cassette, RecordMode
from replayx.serializers import JSONSerializer, serializer_for_path


def test_serializer_for_path_picks_json_by_default(tmp_path) -> None:
    assert isinstance(serializer_for_path(tmp_path / "c.json"), JSONSerializer)
    assert isinstance(serializer_for_path(tmp_path / "c.unknown"), JSONSerializer)


def test_yaml_cassette_roundtrip(tmp_path) -> None:
    pytest.importorskip("yaml")
    path = tmp_path / "c.yaml"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"hello": "world"})

    recorder = Cassette.load(path, record_mode=RecordMode.ONCE)
    with httpx.Client(
        transport=recorder.sync_transport(real=httpx.MockTransport(handler))
    ) as client:
        client.get("https://api.example.com/")
    recorder.save()
    assert path.exists()
    assert "interactions:" in path.read_text()

    player = Cassette.load(path, record_mode=RecordMode.NONE)
    assert len(player.interactions) == 1
