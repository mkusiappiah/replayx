"""replayx — record & replay HTTP interactions for httpx.

replayx is an async-native "VCR" for `httpx`: it records real HTTP responses
to a cassette file the first time your tests run, then replays them on every
subsequent run so tests are fast, offline and deterministic.

See https://github.com/mkusiappiah/replayx for documentation.
"""

from __future__ import annotations

__version__ = "0.3.0"

from ._types import RecordMode
from .cassette import Cassette, Interaction, RecordedRequest, RecordedResponse
from .errors import CassetteFormatError, ReplayxError, UnhandledRequestError
from .recorder import use_cassette
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
    "UnhandledRequestError",
    "__version__",
    "use_cassette",
]
