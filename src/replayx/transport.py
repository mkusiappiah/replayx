"""httpx transports that record to / replay from a cassette."""

from __future__ import annotations

import httpx

from .cassette import Cassette, RecordedRequest, RecordedResponse
from .errors import UnhandledRequestError


class ReplayTransport(httpx.BaseTransport):
    """Synchronous transport. Wrap a real transport to enable recording."""

    def __init__(self, cassette: Cassette, real: httpx.BaseTransport) -> None:
        self._cassette = cassette
        self._real = real

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.read()
        recorded_request = RecordedRequest.from_httpx(request)

        if self._cassette.allow_replay:
            interaction = self._cassette.find(recorded_request)
            if interaction is not None:
                return interaction.response.to_httpx(request)

        if self._cassette.allow_record:
            real_response = self._real.handle_request(request)
            real_response.read()
            recorded_response = RecordedResponse.from_httpx(real_response)
            self._cassette.record(recorded_request, recorded_response)
            return recorded_response.to_httpx(request)

        raise UnhandledRequestError(recorded_request, self._cassette)

    def close(self) -> None:
        self._real.close()


class AsyncReplayTransport(httpx.AsyncBaseTransport):
    """Asynchronous transport. Wrap a real transport to enable recording."""

    def __init__(self, cassette: Cassette, real: httpx.AsyncBaseTransport) -> None:
        self._cassette = cassette
        self._real = real

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await request.aread()
        recorded_request = RecordedRequest.from_httpx(request)

        if self._cassette.allow_replay:
            interaction = self._cassette.find(recorded_request)
            if interaction is not None:
                return interaction.response.to_httpx(request)

        if self._cassette.allow_record:
            real_response = await self._real.handle_async_request(request)
            await real_response.aread()
            recorded_response = RecordedResponse.from_httpx(real_response)
            self._cassette.record(recorded_request, recorded_response)
            return recorded_response.to_httpx(request)

        raise UnhandledRequestError(recorded_request, self._cassette)

    async def aclose(self) -> None:
        await self._real.aclose()
