"""Request matching strategies.

A matcher is a callable ``(recorded, incoming) -> bool`` that decides whether a
recorded request should satisfy an incoming one. Cassettes combine matchers with
logical AND; an interaction matches only if *all* configured matchers agree.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Callable
from urllib.parse import parse_qsl, urlsplit

if TYPE_CHECKING:
    from .cassette import RecordedRequest

Matcher = Callable[["RecordedRequest", "RecordedRequest"], bool]

_DEFAULT_PORTS = {"http": 80, "https": 443, "ws": 80, "wss": 443}


def _port(scheme: str, port: int | None) -> int | None:
    if port is not None:
        return port
    return _DEFAULT_PORTS.get(scheme.lower())


def _query_items(query: str) -> list[tuple[str, str]]:
    return sorted(parse_qsl(query, keep_blank_values=True))


def match_method(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    return recorded.method.upper() == incoming.method.upper()


def match_scheme(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    return urlsplit(recorded.url).scheme == urlsplit(incoming.url).scheme


def match_host(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    return urlsplit(recorded.url).hostname == urlsplit(incoming.url).hostname


def match_port(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    a, b = urlsplit(recorded.url), urlsplit(incoming.url)
    return _port(a.scheme, a.port) == _port(b.scheme, b.port)


def match_path(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    return urlsplit(recorded.url).path == urlsplit(incoming.url).path


def match_query(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    return _query_items(urlsplit(recorded.url).query) == _query_items(urlsplit(incoming.url).query)


def match_url(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    """Match scheme, host, port, path and query (order-independent), ignoring fragments."""

    a, b = urlsplit(recorded.url), urlsplit(incoming.url)
    return (
        a.scheme == b.scheme
        and a.hostname == b.hostname
        and _port(a.scheme, a.port) == _port(b.scheme, b.port)
        and a.path == b.path
        and _query_items(a.query) == _query_items(b.query)
    )


def match_headers(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    def normalise(headers: list[tuple[str, str]]) -> set[tuple[str, str]]:
        return {(name.lower(), value) for name, value in headers}

    return normalise(recorded.headers) == normalise(incoming.headers)


def match_body(recorded: RecordedRequest, incoming: RecordedRequest) -> bool:
    return recorded.body == incoming.body


REGISTRY: dict[str, Matcher] = {
    "method": match_method,
    "scheme": match_scheme,
    "host": match_host,
    "port": match_port,
    "path": match_path,
    "query": match_query,
    "url": match_url,
    "uri": match_url,
    "headers": match_headers,
    "body": match_body,
}


def build_matchers(names: Iterable[str]) -> list[Matcher]:
    """Resolve matcher names to callables, raising ``ValueError`` for unknown names."""

    matchers: list[Matcher] = []
    for name in names:
        try:
            matchers.append(REGISTRY[name])
        except KeyError:
            valid = ", ".join(sorted(REGISTRY))
            raise ValueError(f"unknown matcher {name!r}; available matchers: {valid}") from None
    if not matchers:
        raise ValueError("at least one matcher is required")
    return matchers
