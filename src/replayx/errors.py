"""Exception types raised by replayx."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cassette import Cassette, RecordedRequest


class ReplayxError(Exception):
    """Base class for all replayx errors."""


class CassetteFormatError(ReplayxError):
    """Raised when a cassette file cannot be parsed or is malformed."""


class UnhandledRequestError(ReplayxError):
    """Raised when a request has no matching recorded interaction.

    This happens in ``none`` mode (replay only) or ``once`` mode when the
    cassette already exists and the request was not recorded previously.
    """

    def __init__(self, request: RecordedRequest, cassette: Cassette) -> None:
        self.request = request
        self.cassette = cassette
        message = (
            f"replayx: no recorded interaction matched "
            f"{request.method} {request.url}\n"
            f"  cassette:     {cassette.path}\n"
            f"  record_mode:  {cassette.record_mode.value}\n"
            f"  recorded:     {len(cassette.interactions)} interaction(s)\n"
            "\n"
            "New requests are not allowed in 'none' mode, or in 'once' mode when\n"
            "the cassette already exists. To fix this, either:\n"
            "  - re-record with record_mode='all' (overwrite) or 'new_episodes' (append), or\n"
            "  - relax the request matchers via match_on=(...)."
        )
        super().__init__(message)


class UnhandledStubError(ReplayxError):
    """Raised when an inline stub router has no route matching a request."""

    def __init__(self, method: str, url: str, registered: int) -> None:
        self.method = method
        self.url = url
        message = (
            f"replayx: no stub matched {method} {url}\n"
            f"  registered routes: {registered}\n"
            "\n"
            "Add a matching route, e.g. router.get(url).respond(json=...)."
        )
        super().__init__(message)
