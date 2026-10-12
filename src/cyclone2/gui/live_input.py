"""Mixin: live input from the controller's state reports (pressed buttons, sticks, triggers, battery).

A second handle on the same hidraw node: the kernel hands every input report to each reader, so this thread
sees the ``0x12`` state stream while the worker threads talk to the config channel. It also sends the
heartbeat the app sends every second, and short "write now" commands such as the LED preview.
"""
import os
import select
import time

from .. import discovery
from .. import protocol as p
from . import theme


class PadInput:
    def _read_pad(self):
        """Background thread: follow the real controller; reconnects every second."""
        while not self._closing:
            dev = next(discovery.find_devices(), None)
            try:
                fd = os.open(dev[0], os.O_RDWR | os.O_NONBLOCK) if dev else None
            except OSError:
                fd = None
            if fd is None:
                time.sleep(1)
                continue
            self._pad_fd = fd
            beat = 0.0
            try:
                while not self._closing:
                    if time.time() - beat > theme.HEARTBEAT_MS / 1000:
                        os.write(fd, p.command(p.HEARTBEAT, 0))
                        beat = time.time()
                    if select.select([fd], [], [], 0.2)[0]:
                        st = p.state(os.read(fd, p.REPORT_SIZE))
                        if st:
                            self.pad_state(st)
            except OSError:
                pass
            finally:
                self._pad_fd = None
                os.close(fd)
            self.pad_down = set()
            self.pad = {}
            time.sleep(1)

    def pad_state(self, st):
        """New state report: ripple on buttons that just went down."""
        now = time.time()
        for name in st["pressed"] - self.pad_down:
            self.press_t[name] = now
        self.pad_down, self.pad = st["pressed"], st

    def send_now(self, report):
        """Write a command on the input thread's handle (no answer expected); ignored while disconnected."""
        fd = self._pad_fd
        if fd is not None:
            try:
                os.write(fd, report)
            except OSError:
                pass

    def preview_frame(self, editing):
        """On the lights page the controller holds the frame being edited; elsewhere it plays the animation."""
        self.send_now(p.command(p.LIGHT, 0, self.frame + 1) if editing else p.command(p.LIGHT, 1, 1))
