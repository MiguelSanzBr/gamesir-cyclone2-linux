import pytest

from cyclone2 import keys


def test_keyboard_is_contiguous_50_to_154():
    assert sorted(keys.KEYBOARD) == list(range(50, 155))
    assert keys.KEYBOARD[50] == "ESC" and keys.KEYBOARD[154] == "VOLDOWN"


def test_codes_unique_and_round_trip():
    assert len(keys.NAMES) == len(keys.CODES)         # no name used twice
    for c, n in keys.CODES.items():
        assert keys.code(keys.name(c)) == c and keys.NAMES[n] == c
    assert keys.name(keys.NONE) == "None" and keys.code("KB_A") == keys.NAMES["KB_A"]


def test_unknown_codes_survive():
    assert keys.name(0xEE) == "0xee" and keys.code("0xee") == 0xEE


def test_code_rejects_unknown():
    for bad in ("nope", "KB_", 5, None):
        with pytest.raises(ValueError, match="unknown key"):
            keys.code(bad)


def test_button_tables():
    assert len(keys.BUTTONS) == 16 and all(b in keys.NAMES for b in keys.BUTTONS + keys.PADDLES + keys.TRIGGERS)
    assert all(t in keys.NAMES for t in keys.TARGETS)
