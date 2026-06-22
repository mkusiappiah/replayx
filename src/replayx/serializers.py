"""Cassette serialization backends (JSON built-in, YAML optional)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from .errors import CassetteFormatError


class Serializer(Protocol):
    """A cassette serializer turns a plain dict into text and back."""

    name: str

    def dumps(self, data: dict[str, Any]) -> str: ...

    def loads(self, text: str) -> dict[str, Any]: ...


class JSONSerializer:
    """Human-readable, dependency-free JSON serializer (the default)."""

    name = "json"

    def dumps(self, data: dict[str, Any]) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    def loads(self, text: str) -> dict[str, Any]:
        try:
            result = json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover - thin wrapper
            raise CassetteFormatError(f"invalid JSON cassette: {exc}") from exc
        if not isinstance(result, dict):
            raise CassetteFormatError("cassette root must be a JSON object")
        return result


class YAMLSerializer:
    """YAML serializer. Requires the optional ``pyyaml`` dependency."""

    name = "yaml"

    def __init__(self) -> None:
        try:
            import yaml  # noqa: F401
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise CassetteFormatError(
                "YAML cassettes require PyYAML. Install it with: pip install 'replayx[yaml]'"
            ) from exc

    def dumps(self, data: dict[str, Any]) -> str:
        import yaml

        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    def loads(self, text: str) -> dict[str, Any]:
        import yaml

        try:
            result = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise CassetteFormatError(f"invalid YAML cassette: {exc}") from exc
        if not isinstance(result, dict):
            raise CassetteFormatError("cassette root must be a mapping")
        return result


def serializer_for_path(path: Path) -> Serializer:
    """Pick a serializer based on the cassette file extension."""

    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        return YAMLSerializer()
    return JSONSerializer()
