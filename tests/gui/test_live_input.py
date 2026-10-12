"""live_input mixin: state reports, the reader thread (against the fake controller or patched I/O), send_now."""
import os
import threading
import time

import pytest

from cyclone2 import discovery
from cyclone2 import protocol as p
from cyclone2.gui import live_input, theme


@pytest.fixture
def closing_sleep(shared_app, monkeypatch):
    """time.sleep(1) of the reconnect loop ends the reader instead of sleeping."""
    app, calls = shared_app, []
    app._closing = False
    monkeypatch.setattr(live_input.time, "sleep", lambda s: (calls.append(s), setattr(app, "_closing", True)))
    yield calls
    app._closing = False


def test_pad_state_ripples_only_new_presses(app):
    app.pad_state({"pressed": {"A"}})
    t = app.press_t["A"]
    assert app.pad_down == {"A"} and app.pad == {"pressed": {"A"}}
    app.pad_state({"pressed": {"A", "B"}})                  # A still held: no new ripple; B is new
    assert app.press_t["A"] == t and "B" in app.press_t
    app.pad_state({"pressed": set()})
    assert not app.pad_down


def test_read_pad_returns_when_already_closing(shared_app):
    shared_app._closing = True
    try:
        shared_app._read_pad()                                  # loop body never runs
    finally:
        shared_app._closing = False


def test_read_pad_no_device_retries_after_a_second(shared_app, closing_sleep, monkeypatch):
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([]))
    shared_app._read_pad()
    assert closing_sleep == [1] and shared_app._pad_fd is None


def test_read_pad_open_error_is_a_missing_device(shared_app, closing_sleep, monkeypatch):
    monkeypatch.setattr(discovery, "find_devices", lambda: iter([("/dev/hidraw-nope", 1)]))
    real = os.open

    def deny(path, flags, *a):
        if path == "/dev/hidraw-nope":
            raise PermissionError("denied")
        return real(path, flags, *a)
    monkeypatch.setattr(live_input.os, "open", deny)
    shared_app._read_pad()
    assert closing_sleep == [1] and shared_app._pad_fd is None


def test_read_pad_follows_state_stream(shared_app, fake, closing_sleep):
    app, seen = shared_app, []
    real = app.pad_state
    app.pad_state = lambda st: (seen.append(st), real(st), len(seen) == 2 and setattr(app, "_closing", True))
    fake.push(fake.state_report(pressed={"A", "Up"}, lt=200, left=(255, 0)))
    fake.push(bytes([p.ANSWER, p.ACK, 0]).ljust(p.REPORT_SIZE, b"\0"))     # not a state report: skipped
    fake.push(fake.state_report(pressed={"B"}, rt=50))
    try:
        app._read_pad()
    finally:
        del app.pad_state
    assert [s["pressed"] for s in seen] == [{"A", "Up"}, {"B"}] and seen[0]["lt"] == 200 and seen[1]["rt"] == 50
    end = time.time() + 2                                                   # the fake logs on its own thread
    while not fake.commands(p.HEARTBEAT) and time.time() < end:
        time.sleep(0.005)
    assert fake.commands(p.HEARTBEAT)                                       # sent when the connection was opened
    assert {"A", "Up", "B"} <= set(app.press_t)
    assert app.pad == {} and not app.pad_down and app._pad_fd is None       # cleared once the node went away
    assert closing_sleep == [1]


def test_read_pad_heartbeat_repeats(shared_app, fake, closing_sleep, monkeypatch):
    app = shared_app
    monkeypatch.setattr(theme, "HEARTBEAT_MS", 20)
    real = app.pad_state
    n = []
    app.pad_state = lambda st: (n.append(1), real(st), len(n) == 1 and setattr(app, "_closing", True))
    threading.Timer(0.35, lambda: fake.push(fake.state_report(pressed={"X"}))).start()
    try:
        app._read_pad()
    finally:
        del app.pad_state
        app.update()
    end = time.time() + 2
    while len(fake.commands(p.HEARTBEAT)) < 2 and time.time() < end:
        time.sleep(0.005)
    assert len(fake.commands(p.HEARTBEAT)) >= 2


def test_read_pad_write_error_reconnects(shared_app, fake, closing_sleep, monkeypatch):
    app = shared_app
    real = live_input.os.write

    def broken(fd, data):
        if fd == app._pad_fd:
            raise OSError("unplugged")
        return real(fd, data)
    monkeypatch.setattr(live_input.os, "write", broken)
    app.pad_down = {"stale"}
    app._read_pad()
    assert closing_sleep == [1] and app._pad_fd is None and not app.pad_down


# ---------------------------------------------------------------- send_now / preview_frame
def test_send_now_disconnected_and_errors(app):
    app.send_now(b"x")                                      # no handle: ignored
    r, w = os.pipe()
    os.close(r)                                             # EPIPE on write: swallowed
    app._pad_fd = w
    try:
        app.send_now(b"x")
    finally:
        os.close(w)
        app._pad_fd = None


def test_send_now_writes_on_the_handle(app):
    r, w = os.pipe()
    app._pad_fd = w
    try:
        app.send_now(b"hello")
        assert os.read(r, 10) == b"hello"
    finally:
        app._pad_fd = None
        os.close(r)
        os.close(w)


def test_preview_frame_sends_light_commands(app, fake):
    app._pad_fd = os.open(fake.path, os.O_RDWR | os.O_NONBLOCK)
    try:
        app.frame = 2
        app.preview_frame(True)                             # hold the frame being edited (1-based)
        app.preview_frame(False)                            # play the animation
        end = time.time() + 5
        while len(fake.commands(p.LIGHT)) < 2 and time.time() < end:
            time.sleep(0.005)
    finally:
        os.close(app._pad_fd)
        app._pad_fd = None
    assert [bytes(r[2:4]) for r in fake.commands(p.LIGHT)] == [bytes([0, 3]), bytes([1, 1])]


def test_show_leds_page_previews_frame_and_leaving_plays(app, monkeypatch):
    sent = []
    monkeypatch.setattr(app, "send_now", sent.append)
    app.frame = 1
    app.show("leds")
    app.show("leds")                                        # already there: nothing new
    app.show("home")
    assert sent == [p.command(p.LIGHT, 0, 2), p.command(p.LIGHT, 1, 1)]
