"""High-level API: the ``use_cassette`` context manager.

``use_cassette`` patches httpx so that *any* ``httpx.Client`` or
``httpx.AsyncClient`` created inside the block is transparently recorded or
replayed — no need to inject a transport yourself. For explicit control, build
a transport via :meth:`Cassette.sync_transport` / :meth:`Cassette.async_transport`
instead.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import httpx

from ._types import RecordMode
from .cassette import Cassette
from .patching import patch_httpx
from .redaction import RequestHook, ResponseHook
from .serializers import Serializer
from .transport import AsyncReplayTransport, ReplayTransport


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

    def make_sync(
        client: httpx.Client, url: httpx.URL, original: httpx.BaseTransport
    ) -> httpx.BaseTransport:
        real = real_sync_transport if real_sync_transport is not None else original
        return ReplayTransport(cassette, real)

    def make_async(
        client: httpx.AsyncClient, url: httpx.URL, original: httpx.AsyncBaseTransport
    ) -> httpx.AsyncBaseTransport:
        real = real_async_transport if real_async_transport is not None else original
        return AsyncReplayTransport(cassette, real)

    if not patch:
        try:
            yield cassette
        finally:
            cassette.save()
        return

    with patch_httpx(make_sync, make_async):
        try:
            yield cassette
        finally:
            cassette.save()
