"""Shared test helpers."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest


@pytest.fixture
def echo_handler() -> Callable[[list[str]], Callable[[httpx.Request], httpx.Response]]:
    """Return a factory that builds a MockTransport handler recording its calls."""

    def make(calls: list[str]) -> Callable[[httpx.Request], httpx.Response]:
        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(f"{request.method} {request.url.path}")
            return httpx.Response(
                200,
                json={"path": request.url.path, "method": request.method, "ok": True},
            )

        return handler

    return make


@pytest.fixture
def boom() -> Callable[[httpx.Request], httpx.Response]:
    """A handler that fails if the network is ever touched during replay."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"network was hit during replay: {request.method} {request.url}")

    return handler
