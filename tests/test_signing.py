import re

import pytest

from tetris_ui import signing

ID = "0123456789abcdef0123456789abcdef"
OTHER_ID = "fedcba9876543210fedcba9876543210"


def records() -> list[dict]:
    return [
        {"name": "Иван", "score": 1200, "lines": 13, "level": 1},
        {"name": "Ann", "score": 340, "lines": 3, "level": 0},
    ]


def test_signature_is_64_lowercase_hex_digits():
    assert re.fullmatch(r"[0-9a-f]{64}", signing.signature(ID, records()))


def test_signature_is_pinned():
    # Changing the key or the signed form must be a deliberate new format, not an accident.
    one = [{"name": "A", "score": 100, "lines": 1, "level": 0}]
    assert signing.signature(ID, one) == (
        "2b1d90cc887a4d0fbf9928ae2bae839601a77fdf41a240059fa910124b8041a8"
    )


def test_other_installation_gives_another_signature():
    assert signing.signature(OTHER_ID, records()) != signing.signature(ID, records())


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize(("field", "value"), [
    ("name", "Ivan"), ("score", 999999), ("lines", 14), ("level", 2),
])
def test_any_changed_field_changes_the_signature(index, field, value):
    changed = records()
    changed[index][field] = value
    assert signing.signature(ID, changed) != signing.signature(ID, records())


def test_swapped_records_change_the_signature():
    assert signing.signature(ID, records()[::-1]) != signing.signature(ID, records())


def test_extra_record_changes_the_signature():
    more = records() + [{"name": "Zed", "score": 10, "lines": 0, "level": 0}]
    assert signing.signature(ID, more) != signing.signature(ID, records())


def test_key_order_in_a_record_does_not_matter():
    reordered = [{key: record[key] for key in reversed(record)} for record in records()]
    assert list(reordered[0]) != list(records()[0])
    assert signing.signature(ID, reordered) == signing.signature(ID, records())


def test_the_right_signature_is_valid():
    assert signing.is_valid(signing.signature(ID, records()), ID, records())


@pytest.mark.parametrize("sig", [
    None,
    12345,
    "",
    "ё" * 64,  # not ASCII: must not raise
    "\ud800",  # a lone surrogate, as json.loads can produce
])
def test_is_valid_rejects_what_is_not_a_signature(sig):
    assert not signing.is_valid(sig, ID, records())


def test_is_valid_rejects_an_upper_case_signature():
    assert not signing.is_valid(signing.signature(ID, records()).upper(), ID, records())


def test_is_valid_rejects_another_installation():
    assert not signing.is_valid(signing.signature(OTHER_ID, records()), ID, records())
