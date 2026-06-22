"""High-level API: the ``use_cassette`` context manager.

``use_cassette`` patches httpx so that *any* ``httpx.Client`` or
``httpx.AsyncClient`` created inside the block is transparently recorded or
replayed — no need to inject a transport yourself. For explicit control, build
a transport via :meth:`Cassette.sync_transport` / :meth:`Cassette.async_transport`
instead.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import httpx

from ._types import RecordMode
from .cassette import Cassette
from .errors import ReplayxError
from .redaction import RequestHook, ResponseHook
from .serializers import Serializer
from .transport import AsyncReplayTransport, ReplayTransport

_TRANSPORT_HOOK = "_transport_for_url"

SyncTransportFor = Callable[[httpx.Client, httpx.URL], httpx.BaseTransport]
AsyncTransportFor = Callable[[httpx.AsyncClient, httpx.URL], httpx.AsyncBaseTransport]


class _Patcher:
    """Temporarily intercepts httpx's per-request transport selection.

    httpx asks ``Client._transport_for_url`` for a transport on every request,
    so swapping that method lets replayx wrap whatever transport the client
    would otherwise use — without the caller changing how clients are built.
    """

    def __init__(
        self,
        cassette: Cassette,
        real_sync: httpx.BaseTransport | None,
        real_async: httpx.AsyncBaseTransport | None,
    ) -> None:
        self._cassette = cassette
        self._real_sync = real_sync
        self._real_async = real_async
        self._original_sync: SyncTransportFor | None = None
        self._original_async: AsyncTransportFor | None = None

    def start(self) -> None:
        if not hasattr(httpx.Client, _TRANSPORT_HOOK):  # pragma: no cover - version guard
            raise ReplayxError(
                "replayx could not patch httpx (incompatible version). "
                "Use Cassette.sync_transport()/async_transport() explicitly instead."
            )

        cassette = self._cassette
        original_sync: SyncTransportFor = httpx.Client._transport_for_url
        original_async: AsyncTransportFor = httpx.AsyncClient._transport_for_url
        self._original_sync = original_sync
        self._original_async = original_async
        real_sync = self._real_sync
        real_async = self._real_async

        def sync_transport_for_url(client: httpx.Client, url: httpx.URL) -> httpx.BaseTransport:
            real = real_sync if real_sync is not None else original_sync(client, url)
            return ReplayTransport(cassette, real)

        def async_transport_for_url(
            client: httpx.AsyncClient, url: httpx.URL
        ) -> httpx.AsyncBaseTransport:
            real = real_async if real_async is not None else original_async(client, url)
            return AsyncReplayTransport(cassette, real)

        setattr(httpx.Client, _TRANSPORT_HOOK, sync_transport_for_url)
        setattr(httpx.AsyncClient, _TRANSPORT_HOOK, async_transport_for_url)

    def stop(self) -> None:
        if self._original_sync is not None:
            setattr(httpx.Client, _TRANSPORT_HOOK, self._original_sync)
        if self._original_async is not None:
            setattr(httpx.AsyncClient, _TRANSPORT_HOOK, self._original_async)


@contextmanager
def use_cassette(
    path: str | Path,
    *,
    record_mode: RecordMode | str = RecordMode.ONCE,
    match_on: Sequence[str] = ("method", "url"),
    serializer: Serializer | None = None,
    allow_playback_repeats: bool = False,
    filter_headers: Sequence[str] = (),
    filter_query_params: Sequence[str] = (),
    before_record_request: RequestHook | None = None,
    before_record_response: ResponseHook | None = None,
    patch: bool = True,
    real_sync_transport: httpx.BaseTransport | None = None,
    real_async_transport: httpx.AsyncBaseTransport | None = None,
) -> Iterator[Cassette]:
    """Record or replay HTTP interactions for the duration of the block.

    Args:
        path: Cassette file path. Extension selects the format (``.json`` default,
            ``.yaml``/``.yml`` require the ``yaml`` extra).
        record_mode: One of :class:`~replayx.RecordMode` (or its string value).
        match_on: Matcher names used to pair requests with recordings.
        filter_headers: Header names whose values are redacted before saving.
        filter_query_params: Query parameter names redacted before saving.
        before_record_request / before_record_response: Hooks returning a modified
            recording, or ``None`` to skip recording that interaction.
        patch: When ``True`` (default) httpx is patched so existing client code is
            intercepted automatically. When ``False``, build a transport yourself.
        real_sync_transport / real_async_transport: Override the underlying transport
            used while recording (primarily for testing).

    Yields:
        The active :class:`~replayx.Cassette`.
    """

    cassette = Cassette.load(
        path,
        record_mode=record_mode,
        match_on=match_on,
        serializer=serializer,
        allow_playback_repeats=allow_playback_repeats,
        filter_headers=filter_headers,
        filter_query_params=filter_query_params,
        before_record_request=before_record_request,
        before_record_response=before_record_response,
    )

    patcher = _Patcher(cassette, real_sync_transport, real_async_transport) if patch else None
    if patcher is not None:
        patcher.start()
    try:
        yield cassette
    finally:
        if patcher is not None:
            patcher.stop()
        cassette.save()
