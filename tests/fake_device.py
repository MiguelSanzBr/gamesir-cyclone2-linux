"""In-process emulator of the Cyclone 2 firmware's config channel, for tests.

The fake hidraw node is one end of a SOCK_SEQPACKET socketpair (keeps 64-byte report boundaries and works with
select/os.read/os.write); a thread answers on the other end like the real controller. The records start as a
backup taken from a real controller (``fixtures/backup.bin``).
"""
import os
import socket
import threading

from cyclone2 import discovery
from cyclone2 import protocol as p

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "backup.bin")
RECORDS = (1, 2, 3, 4, 5, 32)


def load_records(path=FIXTURE):
    data, out, off = open(path, "rb").read(), {}, 0
    for n in RECORDS:
        out[n] = bytearray(data[off:off + p.size_of(n)])
        off += p.size_of(n)
    return out


class FakeController:
    def __init__(self, pid=0x1053, firmware=b"3\x005\x006", current=1):
        self.records = load_records()
        self.pid, self.firmware, self.current = pid, firmware, current
        self.path = "/dev/hidraw-fake"
        self.drop = 0              # ignore the next N requests (lost answers -> resend)
        self.busy = 0              # answer the next N requests with "busy"
        self.silent = set()        # commands never answered
        self.corrupt = False       # store something else on write (verification-failure path)
        self.noise = True          # send a state report before every answer (like the real stream)
        self.log = []              # every report received (bytes)
        self.host, self._dev = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    # ---- wiring
    def install(self, monkeypatch):
        """Make cyclone2.device.Device() (and the GUI input thread) find and open this fake."""
        real_open = os.open

        def fake_open(path, flags, *a):
            if path == self.path:
                return os.dup(self.host.fileno())
            return real_open(path, flags, *a)
        monkeypatch.setattr(os, "open", fake_open)
        monkeypatch.setattr(discovery, "find_devices", lambda: iter([(self.path, self.pid)]))
        return self

    def close(self):
        self._dev.close()
        self.host.close()

    def commands(self, cmd):
        return [r for r in self.log if r[1] == cmd]

    # ---- firmware side
    def state_report(self, pressed=(), lt=0, rt=0, left=(128, 128), right=(128, 128), battery=100):
        """A 0x12 report with the given physical input (offsets as in cyclone2.protocol.state)."""
        r = bytearray(p.REPORT_SIZE)
        r[0] = p.STATE
        raw = bytearray(10)
        raw[1:5] = bytes([*left, *right])
        raw[5] = 0x0F
        hat = {v: k for k, v in p.HAT.items()}
        dirs = tuple(d for d in ("Up", "Down", "Right", "Left") if d in pressed)
        key = next((k for k in hat if set(k) == set(dirs)), None)
        if key:
            raw[5] = hat[key]
        for byte, bits in p.STATE_BITS.items():
            for bit, name in bits.items():
                if name in pressed:
                    raw[byte] |= 1 << bit
        raw[8], raw[9] = lt, rt
        r[p.RAW:p.RAW + 10] = raw
        r[36] = battery
        return bytes(r)

    def push(self, report):
        self._dev.send(report)

    def _answer(self, *data):
        if self.noise:
            self._dev.send(self.state_report())
        self._dev.send(bytes([p.ANSWER, *data]).ljust(p.REPORT_SIZE, b"\0"))

    def _serve(self):
        while True:
            try:
                r = self._dev.recv(p.REPORT_SIZE)
            except OSError:
                return
            if not r:
                return
            self.log.append(r)
            cmd = r[1]
            if r[0] != p.OUT or cmd in (p.HEARTBEAT, p.VIBRATE, p.LIGHT) or cmd in self.silent:
                continue
            if self.drop:
                self.drop -= 1
                continue
            if self.busy:
                self.busy -= 1
                self._answer(p.ACK, 1)
                continue
            if cmd == p.FIRMWARE:
                self._answer(p.FIRMWARE_ACK, 0x30, 0, *self.firmware)
            elif cmd == p.CURRENT:
                self._answer(p.CURRENT_ACK, self.current)
            elif cmd == p.SWITCH:
                self.current = r[2]
                self._answer(p.ACK, 0)
            elif cmd == p.READ:
                n, off, size = r[2], r[3] << 8 | r[4], r[5]
                self._answer(p.READ_ACK, n, r[3], r[4], size, *self.records[n][off:off + size])
            elif cmd == p.WRITE:
                n, off, size = r[2], r[3] << 8 | r[4], r[5]
                data = bytearray(r[6:6 + size])
                if self.corrupt:
                    data[0] ^= 0xFF
                self.records[n][off:off + size] = data
                self._answer(p.ACK, 0)
