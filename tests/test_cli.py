import json
import threading
import time
import types

import pytest

from cyclone2 import cli, device, discovery, light, profile
from cyclone2 import protocol as p


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    monkeypatch.setattr(device, "RESEND", 0.02)


def run(*args):
    return cli.main(list(args))


def test_list_with_and_without_devices(fake, capsys, monkeypatch):
    assert run("list") == 0
    assert capsys.readouterr().out == "/dev/hidraw-fake  1053  Cyclone 2 (cabo, ADC)\n"
    fake.pid = 0x1234
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([(fake.path, fake.pid)]))
    run("list")
    assert "1234  GameSir" in capsys.readouterr().out
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([]))
    run("list")
    assert capsys.readouterr().out == "no GameSir Cyclone 2 found\n"


def test_device_missing_exits(monkeypatch):
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([]))
    with pytest.raises(SystemExit, match="not found"):
        run("info")


def test_info(fake, capsys):
    threading.Timer(0.1, fake.push, [fake.state_report(battery=80)]).start()   # state() waits for it
    run("--device", fake.path, "info")
    out = capsys.readouterr().out
    assert f"device:   {fake.path} (Cyclone 2 (cabo, ADC))" in out and "firmware: 3.5.6\n" in out
    assert "profile:  1" in out and "battery:  80%\n" in out


def test_info_charging_dongle_unknown_pid(fake, capsys, monkeypatch):
    fake.pid = 0x9999
    monkeypatch.setattr(device.Device, "firmware", lambda self: ("1.0", "2.0"))
    monkeypatch.setattr(device.Device, "state", lambda self, t=0.5: {"battery": 5, "charging": 1})
    run("info")
    out = capsys.readouterr().out
    assert "(0x9999)" in out and "firmware: 1.0 (dongle 2.0)" in out and "5% (charging)" in out


def test_info_without_state(fake, capsys, monkeypatch):
    monkeypatch.setattr(device.Device, "state", lambda self, t=0.5: None)
    run("info")
    assert "battery" not in capsys.readouterr().out


def test_dump_active_and_selected(fake, capsys):
    fake.current = 2
    run("dump")
    assert json.loads(capsys.readouterr().out) == profile.decode(bytes(fake.records[2]))
    run("dump", "-p", "5")
    assert json.loads(capsys.readouterr().out) == profile.decode(bytes(fake.records[5]))


def test_dump_lights(fake, capsys):
    run("dump", "--lights")
    assert json.loads(capsys.readouterr().out) == light.decode(bytes(fake.records[32]))


def test_apply_partial_json(fake, capsys, tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"name": "Racing", "motors": {"left": 20}}))
    before = bytes(fake.records[3])
    run("apply", "-p", "3", str(f))
    assert capsys.readouterr().out == "profile 3: 33 bytes written\n"
    after = bytes(fake.records[3])
    d = profile.decode(after)
    assert d["name"] == "Racing" and d["motors"]["left"] == 20
    assert {i for i in range(680) if before[i] != after[i]} <= set(range(33))


def test_apply_to_active_profile_nothing_changed(fake, capsys, tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps(profile.decode(bytes(fake.records[1]))))
    run("apply", str(f))
    assert capsys.readouterr().out == "profile 1: 0 bytes written\n"
    assert not fake.commands(p.WRITE)


def test_apply_lights_partial(fake, capsys, tmp_path):
    f = tmp_path / "l.json"
    f.write_text(json.dumps({"standby": 10, "raise_to_wake": False}))
    run("apply", "--lights", str(f))
    d = light.decode(bytes(fake.records[32]))
    assert d["standby"] == 10 and d["raise_to_wake"] is False and d["audio_reactive"] is True
    assert capsys.readouterr().out == "profile 32: 2 bytes written\n"


def test_apply_verification_failure(fake, tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"name": "Nope"}))
    fake.corrupt = True
    with pytest.raises(SystemExit, match="verification failed"):
        run("apply", "-p", "1", str(f))


def test_switch(fake, capsys):
    run("switch", "4")
    assert fake.current == 4 and capsys.readouterr().out == "active profile: 4\n"


def test_reset_all_and_part(fake, capsys):
    run("reset", "-p", "2")
    assert "profile 2:" in capsys.readouterr().out
    d = profile.decode(bytes(fake.records[2]))
    assert d == profile.reset(profile.decode(bytes(fake.records[2])))
    fake.records[1][32:36] = bytes([1, 2, 3, 4])
    run("reset", "--part", "motors")                 # active profile (1)
    assert profile.decode(bytes(fake.records[1]))["motors"] == dict.fromkeys(("left", "right", "lt", "rt"), 75)


def test_light_preset_color_brightness_speed_animation(fake, capsys):
    run("light", "--preset", "Pulse", "--animation", "1", "--brightness", "150", "--speed", "7")
    d = light.decode(bytes(fake.records[32]))
    a = d["animations"][1]
    assert d["active"] == 1 and a["frames"] == 2 and a["brightness"] == 100 and a["speed"] == 7
    assert a["colors"][0] == light.PRESETS["Pulse"]["colors"][0]
    assert capsys.readouterr().out.startswith("lighting: ")
    run("light", "--color", "#00FFAA", "--brightness", "-5")
    a = light.decode(bytes(fake.records[32]))["animations"][1]
    assert a["frames"] == 1 and a["colors"][0]["home"] == "#00ffaa" and a["brightness"] == 0
    run("light", "--color", "FF0000", "--animation", "0")
    d = light.decode(bytes(fake.records[32]))
    assert d["active"] == 0 and d["animations"][0]["colors"][0]["lower_left"] == "#ff0000"


def test_light_nothing_to_do(fake, capsys):
    run("light")
    assert capsys.readouterr().out == "lighting: 0 bytes written\n" and not fake.commands(p.WRITE)


def test_vibrate(fake, monkeypatch):
    slept = []
    monkeypatch.setattr(cli, "time", types.SimpleNamespace(sleep=slept.append))
    run("vibrate", "--left", "10", "--right", "20", "--time", "0.5")
    time.sleep(0.05)
    assert slept == [0.5]
    assert [r[4:6] for r in fake.commands(p.VIBRATE)] == [bytes([10, 20]), bytes([0, 0])]
    run("vibrate")
    time.sleep(0.05)
    assert fake.commands(p.VIBRATE)[2][4:6] == bytes([160, 160])


def test_backup_restore_round_trip(fake, capsys, tmp_path):
    f = tmp_path / "b.bin"
    run("backup", str(f))
    assert f.read_bytes() == open(__import__("fake_device").FIXTURE, "rb").read()
    assert capsys.readouterr().out == f"saved {cli.BACKUP_SIZE} bytes to {f}\n"
    run("restore", str(f))
    assert capsys.readouterr().out == "restored (0 bytes changed)\n" and not fake.commands(p.WRITE)
    data = bytearray(f.read_bytes())
    data[0:3] = b"abc"                              # profile 1
    data[-1] ^= 0xFF                                # last lighting byte
    f.write_bytes(data)
    run("restore", str(f))
    assert capsys.readouterr().out == "restored (4 bytes changed)\n"
    assert bytes(fake.records[1][:3]) == b"abc" and b"".join(bytes(fake.records[n]) for n in cli.RECORDS) == data


def test_restore_wrong_size(fake, tmp_path):
    f = tmp_path / "bad.bin"
    f.write_bytes(b"abc")
    with pytest.raises(SystemExit, match="not a c2ctl backup .3 bytes"):
        run("restore", str(f))
    assert not fake.commands(p.WRITE)


def test_watch_time(fake, capsys):
    fake.push(fake.state_report(pressed={"A", "Up"}, lt=7, left=(255, 0)))
    fake.push(fake.state_report(pressed={"A", "Up"}, lt=7, left=(255, 0)))   # same line: printed once
    fake.push(fake.state_report())
    run("watch", "--time", "0.5")
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("A Up") and "LT   7" in lines[0] and "L +1.00 -1.00" in lines[0]
    assert lines[1].startswith("-") and len(lines) == 2


def test_watch_sends_heartbeat(fake, monkeypatch, capsys):
    clock = iter(range(1000))
    monkeypatch.setattr(cli, "time", types.SimpleNamespace(time=lambda: next(clock) * 0.6))   # fast-forward
    run("watch", "--time", "5")
    assert len(fake.commands(p.HEARTBEAT)) > 1


def test_watch_until_interrupted(fake, monkeypatch):
    calls = []

    def state(self, timeout=0.5):
        calls.append(timeout)
        if len(calls) > 2:
            raise KeyboardInterrupt
        return None
    monkeypatch.setattr(device.Device, "state", state)
    with pytest.raises(KeyboardInterrupt):
        run("watch")
    assert calls == [0.2] * 3


def test_device_closed_on_error(fake, monkeypatch):
    closed = []
    monkeypatch.setattr(device.Device, "close", lambda self: closed.append(1))
    monkeypatch.setattr(cli, "run", lambda dev, args: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        run("info")
    assert closed == [1]


def test_parser_requires_command():
    with pytest.raises(SystemExit):
        cli.parser().parse_args([])
