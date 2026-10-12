import pytest

from cyclone2 import protocol as p
from fake_device import FakeController


def test_size_of_and_command():
    assert p.size_of(p.LIGHTS) == p.LIGHT_SIZE == 635
    assert {p.size_of(n) for n in (1, 2, 3, 4, p.SHIFT)} == {680}
    c = p.command(p.SWITCH, 3)
    assert c == bytes([0x0F, 7, 3]) + bytes(61) and len(c) == p.REPORT_SIZE


@pytest.mark.parametrize("n", [1, 5, 32])
def test_read_requests_cover_record(n):
    reqs = p.read_requests(n)
    size = p.size_of(n)
    assert len(reqs) == -(-size // p.CHUNK)
    covered = 0
    for i, r in enumerate(reqs):
        assert r[:3] == bytes([p.OUT, p.READ, n])
        assert r[3] << 8 | r[4] == i * p.CHUNK == covered
        assert r[5] == min(p.CHUNK, size - covered)
        covered += r[5]
    assert covered == size


def test_read_requests_range():
    reqs = p.read_requests(1, 100, 130)
    assert [(r[3] << 8 | r[4], r[5]) for r in reqs] == [(100, 30)]
    reqs = p.read_requests(1, 100, 200)
    assert [(r[3] << 8 | r[4], r[5]) for r in reqs] == [(100, 58), (158, 42)]


def test_write_requests_chunks_and_offsets():
    data = bytes(range(150))
    reqs = p.write_requests(2, data, offset=300)
    assert [(r[3] << 8 | r[4], r[5]) for r in reqs] == [(300, 58), (358, 58), (416, 34)]
    assert all(r[:3] == bytes([p.OUT, p.WRITE, 2]) and len(r) == p.REPORT_SIZE for r in reqs)
    assert b"".join(r[6:6 + r[5]] for r in reqs) == data
    assert p.write_requests(1, b"") == []


def test_kind_busy_chunk():
    ans = lambda *a: bytes([p.ANSWER, *a]).ljust(64, b"\0")
    assert p.kind(ans(p.ACK, 0)) == p.ACK
    assert p.kind(bytes([p.STATE, 5])) is None
    assert p.kind(b"\x10") is None and p.kind(b"") is None
    assert p.busy(ans(p.ACK, 1)) and not p.busy(ans(p.ACK, 0)) and not p.busy(ans(p.READ_ACK, 1))
    assert p.chunk(ans(p.READ_ACK, 1, 1, 2, 3, 9, 8, 7, 6)) == (1, 258, b"\x09\x08\x07")


def test_version_and_firmware():
    assert p.version(b"3\x005\x006") == "3.5.6"
    assert p.version(b"1\x002\x00 \x00") == "1.2"
    assert p.version(b"\0\0\0") == ""
    r = bytes([p.ANSWER, p.FIRMWARE_ACK, 0, 0]) + b"3\x005\x006" + bytes(3) + b"1\x002\x00\x00\x00" + bytes(47)
    assert p.firmware(r) == ("3.5.6", "1.2")


def test_state_rejects_other_reports():
    assert p.state(bytes(10)) is None
    assert p.state(bytes([p.ANSWER]) + bytes(63)) is None


def test_state_decodes_everything():
    f = FakeController.state_report
    pressed = {"A", "X", "LB", "RT", "View", "Home", "L4", "M", "Up", "Right"}
    s = p.state(f(None, pressed=pressed, lt=200, rt=17, left=(0, 255), right=(128, 64), battery=55))
    assert s["pressed"] == pressed
    assert (s["lt"], s["rt"], s["battery"]) == (200, 17, 55)
    assert s["left"] == (-1.0, 1.0) and s["right"] == (0.0, -0.5)
    assert s["charging"] == s["animation"] == 0


def test_state_every_button_and_direction():
    f = FakeController.state_report
    for names in p.STATE_BITS.values():
        for n in names.values():
            assert p.state(f(None, pressed={n}))["pressed"] == {n}
    for d in ("Up", "Down", "Left", "Right"):
        assert p.state(f(None, pressed={d}))["pressed"] == {d}
    assert p.state(f(None, pressed={"Down", "Left"}))["pressed"] == {"Down", "Left"}
    assert p.state(f(None))["pressed"] == set()      # hat neutral (0x0F) maps to nothing
