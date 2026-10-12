import copy

import pytest

from cyclone2 import keys, profile
from cyclone2.protocol import PROFILE_SIZE
from fake_device import load_records

RECORDS = {n: bytes(b) for n, b in load_records().items() if n != 32}


@pytest.fixture(params=sorted(RECORDS))
def base(request):
    return RECORDS[request.param]


def test_fields_do_not_overlap_and_fit():
    used = bytearray(PROFILE_SIZE)
    for path, o, kind in profile.FIELDS:
        for i in range(o, o + profile.SIZE[kind]):
            assert not used[i], (path, i)
            used[i] = 1
    assert len(used) == PROFILE_SIZE


def test_round_trip_every_record(base):
    doc = profile.decode(base)
    assert profile.encode(doc, base) == base                       # unchanged doc -> identical bytes
    blank = bytes(PROFILE_SIZE)
    assert profile.decode(profile.encode(doc, blank)) == doc       # and the doc alone rebuilds the same doc


def test_decode_wrong_size():
    with pytest.raises(ValueError, match="680 bytes, got 3"):
        profile.decode(b"abc")


def test_partial_doc_changes_only_its_bytes(base):
    new = profile.encode({"motors": {"left": 7}}, base)
    assert new[32] == 7 and new[33:] == base[33:] and new[:32] == base[:32]
    new = profile.encode({"sticks": {"right": {"output": {"target": 4}}}}, base)
    assert profile.decode(new)["sticks"]["right"]["output"]["target"] == 4
    assert profile.changed_span(base, new) in {(o, o + 1) for o in range(550 + 32 + 20, 550 + 32 + 28)} | {None}


def test_partial_doc_ignores_missing_and_non_dict_nodes(base):
    assert profile.encode({}, base) == base
    assert profile.encode({"motors": None}, base) == base
    assert profile.encode({"buttons": {"A": 3}}, base) == base


def test_name_truncated_and_stripped(base):
    new = profile.encode({"name": "é" * 40}, base)
    assert profile.decode(new)["name"] == "é" * 15                 # 31 bytes max, cut on a whole char
    assert new[31] == 0
    assert profile.decode(profile.encode({"name": "  Racing  "}, base))["name"] == "Racing"


def test_keys_field(base):
    d = profile.decode(profile.encode({"buttons": {"A": {"map": ["B", "KB_ESC", "0xee"]}}}, base))
    assert d["buttons"]["A"]["map"] == ["B", "KB_ESC", "0xee"]
    d = profile.decode(profile.encode({"buttons": {"A": {"map": []}}}, base))
    assert d["buttons"]["A"]["map"] == []
    with pytest.raises(ValueError, match="at most 3 keys"):
        profile.encode({"buttons": {"A": {"map": ["A", "B", "X", "Y"]}}}, base)
    with pytest.raises(ValueError, match="unknown key"):
        profile.encode({"buttons": {"A": {"map": ["Nope"]}}}, base)


def test_scalar_kinds(base):
    doc = {"options": {"shift": True, "report_rate": 3}, "audio": {"volume": 9},
           "motion": {"aim": {"trigger_key": "RT", "deadzone": [1, 2, 3, 4], "deadzone_on": False}},
           "triggers": {"LT": {"hair_trigger": {"on": True, "mode": 2, "start": 4, "end": 5}}}}
    d = profile.decode(profile.encode(doc, base))
    assert d["options"]["shift"] is True and d["options"]["report_rate"] == 3 and d["audio"]["volume"] == 9
    assert d["motion"]["aim"]["trigger_key"] == "RT" and d["motion"]["aim"]["deadzone"] == [1, 2, 3, 4]
    assert d["motion"]["aim"]["deadzone_on"] is False
    assert d["triggers"]["LT"]["hair_trigger"] == {"on": True, "mode": 2, "start": 4, "end": 5}
    off = {"triggers": {"LT": {"hair_trigger": {"on": False, "mode": 1, "start": 4, "end": 5}}}}
    assert profile.decode(profile.encode(off, base))["triggers"]["LT"]["hair_trigger"]["on"] is False
    mode1 = {"triggers": {"LT": {"hair_trigger": {"on": True, "mode": 1, "start": 4, "end": 5}}}}
    assert profile.decode(profile.encode(mode1, base))["triggers"]["LT"]["hair_trigger"]["mode"] == 1


def test_curve_and_wheel_fields(base):
    c = {"on": False, "type": 2, "curvature": 50, "points": [[0, 0], [1, 2], [3, 4], [5, 6], [255, 255]]}
    wheel = {"up": "KB_W", "down": "KB_S", "left": "", "right": "KB_D", "center": ""}
    d = profile.decode(profile.encode({"sticks": {"left": {"curve": c, "output": {"wheel": wheel}}}}, base))
    assert d["sticks"]["left"]["curve"] == c and d["sticks"]["left"]["output"]["wheel"] == wheel


def test_value_validation(base):
    with pytest.raises(ValueError, match="bad value"):
        profile.encode({"motors": {"left": 300}}, base)
    with pytest.raises(ValueError, match="bad value"):
        profile.encode({"motors": {"left": -1}}, base)
    with pytest.raises(ValueError, match="bad value"):
        profile.encode({"sticks": {"left": {"deadzone": [1, 2, 3]}}}, base)


def test_macro_round_trip_and_validation(base):
    steps = [{"key": "KB_A", "hold": 300, "delay": 1000}, {"key": "A", "hold": 1, "delay": 2}]
    m = {"on": True, "press_to_trigger": True, "cycle": True, "cycle_time": 513, "steps": steps}
    d = profile.decode(profile.encode({"macros": {"L4": m}}, base))
    assert d["macros"]["L4"] == m
    assert d["macros"]["R4"] == profile.decode(base)["macros"]["R4"]
    off = profile.decode(profile.encode({"macros": {"L4": {**m, "steps": []}}}, base))["macros"]["L4"]
    assert off["on"] is False and off["steps"] == []               # no steps -> never enabled
    full = [{"key": "KB_A", "hold": 5, "delay": 9}] * profile.STEPS
    d = profile.decode(profile.encode({"macros": {"L4": {**m, "steps": full}}}, base))["macros"]["L4"]
    assert len(d["steps"]) == 30 and d["steps"][-1]["delay"] == 0   # the 30th step has no delay slot
    with pytest.raises(ValueError, match="at most 30"):
        profile.encode({"macros": {"L4": {**m, "steps": full + full[:1]}}}, base)
    for field, bad in (("hold", 70000), ("delay", -1)):
        with pytest.raises(ValueError, match="bad value"):
            profile.encode({"macros": {"L4": {**m, "steps": [{"key": "A", "hold": 1, "delay": 1, field: bad}]}}}, base)
    with pytest.raises(ValueError, match="bad value"):
        profile.encode({"macros": {"L4": {**m, "cycle_time": 65536}}}, base)


def test_macro_with_blank_key_step(base):
    m = {"on": True, "press_to_trigger": False, "cycle": False, "cycle_time": 0,
         "steps": [{"key": "", "hold": 1, "delay": 1}]}
    d = profile.decode(profile.encode({"macros": {"R4": m}}, base))["macros"]["R4"]
    assert d["steps"][0]["key"] == keys.name(0)


def test_decode_clamps_macro_step_count(base):
    raw = bytearray(base)
    raw[176 + 7 + 3] = 200
    assert len(profile.decode(bytes(raw))["macros"]["L4"]["steps"]) == 30


def test_changed_span():
    assert profile.changed_span(b"abc", b"abc") is None
    assert profile.changed_span(b"abcde", b"aXcdY") == (1, 5)


def test_curve_and_inverse():
    assert profile.curve([0, 100, 0, 100]) == {"on": True, "type": 0, "curvature": 100,
                                               "points": [[0, 0], [64, 64], [128, 128], [191, 191], [255, 255]]}
    assert profile.curve([0, 100, 0, 100], type=3, curvature=7)["type"] == 3
    for dz in ([0, 100, 0, 100], [10, 100, 0, 100], [5, 95, 20, 80], [30, 60, 10, 90]):
        for pts in [((25, 25), (50, 50), (75, 75)), ((40, 20), (50, 60), (80, 90))]:
            pts = [(max(dz[0], x), max(dz[2], y)) for x, y in pts]
            back = profile.curve_percent(profile.curve(dz, pts), dz)
            for (x, y), (bx, by) in zip(pts, back):
                assert abs(x - bx) <= max(1, 100 / max(dz[1] - dz[0], 1)) and abs(y - by) <= max(1, 100 / max(dz[3] - dz[2], 1))


def test_curve_degenerate_range():
    assert profile.curve([50, 50, 0, 0], [(50, 0)] * 3)["points"][1] == [0, 0]   # no division by zero


def test_reset_all_matches_app_defaults(base):
    d = profile.reset(profile.decode(base))
    for b in d["buttons"].values():
        assert (b["map"], b["turbo"], b["turbo_speed"], b["toggle"]) == ([], False, 0, False)
    for m in d["macros"].values():
        assert m == {"on": False, "press_to_trigger": False, "cycle": False, "cycle_time": 0, "steps": []}
    for i, s in enumerate(d["sticks"].values()):
        assert (s["on"], s["square"], s["deadzone_on"], s["deadzone"]) == (True, False, True, [10, 100, 0, 100])
        assert s["curve"] == profile.curve([10, 100, 0, 100]) and s["output"]["target"] == i + 1
        assert (s["output"]["axis_ratio"], s["output"]["mouse_dpi"]) == (50, 50)
    for i, s in enumerate(d["motion"].values()):
        assert (s["activation"], s["trigger_key"], s["axes"]) == (0, "None", 2)
        assert s["output"]["target"] == i + 1 and s["deadzone"] == [10, 100, 0, 100]
    for t in d["triggers"].values():
        assert t["deadzone"] == [5, 95, 0, 100] and t["curve"] == profile.curve([5, 95, 0, 100])
        assert t["hair_trigger"]["on"] is False and t["hair_trigger"]["mode"] == 1
    assert d["motors"] == {"left": 75, "right": 75, "lt": 75, "rt": 75}
    assert profile.decode(profile.encode(d, base)) == d            # defaults are encodable


@pytest.mark.parametrize("part,keys_", [("mapping", {"buttons", "macros"}), ("sticks", {"sticks"}),
                                         ("triggers", {"triggers"}), ("motion", {"motion"}), ("motors", {"motors"})])
def test_reset_part_touches_only_that_part(base, part, keys_):
    doc = profile.decode(base)
    before = copy.deepcopy(doc)
    out = profile.reset(doc, part)
    assert doc == before                                           # input untouched
    assert {k for k in doc if out[k] != doc[k]} <= keys_
