"""Pytest integration for replayx.

Provides a ``replayx_cassette`` fixture that builds a per-test cassette path
(``<test-dir>/cassettes/<test-name>.json``) and a ``--replayx-record`` CLI flag
to override the record mode for a whole run (handy for re-recording in CI).

Example::

    def test_github_user(replayx_cassette):
        with replayx_cassette():
            import httpx
            resp = httpx.get("https://api.github.com/users/octocat")
            assert resp.status_code == 200
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import pytest

from ._types import RecordMode
from .cassette import Cassette
from .recorder import use_cassette

CassetteFactory = Callable[..., AbstractContextManager[Cassette]]


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("replayx")
    group.addoption(
        "--replayx-record",
        action="store",
        default=None,
        choices=[mode.value for mode in RecordMode],
        help="Override the replayx record mode for this run (once/new_episodes/none/all).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "replayx(**kwargs): default keyword arguments for the replayx_cassette fixture.",
    )


def _marker_kwargs(request: pytest.FixtureRequest) -> dict[str, Any]:
    marker = request.node.get_closest_marker("replayx")
    return dict(marker.kwargs) if marker is not None else {}


@pytest.fixture
def replayx_cassette(request: pytest.FixtureRequest) -> CassetteFactory:
    cassette_dir = Path(request.path).parent / "cassettes"
    default_path = cassette_dir / f"{request.node.name}.json"
    override = request.config.getoption("--replayx-record")
    defaults = _marker_kwargs(request)

    def factory(path: str | Path | None = None, **kwargs: Any) -> AbstractContextManager[Cassette]:
        options: dict[str, Any] = {**defaults, **kwargs}
        if override and "record_mode" not in kwargs:
            options["record_mode"] = RecordMode(override)
        return use_cassette(path or default_path, **options)

    return factory
