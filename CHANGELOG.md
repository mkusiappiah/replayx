# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-22

### Added
- Initial release.
- `use_cassette` context manager that transparently patches `httpx` to record
  and replay interactions.
- Synchronous (`ReplayTransport`) and asynchronous (`AsyncReplayTransport`)
  transports for explicit, no-magic usage.
- Four record modes: `once`, `new_episodes`, `none`, `all`.
- Configurable request matchers (`method`, `url`, `host`, `path`, `query`,
  `headers`, `body`, ...).
- Secret redaction via `filter_headers`, `filter_query_params`, and
  `before_record_request` / `before_record_response` hooks.
- JSON cassettes by default; optional YAML cassettes via the `yaml` extra.
- A `pytest` plugin exposing the `replayx_cassette` fixture and a
  `--replayx-record` flag.

[Unreleased]: https://github.com/your-org/replayx/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/replayx/releases/tag/v0.1.0
