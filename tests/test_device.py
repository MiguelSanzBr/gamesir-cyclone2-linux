import os
import time

import pytest

from cyclone2 import device, discovery, protocol as p
from fake_device import FakeController


@pytest.fixture
def dev(fake, monkeypatch):
    monkeypatch.setattr(device, "RESEND", 0.02)
    d = device.Device()
    yield d
    d.close()


def test_open_sends_heartbeat(fake, dev):
    assert (dev.path, dev.pid) == (fake.path, fake.pid)
    time.sleep(0.05)
    assert len(fake.commands(p.HEARTBEAT)) == 1


def test_open_by_path(fake, monkeypatch, tmp_path):
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([("/dev/hidraw-x", 1), (fake.path, 2)]))
    d = device.Device(fake.path)
    assert (d.path, d.pid) == (fake.path, 2)
    d.close()
    other = tmp_path / "node"                    # a path discovery does not know is opened as given, pid 0
    other.touch()
    d = device.Device(str(other))
    assert (d.path, d.pid) == (str(other), 0)
    d.close()


def test_no_controller(monkeypatch):
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([]))
    with pytest.raises(SystemExit, match="not found"):
        device.Device()


def test_permission_denied(fake, monkeypatch):
    def deny(*a):
        raise PermissionError
    monkeypatch.setattr(os, "open", deny)
    with pytest.raises(SystemExit, match="permission denied on /dev/hidraw-fake"):
        device.Device()


def test_read_times_out(dev):
    assert dev.read(0.01) is None
    assert dev.read(-1) is None                  # negative timeouts are clamped


def test_firmware_current_switch(fake, dev):
    assert dev.firmware() == ("3.5.6", "")
    assert dev.current_profile() == 1
    fake.current = 0
    assert dev.current_profile() == 1            # 0 counts as 1
    dev.switch_profile(3)
    assert fake.current == 3 and dev.current_profile() == 3


def test_request_resends_on_silence(fake, dev):
    fake.drop = 2
    assert dev.current_profile() == 1
    assert len(fake.commands(p.CURRENT)) == 3


def test_request_resends_on_busy(fake, dev):
    fake.busy = 3
    dev.switch_profile(2)
    assert len(fake.commands(p.SWITCH)) == 4 and fake.current == 2


def test_request_gives_up(fake, dev, monkeypatch):
    monkeypatch.setattr(device, "TRIES", 3)
    fake.silent.add(p.CURRENT)
    with pytest.raises(IOError, match="no answer to command 11"):
        dev.current_profile()
    assert len(fake.commands(p.CURRENT)) == 3


def test_request_skips_unrelated_answers(fake, dev):
    fake.push(bytes([p.ANSWER, p.ACK, 0]).ljust(64, b"\0"))      # not the kind we want
    assert dev.current_profile() == 1
    assert len(fake.commands(p.CURRENT)) == 1


def test_request_match_filter(fake, dev):
    fake.push(bytes([p.ANSWER, p.CURRENT_ACK, 9]).ljust(64, b"\0"))
    r = dev.request(p.command(p.CURRENT), p.CURRENT_ACK, lambda r: r[2] == 1)
    assert r[2] == 1


def test_state(fake, dev):
    assert dev.state(0.02) is None
    fake.push(bytes([p.ANSWER, p.ACK, 0]).ljust(64, b"\0"))          # not a state report: skipped
    fake.push(fake.state_report(pressed={"B"}, lt=9))
    s = dev.state()
    assert s["pressed"] == {"B"} and s["lt"] == 9


def test_vibrate_and_light_preview(fake, dev):
    dev.vibrate(10, 200)
    dev.light_preview(True)
    dev.light_preview(False, 4)
    time.sleep(0.05)
    assert fake.commands(p.VIBRATE)[0][2:6] == bytes([102, 85, 10, 200])
    assert [r[2:4] for r in fake.commands(p.LIGHT)] == [bytes([1, 1]), bytes([0, 4])]


@pytest.mark.parametrize("n", [1, 5, 32])
def test_read_profile_matches_firmware(fake, dev, n):
    assert dev.read_profile(n) == bytes(fake.records[n])


def test_write_profile_whole_and_range(fake, dev):
    new = bytearray(fake.records[2])
    new[0:4] = b"abcd"
    new[300:420] = bytes(range(120))
    dev.write_profile(2, bytes(new))
    assert fake.records[2] == new
    assert len(fake.commands(p.WRITE)) == -(-680 // 58)
    fake.log.clear()
    new[100] ^= 0xFF
    dev.write_profile(2, bytes(new), 100, 101)
    assert fake.records[2] == new and len(fake.commands(p.WRITE)) == 1


@pytest.mark.parametrize("args", [(b"short",), (bytes(680), 5, 5), (bytes(680), -1, 3), (bytes(680), 0, 681)])
def test_write_profile_rejects_bad_ranges(dev, args):
    with pytest.raises(AssertionError):
        dev.write_profile(1, *args)
