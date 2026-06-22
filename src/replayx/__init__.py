"""replayx — record & replay HTTP interactions for httpx.

replayx is an async-native "VCR" for `httpx`: it records real HTTP responses
to a cassette file the first time your tests run, then replays them on every
subsequent run so tests are fast, offline and deterministic.

See https://github.com/mkusiappiah/replayx for documentation.
"""

from __future__ import annotations

__version__ = "0.4.2"

from ._types import RecordMode
from .cassette import Cassette, Interaction, RecordedRequest, RecordedResponse
from .errors import (
    CassetteFormatError,
    ReplayxError,
    UnhandledRequestError,
    UnhandledStubError,
)
from .recorder import use_cassette
from .stubs import Route, StubRouter, use_stubs
from .transport import AsyncReplayTransport, ReplayTransport

__all__ = [
    "AsyncReplayTransport",
    "Cassette",
    "CassetteFormatError",
    "Interaction",
    "RecordMode",
    "RecordedRequest",
    "RecordedResponse",
    "ReplayTransport",
    "ReplayxError",
    "Route",
    "StubRouter",
    "UnhandledRequestError",
    "UnhandledStubError",
    "__version__",
    "use_cassette",
    "use_stubs",
]
