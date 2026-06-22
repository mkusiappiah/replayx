"""Cassette model: recorded requests/responses and persistence."""

from __future__ import annotations

import base64
import importlib.metadata
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from ._types import RecordMode
from .encoding import encode_content
from .errors import CassetteFormatError
from .matchers import Matcher, build_matchers
from .redaction import (
    RequestHook,
    ResponseHook,
    apply_request_filters,
    apply_response_filters,
)
from .serializers import Serializer, serializer_for_path

CASSETTE_VERSION = 1
# Strip framing headers that no longer apply to a buffered, replayed body.
# Keep content-encoding so replay reproduces the original wire behaviour.
_STRIPPED_RESPONSE_HEADERS = {"content-length", "transfer-encoding"}


def _content_encoding(headers: list[tuple[str, str]]) -> str | None:
    for name, value in headers:
        if name.lower() == "content-encoding":
            return value
    return None


# A serialized body is ``None`` (empty), ``{"text": "..."}`` for UTF-8 content,
# or ``{"base64": "..."}`` for binary content.


def _recorded_with() -> str:
    try:
        version = importlib.metadata.version("replayx")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - editable/source
        version = "0+unknown"
    return f"replayx/{version}"


def encode_body(data: bytes) -> dict[str, str] | None:
    if not data:
        return None
    try:
        return {"text": data.decode("utf-8")}
    except UnicodeDecodeError:
        return {"base64": base64.b64encode(data).decode("ascii")}


def decode_body(obj: dict[str, str] | None) -> bytes:
    if obj is None:
        return b""
    if "text" in obj:
        return obj["text"].encode("utf-8")
    if "base64" in obj:
        return base64.b64decode(obj["base64"])
    raise CassetteFormatError(f"cannot decode body: {obj!r}")


@dataclass
class RecordedRequest:
    method: str
    url: str
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""

    @classmethod
    def from_httpx(cls, request: httpx.Request) -> RecordedRequest:
        return cls(
            method=request.method,
            url=str(request.url),
            headers=list(request.headers.multi_items()),
            body=request.content,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "headers": [list(item) for item in self.headers],
            "body": encode_body(self.body),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecordedRequest:
        return cls(
            method=data["method"],
            url=data["url"],
            headers=[(name, value) for name, value in data.get("headers", [])],
            body=decode_body(data.get("body")),
        )


@dataclass
class RecordedResponse:
    status_code: int
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""
    http_version: str | None = None

    @classmethod
    def from_httpx(cls, response: httpx.Response) -> RecordedResponse:
        # ``response.content`` is content-decoded by httpx. Keep content-encoding
        # so replay can re-encode; drop framing headers that no longer apply.
        headers = [
            (name, value)
            for name, value in response.headers.multi_items()
            if name.lower() not in _STRIPPED_RESPONSE_HEADERS
        ]
        raw_version = response.extensions.get("http_version")
        if isinstance(raw_version, bytes):
            http_version = raw_version.decode("ascii", "ignore") or None
        else:
            http_version = raw_version
        return cls(
            status_code=response.status_code,
            headers=headers,
            body=response.content,
            http_version=http_version,
        )

    def to_httpx(self, request: httpx.Request) -> httpx.Response:
        headers = self.headers
        body = self.body
        encoding = _content_encoding(headers)
        if encoding:
            reencoded = encode_content(self.body, encoding)
            if reencoded is None:
                # Unknown codec or missing optional dependency: drop the header
                # and serve the decoded body so replay still works.
                headers = [(n, v) for n, v in headers if n.lower() != "content-encoding"]
            else:
                body = reencoded
        return httpx.Response(
            status_code=self.status_code,
            headers=headers,
            content=body,
            request=request,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status_code": self.status_code,
            "headers": [list(item) for item in self.headers],
            "body": encode_body(self.body),
        }
        if self.http_version:
            data["http_version"] = self.http_version
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecordedResponse:
        return cls(
            status_code=int(data["status_code"]),
            headers=[(name, value) for name, value in data.get("headers", [])],
            body=decode_body(data.get("body")),
            http_version=data.get("http_version"),
        )


@dataclass
class Interaction:
    request: RecordedRequest
    response: RecordedResponse
    played: bool = field(default=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        return {"request": self.request.to_dict(), "response": self.response.to_dict()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Interaction:
        try:
            return cls(
                request=RecordedRequest.from_dict(data["request"]),
                response=RecordedResponse.from_dict(data["response"]),
            )
        except (KeyError, TypeError) as exc:
            raise CassetteFormatError(f"malformed interaction: {exc}") from exc


class Cassette:
    """A collection of recorded HTTP interactions backed by a file."""

    def __init__(
        self,
        *,
        path: Path,
        record_mode: RecordMode,
        matchers: list[Matcher],
        serializer: Serializer,
        interactions: list[Interaction] | None = None,
        allow_record: bool,
        allow_replay: bool,
        allow_playback_repeats: bool = False,
        filter_headers: Sequence[str] = (),
        filter_query_params: Sequence[str] = (),
        before_record_request: RequestHook | None = None,
        before_record_response: ResponseHook | None = None,
    ) -> None:
        self.path = path
        self.record_mode = record_mode
        self.matchers = matchers
        self.serializer = serializer
        self.interactions: list[Interaction] = interactions or []
        self.allow_record = allow_record
        self.allow_replay = allow_replay
        self.allow_playback_repeats = allow_playback_repeats
        self.filter_headers = tuple(filter_headers)
        self.filter_query_params = tuple(filter_query_params)
        self.before_record_request = before_record_request
        self.before_record_response = before_record_response
        self._dirty = False

    # -- construction --------------------------------------------------------

    @classmethod
    def load(
        cls,
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
    ) -> Cassette:
        path = Path(path)
        record_mode = RecordMode(record_mode)
        serializer = serializer or serializer_for_path(path)
        matchers = build_matchers(match_on)

        interactions: list[Interaction] = []
        if path.exists() and record_mode is not RecordMode.ALL:
            data = serializer.loads(path.read_text(encoding="utf-8"))
            raw = data.get("interactions", [])
            if not isinstance(raw, list):
                raise CassetteFormatError("'interactions' must be a list")
            interactions = [Interaction.from_dict(item) for item in raw]

        allow_replay = record_mode is not RecordMode.ALL
        if record_mode is RecordMode.NONE:
            allow_record = False
        elif record_mode is RecordMode.ONCE:
            # Only record when starting from an empty cassette.
            allow_record = len(interactions) == 0
        else:  # ALL, NEW_EPISODES
            allow_record = True

        return cls(
            path=path,
            record_mode=record_mode,
            matchers=matchers,
            serializer=serializer,
            interactions=interactions,
            allow_record=allow_record,
            allow_replay=allow_replay,
            allow_playback_repeats=allow_playback_repeats,
            filter_headers=filter_headers,
            filter_query_params=filter_query_params,
            before_record_request=before_record_request,
            before_record_response=before_record_response,
        )

    # -- transports ----------------------------------------------------------

    def sync_transport(self, real: httpx.BaseTransport | None = None) -> httpx.BaseTransport:
        from .transport import ReplayTransport

        return ReplayTransport(self, real if real is not None else httpx.HTTPTransport())

    def async_transport(
        self, real: httpx.AsyncBaseTransport | None = None
    ) -> httpx.AsyncBaseTransport:
        from .transport import AsyncReplayTransport

        return AsyncReplayTransport(self, real if real is not None else httpx.AsyncHTTPTransport())

    # -- record / replay -----------------------------------------------------

    def find(self, incoming: RecordedRequest) -> Interaction | None:
        """Return the first recorded interaction that matches ``incoming``."""

        for interaction in self.interactions:
            if interaction.played and not self.allow_playback_repeats:
                continue
            if all(matcher(interaction.request, incoming) for matcher in self.matchers):
                interaction.played = True
                return interaction
        return None

    def record(self, request: RecordedRequest, response: RecordedResponse) -> None:
        """Store a new interaction, applying redaction filters first."""

        filtered_request = apply_request_filters(
            request,
            filter_headers=self.filter_headers,
            filter_query_params=self.filter_query_params,
            hook=self.before_record_request,
        )
        if filtered_request is None:
            return
        filtered_response = apply_response_filters(
            response,
            filter_headers=self.filter_headers,
            hook=self.before_record_response,
        )
        if filtered_response is None:
            return
        self.interactions.append(
            Interaction(request=filtered_request, response=filtered_response, played=True)
        )
        self._dirty = True

    # -- persistence ---------------------------------------------------------

    @property
    def dirty(self) -> bool:
        return self._dirty

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": CASSETTE_VERSION,
            "recorded_with": _recorded_with(),
            "interactions": [interaction.to_dict() for interaction in self.interactions],
        }

    def save(self) -> bool:
        """Persist the cassette if new interactions were recorded.

        Returns ``True`` if the file was written.
        """

        if not self._dirty:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.serializer.dumps(self.to_dict()), encoding="utf-8")
        self._dirty = False
        return True
