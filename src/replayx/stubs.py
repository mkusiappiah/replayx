"""Inline HTTP stubs for httpx, a respx-style alternative to recording.

Define responses in code, with no cassette and no network:

    import httpx
    from replayx import use_stubs

    with use_stubs() as router:
        router.get("https://api.example.com/users").respond(json=[{"id": 1}])
        with httpx.Client() as client:
            resp = client.get("https://api.example.com/users")
            assert resp.json() == [{"id": 1}]

A request that matches no route raises ``UnhandledStubError``, so unmocked calls
surface immediately. Routes match on method plus scheme, host, port, and path;
the query string is ignored.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlsplit

import httpx

from .errors import UnhandledStubError
from .matchers import _port
from .patching import patch_httpx


class Route:
    """A single stubbed endpoint and its response."""

    def __init__(self, method: str, url: str) -> None:
        self.method = method.upper()
        self.url = url
        self.calls: list[httpx.Request] = []
        self._response: dict[str, Any] = {"status_code": 200}

    def respond(
        self,
        status_code: int = 200,
        *,
        json: Any = None,
        text: str | None = None,
        content: bytes | None = None,
        headers: Mapping[str, str] | Sequence[tuple[str, str]] | None = None,
    ) -> Route:
        """Set the response for this route. Returns the route for chaining."""

        spec: dict[str, Any] = {"status_code": status_code}
        if json is not None:
            spec["json"] = json
        if text is not None:
            spec["text"] = text
        if content is not None:
            spec["content"] = content
        if headers is not None:
            spec["headers"] = headers
        self._response = spec
        return self

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def matches(self, request: httpx.Request) -> bool:
        if self.method != request.method.upper():
            return False
        stub = urlsplit(self.url)
        req = urlsplit(str(request.url))
        return (stub.scheme, stub.hostname, _port(stub.scheme, stub.port), stub.path) == (
            req.scheme,
            req.hostname,
            _port(req.scheme, req.port),
            req.path,
        )

    def build_response(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return httpx.Response(request=request, **self._response)


class StubRouter:
    """Holds stubbed routes and finds the one matching a request."""

    def __init__(self) -> None:
        self.routes: list[Route] = []

    def route(self, method: str, url: str) -> Route:
        route = Route(method, url)
        self.routes.append(route)
        return route

    def get(self, url: str) -> Route:
        return self.route("GET", url)

    def post(self, url: str) -> Route:
        return self.route("POST", url)

    def put(self, url: str) -> Route:
        return self.route("PUT", url)

    def patch(self, url: str) -> Route:
        return self.route("PATCH", url)

    def delete(self, url: str) -> Route:
        return self.route("DELETE", url)

    def head(self, url: str) -> Route:
        return self.route("HEAD", url)

    def options(self, url: str) -> Route:
        return self.route("OPTIONS", url)

    def match(self, request: httpx.Request) -> Route | None:
        for route in self.routes:
            if route.matches(request):
                return route
        return None


class StubTransport(httpx.BaseTransport):
    def __init__(self, router: StubRouter) -> None:
        self._router = router

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        route = self._router.match(request)
        if route is None:
            raise UnhandledStubError(request.method, str(request.url), len(self._router.routes))
        return route.build_response(request)


class AsyncStubTransport(httpx.AsyncBaseTransport):
    def __init__(self, router: StubRouter) -> None:
        self._router = router

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await request.aread()
        route = self._router.match(request)
        if route is None:
            raise UnhandledStubError(request.method, str(request.url), len(self._router.routes))
        return route.build_response(request)


@contextmanager
def use_stubs(router: StubRouter | None = None) -> Iterator[StubRouter]:
    """Patch httpx so every request is served from inline stubs.

    Yields the active :class:`StubRouter`. A request matching no route raises
    :class:`~replayx.UnhandledStubError`.
    """

    router = router or StubRouter()

    def make_sync(
        client: httpx.Client, url: httpx.URL, original: httpx.BaseTransport
    ) -> httpx.BaseTransport:
        return StubTransport(router)

    def make_async(
        client: httpx.AsyncClient, url: httpx.URL, original: httpx.AsyncBaseTransport
    ) -> httpx.AsyncBaseTransport:
        return AsyncStubTransport(router)

    with patch_httpx(make_sync, make_async):
        yield router
