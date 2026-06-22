"""Content-encoding support for faithful replay.

replayx stores response bodies decoded, so cassettes stay readable in code
review. On replay, replayx re-encodes the body to match the recorded
``Content-Encoding`` header. httpx then decodes it the same way a live response
would, so ``response.content`` and ``response.headers`` match the real call.

gzip and deflate work with the standard library. brotli needs ``brotli`` or
``brotlicffi``. zstd needs ``zstandard``. When a codec is missing, replayx drops
the encoding header and serves the decoded body, so replay still works.
"""

from __future__ import annotations

import gzip
import zlib


def encode_content(data: bytes, encoding: str) -> bytes | None:
    """Encode ``data`` for the given Content-Encoding.

    Returns the encoded bytes, or ``None`` when the codec is unknown or its
    optional dependency is not installed.
    """

    enc = encoding.strip().lower()
    if enc in ("", "identity"):
        return data
    if enc in ("gzip", "x-gzip"):
        return gzip.compress(data)
    if enc == "deflate":
        return zlib.compress(data)
    if enc == "br":
        return _brotli_compress(data)
    if enc == "zstd":
        return _zstd_compress(data)
    return None


def _brotli_compress(data: bytes) -> bytes | None:
    try:
        import brotli
    except ImportError:
        try:
            import brotlicffi as brotli
        except ImportError:
            return None
    compressed: bytes = brotli.compress(data)
    return compressed


def _zstd_compress(data: bytes) -> bytes | None:
    try:
        import zstandard
    except ImportError:
        return None
    compressed: bytes = zstandard.ZstdCompressor().compress(data)
    return compressed
