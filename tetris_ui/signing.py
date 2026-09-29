"""The signature of the high score table: HMAC-SHA256 with a key built into the game, over
the format number, the installation ID and the records, without pygame.

The key ships inside the game, so the signature stops edits in a text editor and files
copied from another installation, not someone who reads the program. Changing KEY or the
canonical form in signature() makes every saved table fail the check, so it needs a new
FORMAT_VERSION and an OpenSpec change of its own.
"""

from __future__ import annotations

import hashlib
import hmac
import json

FORMAT_VERSION = 2

# Generated once with secrets.token_bytes(32).hex(); see the module docstring before changing it.
KEY = bytes.fromhex("8dc24ef9cc23b0b6f9fe30b8d172199f001ee96971c3dc65267f980424acd0de")


def signature(install_id: str, records: object) -> str:
    """The signature of the records for one installation, as 64 lowercase hex digits.

    The signed data is the canonical JSON of the format number, the ID and the records
    (sorted keys, no spaces), so neither the indentation of the file nor the order of the
    keys in it matters, while any change to a value, a record or their order does.
    Changing this form needs a new FORMAT_VERSION.
    """
    payload = json.dumps(
        {"version": FORMAT_VERSION, "install_id": install_id, "entries": records},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hmac.new(KEY, payload, hashlib.sha256).hexdigest()


def is_valid(sig: object, install_id: str, records: object) -> bool:
    """Whether sig is the signature of the records for this installation; the comparison
    takes the same time wherever the first difference is."""
    if not isinstance(sig, str):
        return False
    # Bytes, because compare_digest refuses str with non-ASCII characters.
    expected = signature(install_id, records).encode("ascii")
    return hmac.compare_digest(sig.encode("utf-8", "replace"), expected)
