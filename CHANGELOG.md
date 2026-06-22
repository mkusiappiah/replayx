# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-06-22

### Added
- Inline stubs through `use_stubs`. Declare responses in code with a
  `StubRouter` (`router.get(url).respond(json=...)`), no cassette and no
  network. Unmatched requests raise `UnhandledStubError`. Routes track calls
  via `route.call_count`. Works for sync and async clients.

### Changed
- Extracted the httpx interception into a shared internal module used by both
  `use_cassette` and `use_stubs`. No change to public behaviour.

## [0.3.0] - 2026-06-22

### Added
- `graphql` request matcher. It compares GraphQL POST bodies on operation name,
  variables, and a whitespace-normalized query, so formatting differences do not
  break matching. Non-GraphQL bodies fall back to an exact comparison.

## [0.2.0] - 2026-06-22

### Added
- Content-encoding fidelity. replayx keeps the `Content-Encoding` header and
  re-encodes the body on replay (gzip and deflate built in, brotli and zstd
  through optional dependencies), so replayed responses match live ones.

### Changed
- Recorded responses keep the `Content-Encoding` header instead of dropping it.
  Bodies stay stored decoded, so cassettes remain readable. v0.1.0 cassettes
  still replay unchanged.

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

[Unreleased]: https://github.com/mkusiappiah/replayx/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/mkusiappiah/replayx/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/mkusiappiah/replayx/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/mkusiappiah/replayx/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mkusiappiah/replayx/releases/tag/v0.1.0
