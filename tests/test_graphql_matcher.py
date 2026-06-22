from __future__ import annotations

import json

import httpx

from replayx import Cassette, RecordedRequest, RecordMode
from replayx.matchers import build_matchers


def gql(
    query: str, *, operation: str | None = None, variables: dict | None = None
) -> RecordedRequest:
    payload: dict = {"query": query}
    if operation is not None:
        payload["operationName"] = operation
    if variables is not None:
        payload["variables"] = variables
    return RecordedRequest(
        "POST", "https://api.example.com/graphql", [], json.dumps(payload).encode()
    )


def matches(a: RecordedRequest, b: RecordedRequest) -> bool:
    return all(m(a, b) for m in build_matchers(["graphql"]))


def test_query_whitespace_is_ignored() -> None:
    a = gql("query { user { id name } }")
    b = gql("query   {\n  user {\n    id\n    name\n  }\n}")
    assert matches(a, b)


def test_operation_name_must_match() -> None:
    a = gql("query A { a }", operation="A")
    b = gql("query A { a }", operation="B")
    assert not matches(a, b)


def test_variables_compared_by_value_order_independent() -> None:
    a = gql("query ($id: ID!) { u(id: $id) }", variables={"id": "1", "page": 2})
    b = gql("query ($id: ID!) { u(id: $id) }", variables={"page": 2, "id": "1"})
    assert matches(a, b)


def test_different_variables_do_not_match() -> None:
    a = gql("query ($id: ID!) { u(id: $id) }", variables={"id": "1"})
    b = gql("query ($id: ID!) { u(id: $id) }", variables={"id": "2"})
    assert not matches(a, b)


def test_non_graphql_body_falls_back_to_exact_match() -> None:
    a = RecordedRequest("POST", "https://api.example.com/x", [], b"raw-1")
    same = RecordedRequest("POST", "https://api.example.com/x", [], b"raw-1")
    diff = RecordedRequest("POST", "https://api.example.com/x", [], b"raw-2")
    assert matches(a, same)
    assert not matches(a, diff)


def test_end_to_end_graphql_replay(tmp_path, boom) -> None:
    path = tmp_path / "gql.json"
    calls: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.content)
        return httpx.Response(200, json={"data": {"user": {"id": "1"}}})

    recorder = Cassette.load(
        path, record_mode=RecordMode.ONCE, match_on=("method", "url", "graphql")
    )
    body = {"query": "query { user { id } }", "variables": {"x": 1}}
    with httpx.Client(
        transport=recorder.sync_transport(real=httpx.MockTransport(handler))
    ) as client:
        resp = client.post("https://api.example.com/graphql", json=body)
        assert resp.json()["data"]["user"]["id"] == "1"
    recorder.save()

    # Same operation, different formatting, replays without touching the network.
    player = Cassette.load(path, record_mode=RecordMode.NONE, match_on=("method", "url", "graphql"))
    reformatted = {"query": "query {\n  user {\n    id\n  }\n}", "variables": {"x": 1}}
    with httpx.Client(transport=player.sync_transport(real=httpx.MockTransport(boom))) as client:
        resp = client.post("https://api.example.com/graphql", json=reformatted)
        assert resp.json()["data"]["user"]["id"] == "1"
