from __future__ import annotations

import pytest

from replayx import RecordedRequest
from replayx.matchers import build_matchers


def req(method: str, url: str, *, body: bytes = b"") -> RecordedRequest:
    return RecordedRequest(method=method, url=url, headers=[], body=body)


def matches(names, a, b) -> bool:
    return all(matcher(a, b) for matcher in build_matchers(names))


def test_method_is_case_insensitive() -> None:
    assert matches(["method"], req("get", "https://x.test/"), req("GET", "https://x.test/"))
    assert not matches(["method"], req("GET", "https://x.test/"), req("POST", "https://x.test/"))


def test_url_matcher_is_query_order_independent() -> None:
    a = req("GET", "https://x.test/a?b=1&c=2")
    b = req("GET", "https://x.test/a?c=2&b=1")
    assert matches(["url"], a, b)


def test_url_matcher_ignores_fragment_and_default_port() -> None:
    a = req("GET", "https://x.test/a#frag")
    b = req("GET", "https://x.test:443/a")
    assert matches(["url"], a, b)


def test_url_matcher_distinguishes_path() -> None:
    assert not matches(["url"], req("GET", "https://x.test/a"), req("GET", "https://x.test/b"))


def test_body_matcher() -> None:
    a = req("POST", "https://x.test/", body=b'{"x":1}')
    same = req("POST", "https://x.test/", body=b'{"x":1}')
    diff = req("POST", "https://x.test/", body=b'{"x":2}')
    assert matches(["body"], a, same)
    assert not matches(["body"], a, diff)


def test_unknown_matcher_name() -> None:
    with pytest.raises(ValueError):
        build_matchers(["definitely-not-real"])


def test_empty_matchers_rejected() -> None:
    with pytest.raises(ValueError):
        build_matchers([])
