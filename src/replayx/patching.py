"""Shared httpx interception used by record/replay and inline stubs.

httpx asks ``Client._transport_for_url`` for a transport on every request. We
swap that method so replayx can return its own transport, then restore it on
exit. Both ``use_cassette`` and ``use_stubs`` build on this.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import httpx

from .errors import ReplayxError

_TRANSPORT_HOOK = "_transport_for_url"

# Each factory receives the client, the request URL, and the transport httpx
# would otherwise use, and returns the transport replayx should use instead.
SyncFactory = Callable[[httpx.Client, httpx.URL, httpx.BaseTransport], httpx.BaseTransport]
AsyncFactory = Callable[
    [httpx.AsyncClient, httpx.URL, httpx.AsyncBaseTransport], httpx.AsyncBaseTransport
]


@contextmanager
def patch_httpx(make_sync: SyncFactory, make_async: AsyncFactory) -> Iterator[None]:
    if not hasattr(httpx.Client, _TRANSPORT_HOOK):  # pragma: no cover - version guard
        raise ReplayxError(
            "replayx could not patch httpx (incompatible version). "
            "Use the explicit transport API instead."
        )

    original_sync = httpx.Client._transport_for_url
    original_async = httpx.AsyncClient._transport_for_url

    def sync_for_url(client: httpx.Client, url: httpx.URL) -> httpx.BaseTransport:
        return make_sync(client, url, original_sync(client, url))

    def async_for_url(client: httpx.AsyncClient, url: httpx.URL) -> httpx.AsyncBaseTransport:
        return make_async(client, url, original_async(client, url))

    setattr(httpx.Client, _TRANSPORT_HOOK, sync_for_url)
    setattr(httpx.AsyncClient, _TRANSPORT_HOOK, async_for_url)
    try:
        yield
    finally:
        setattr(httpx.Client, _TRANSPORT_HOOK, original_sync)
        setattr(httpx.AsyncClient, _TRANSPORT_HOOK, original_async)
