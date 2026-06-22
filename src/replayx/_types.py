"""Shared types and enumerations for replayx."""

from __future__ import annotations

from enum import Enum


class RecordMode(str, Enum):
    """Controls how a cassette records and replays interactions.

    The semantics mirror the well-understood VCR record modes:

    * ``ONCE`` — Replay interactions from an existing cassette. If the cassette
      file does not yet exist, record everything. Once a cassette exists, new
      (unmatched) requests raise :class:`~replayx.UnhandledRequestError`.
    * ``NEW_EPISODES`` — Replay matching interactions and record any new ones,
      appending them to the cassette.
    * ``NONE`` — Replay only. Never touch the network and never write. New
      requests raise :class:`~replayx.UnhandledRequestError`.
    * ``ALL`` — Never replay. Always hit the real backend and (re)record,
      overwriting the cassette.
    """

    ONCE = "once"
    NEW_EPISODES = "new_episodes"
    NONE = "none"
    ALL = "all"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value
