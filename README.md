# replayx

Record and replay HTTP interactions for [httpx](https://www.python-httpx.org/). Run your tests fast and offline.

[![CI](https://github.com/your-org/replayx/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/replayx/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/replayx.svg)](https://pypi.org/project/replayx/)
[![Python versions](https://img.shields.io/pypi/pyversions/replayx.svg)](https://pypi.org/project/replayx/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

replayx saves real HTTP responses to a cassette file on the first test run. Every later run reads from the cassette. No network calls. No flaky tests. No slow CI.

```python
import httpx
from replayx import use_cassette

with use_cassette("cassettes/github.json"):
    resp = httpx.get("https://api.github.com/users/octocat")
    assert resp.json()["login"] == "octocat"
```

The first run records. Later runs replay.

## Why I built replayx

vcrpy brought record and replay to Python. vcrpy targets requests and the sync world. I built replayx for modern httpx code.

| Feature | replayx | vcrpy |
| --- | --- | --- |
| Async httpx.AsyncClient | yes | limited |
| Built for httpx | yes | through patches |
| Zero deps beyond httpx | yes (JSON) | needs PyYAML |
| Secret redaction for committed cassettes | yes | partial |
| Explicit transport API, no patching | yes | no |
| Modern typing with py.typed | yes | no |

## Install

```bash
pip install replayx
```

Add YAML cassettes:

```bash
pip install "replayx[yaml]"
```

replayx needs Python 3.9 or newer and httpx 0.23 or newer.

## Usage

### Patch httpx with use_cassette

use_cassette patches httpx for the block. Your existing client code runs without changes. Sync and async both work.

```python
import httpx
from replayx import use_cassette

async def fetch():
    async with httpx.AsyncClient() as client:
        return await client.get("https://api.example.com/data")

with use_cassette("cassettes/data.json"):
    resp = await fetch()
```

### Build a transport yourself

Prefer no patching? Build a transport and pass the transport to your client. Nothing gets monkeypatched.

```python
import httpx
from replayx import Cassette

cassette = Cassette.load("cassettes/data.json", record_mode="once")

with httpx.Client(transport=cassette.sync_transport()) as client:
    resp = client.get("https://api.example.com/data")

cassette.save()
```

Use `cassette.async_transport()` with `httpx.AsyncClient` for async code.

### The pytest plugin

The plugin gives each test an auto-named cassette at `<test-dir>/cassettes/<test-name>.json`.

```python
import httpx

def test_octocat(replayx_cassette):
    with replayx_cassette():
        resp = httpx.get("https://api.github.com/users/octocat")
        assert resp.status_code == 200
```

Re-record a whole run from the command line:

```bash
pytest --replayx-record=all
```

Set per-test defaults with the marker:

```python
import pytest

@pytest.mark.replayx(match_on=("method", "url", "body"), filter_headers=["authorization"])
def test_create(replayx_cassette):
    with replayx_cassette():
        ...
```

## Record modes

| Mode | What happens |
| --- | --- |
| once (default) | Replay an existing cassette. Record everything when no cassette exists. A new request against an existing cassette raises an error. |
| new_episodes | Replay matches and append new interactions. |
| none | Replay only. No network. No writes. Good for CI. |
| all | Always reach the real backend and overwrite the cassette. Use to re-record. |

```python
with use_cassette("cassettes/api.json", record_mode="none"):
    ...
```

## Match requests

Requests match on method and url by default. Query order does not affect matching. Change the rules with match_on.

```python
with use_cassette("cassettes/api.json", match_on=("method", "path", "body")):
    ...
```

Available matchers: method, scheme, host, port, path, query, url (alias uri), headers, body.

## Redact secrets

Commit cassettes without leaking credentials. Redaction runs at record time. The live response your code receives stays intact.

```python
with use_cassette(
    "cassettes/api.json",
    filter_headers=["authorization", "set-cookie"],
    filter_query_params=["api_key", "token"],
):
    ...
```

Use hooks for full control. Return a changed recording, or return None to skip the recording.

```python
from dataclasses import replace

def scrub_body(response):
    return replace(response, body=b'{"token": "REDACTED"}')

with use_cassette("cassettes/api.json", before_record_response=scrub_body):
    ...
```

## Cassette format

Cassettes use plain JSON. YAML works with the yaml extra. Both read well in code review.

```json
{
  "version": 1,
  "recorded_with": "replayx/0.1.0",
  "interactions": [
    {
      "request": { "method": "GET", "url": "https://api.example.com/data", "headers": [], "body": null },
      "response": { "status_code": 200, "headers": [["content-type", "application/json"]], "body": { "text": "{\"ok\":true}" } }
    }
  ]
}
```

replayx stores binary bodies as base64.

## Contribute

I welcome contributions. Set up a dev environment:

```bash
git clone https://github.com/your-org/replayx
cd replayx
pip install -e ".[dev]"
pytest
ruff check .
mypy
```

Open an issue before large changes.

## License

MIT. See [LICENSE](LICENSE).
