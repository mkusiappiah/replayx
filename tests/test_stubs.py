from __future__ import annotations

import httpx
import pytest

from replayx import StubRouter, UnhandledStubError, use_stubs


def test_basic_get_stub() -> None:
    with use_stubs() as router:
        route = router.get("https://api.example.com/users").respond(json=[{"id": 1}])
        with httpx.Client() as client:
            resp = client.get("https://api.example.com/users")
            assert resp.status_code == 200
            assert resp.json() == [{"id": 1}]
        assert route.call_count == 1


def test_query_string_is_ignored_when_matching() -> None:
    with use_stubs() as router:
        router.get("https://api.example.com/search").respond(json={"hits": 0})
        with httpx.Client() as client:
            resp = client.get("https://api.example.com/search?q=anything&page=3")
            assert resp.json() == {"hits": 0}


def test_method_and_status_and_headers() -> None:
    with use_stubs() as router:
        router.post("https://api.example.com/users").respond(
            201, json={"id": 9}, headers={"x-trace": "abc"}
        )
        with httpx.Client() as client:
            resp = client.post("https://api.example.com/users", json={"name": "a"})
            assert resp.status_code == 201
            assert resp.json() == {"id": 9}
            assert resp.headers["x-trace"] == "abc"


def test_unmatched_request_raises() -> None:
    with use_stubs() as router:
        router.get("https://api.example.com/a").respond(json={})
        with httpx.Client() as client:
            with pytest.raises(UnhandledStubError):
                client.get("https://api.example.com/b")


def test_method_mismatch_raises() -> None:
    with use_stubs() as router:
        router.get("https://api.example.com/a").respond(json={})
        with httpx.Client() as client:
            with pytest.raises(UnhandledStubError):
                client.delete("https://api.example.com/a")


def test_text_and_default_status() -> None:
    with use_stubs() as router:
        router.get("https://api.example.com/ping").respond(text="pong")
        router.get("https://api.example.com/empty")  # no respond -> default 200, empty
        with httpx.Client() as client:
            assert client.get("https://api.example.com/ping").text == "pong"
            empty = client.get("https://api.example.com/empty")
            assert empty.status_code == 200
            assert empty.content == b""


async def test_async_stub() -> None:
    with use_stubs() as router:
        router.get("https://api.example.com/async").respond(json={"ok": True})
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.example.com/async")
            assert resp.json() == {"ok": True}


def test_httpx_restored_after_block() -> None:
    original = httpx.Client._transport_for_url
    with use_stubs() as router:
        router.get("https://api.example.com/x").respond(json={})
        with httpx.Client() as client:
            client.get("https://api.example.com/x")
    assert httpx.Client._transport_for_url is original


def test_supply_own_router() -> None:
    router = StubRouter()
    router.get("https://api.example.com/x").respond(json={"hi": True})
    with use_stubs(router) as active:
        assert active is router
        with httpx.Client() as client:
            assert client.get("https://api.example.com/x").json() == {"hi": True}
