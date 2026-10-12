import copy
import re

import pytest

from cyclone2 import light
from fake_device import load_records

BASE = bytes(load_records()[32])


@pytest.fixture
def doc():
    return light.decode(BASE)


def test_round_trip():
    assert light.encode(light.decode(BASE), BASE) == BASE
    assert light.decode(light.encode(light.decode(BASE), bytes(635))) == light.decode(BASE)


def test_decode_wrong_size():
    with pytest.raises(ValueError, match="635 bytes, got 2"):
        light.decode(b"ab")


def test_decode_clamps():
    raw = bytearray(BASE)
    raw[0] = 9                                  # active animation out of range -> 0
    raw[1 + 2] = 40                             # speed byte > 20 -> speed 0
    raw[1 + 3] = 250                            # brightness > 100 -> 100
    d = light.decode(bytes(raw))
    assert d["active"] == 0 and d["animations"][0]["speed"] == 0 and d["animations"][0]["brightness"] == 100


def test_encode_changes_only_described_bytes(doc):
    doc["animations"][2]["brightness"] = 55
    doc["profile_led"] = "#010203"
    new = light.encode(doc, BASE)
    diff = {i for i in range(635) if new[i] != BASE[i]}
    assert diff <= {1 + 124 * 2 + 3, 623, 624, 625}
    assert new[1 + 124 * 2 + 3] == 55 and new[623:626] == b"\x01\x02\x03"
    assert new[628:] == BASE[628:]              # reserved tail untouched


def test_speed_stored_inverted_and_clamped(doc):
    for given, stored in ((15, 5), (0, 20), (99, 0), (-4, 20)):
        doc["animations"][1]["speed"] = given
        assert light.encode(doc, BASE)[1 + 124 + 2] == stored
    doc["animations"][1]["speed"] = 15
    assert light.decode(light.encode(doc, BASE))["animations"][1]["speed"] == 15


def test_presets_shape():
    assert set(light.PRESETS) == {"Flow", "Rainbow", "Pulse", "Standoff", "Alarm", "Disable"}
    for name, pr in light.PRESETS.items():
        assert 1 <= len(pr["colors"]) <= 8 and 0 <= pr["speed"] <= light.MAX_SPEED, name
        for frame in pr["colors"]:
            assert set(frame) == set(light.LEDS)
            assert all(re.fullmatch(r"#[0-9a-f]{6}", c) for c in frame.values()), name
    assert len(light.PRESETS["Flow"]["colors"]) == 5 and len(light.PRESETS["Alarm"]["colors"]) == 6
    f0 = light.PRESETS["Flow"]["colors"][0]
    assert f0["home"] == "#ff0000" and f0["upper_left"] == "#0000ff" and f0["lower_left"] == "#00ff00"


def test_apply_preset_to_active_animation(doc):
    before = copy.deepcopy(doc)
    out = light.apply_preset(doc, "Pulse")
    assert doc == before
    a = out["animations"][doc["active"]]
    assert a["frames"] == 2 and a["speed"] == 5 and len(a["colors"]) == 8
    assert a["colors"][:2] == light.PRESETS["Pulse"]["colors"] and a["colors"][2:] == [light.BLACK] * 6
    assert a["brightness"] == doc["animations"][doc["active"]]["brightness"]
    other = [i for i in range(5) if i != doc["active"]]
    assert all(out["animations"][i] == doc["animations"][i] for i in other)
    assert light.decode(light.encode(out, BASE))["animations"][doc["active"]] == a


def test_apply_preset_to_given_animation_incl_zero(doc):
    doc["active"] = 3
    out = light.apply_preset(doc, "Standoff", animation=0)
    assert out["animations"][0]["frames"] == 1 and out["animations"][3] == doc["animations"][3]


def test_solid(doc):
    out = light.solid(doc, "#123456", animation=2)
    a = out["animations"][2]
    assert a["frames"] == 1 and a["colors"][0] == dict.fromkeys(light.LEDS, "#123456")
    assert a["colors"][1:] == [light.BLACK] * 7
    out = light.solid(doc, "#654321")
    assert out["animations"][doc["active"]]["colors"][0]["home"] == "#654321"
    assert doc["animations"][2] != a
