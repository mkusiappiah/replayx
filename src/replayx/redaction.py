"""Secret redaction for recorded interactions.

Filters run at *record* time and only affect what is written to the cassette;
the live response handed back to your application is never modified. This makes
it safe to commit cassettes to version control.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING, Callable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

if TYPE_CHECKING:
    from .cassette import RecordedRequest, RecordedResponse

REDACTED = "REDACTED"

RequestHook = Callable[["RecordedRequest"], Optional["RecordedRequest"]]
ResponseHook = Callable[["RecordedResponse"], Optional["RecordedResponse"]]


def _redact_headers(headers: list[tuple[str, str]], names: Sequence[str]) -> list[tuple[str, str]]:
    if not names:
        return headers
    targets = {name.lower() for name in names}
    return [(name, REDACTED if name.lower() in targets else value) for name, value in headers]


def _redact_query(url: str, names: Sequence[str]) -> str:
    if not names:
        return url
    targets = {name.lower() for name in names}
    parts = urlsplit(url)
    if not parts.query:
        return url
    items = [
        (key, REDACTED if key.lower() in targets else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(parts._replace(query=urlencode(items)))


def apply_request_filters(
    request: RecordedRequest,
    *,
    filter_headers: Sequence[str],
    filter_query_params: Sequence[str],
    hook: RequestHook | None,
) -> RecordedRequest | None:
    """Return a redacted copy of ``request``, or ``None`` to skip recording it."""

    redacted = replace(
        request,
        url=_redact_query(request.url, filter_query_params),
        headers=_redact_headers(request.headers, filter_headers),
    )
    if hook is not None:
        return hook(redacted)
    return redacted


def apply_response_filters(
    response: RecordedResponse,
    *,
    filter_headers: Sequence[str],
    hook: ResponseHook | None,
) -> RecordedResponse | None:
    """Return a redacted copy of ``response``, or ``None`` to skip recording it."""

    redacted = replace(response, headers=_redact_headers(response.headers, filter_headers))
    if hook is not None:
        return hook(redacted)
    return redacted
