"""Transport to the controller over ``/dev/hidraw``: profiles, lighting, active profile, firmware, rumble, state."""
import os
import select
import time

from . import discovery
from . import protocol as p

TRIES = 10               # the app gives up on a message after 10 sends
RESEND = 0.2             # ... resending every 200 ms while unanswered


class NotFound(SystemExit):
    """No controller is connected."""


class PermissionDenied(SystemExit):
    """The hidraw node cannot be opened (the udev rule is missing)."""

    def __init__(self, path):
        super().__init__(f"permission denied on {path}: install udev/70-gamesir-cyclone2.rules (see README)")
        self.path = path


class NoAnswer(IOError):
    """The controller did not answer a command (asleep, busy or disconnected)."""


class Device:
    """One open controller (``path``: a specific hidraw node, default the first one found).

    Exits with a message (``SystemExit``) when there is no controller or no permission.
    """

    def __init__(self, path=None):
        devs = list(discovery.find_devices())
        if path:
            devs = [d for d in devs if d[0] == path] or [(path, 0)]
        if not devs:
            raise NotFound("GameSir Cyclone 2 not found (plug it in with the cable or the 2.4G dongle)")
        self.path, self.pid = devs[0]
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)
        except PermissionError:
            raise PermissionDenied(self.path)
        self.heartbeat()

    def close(self):
        os.close(self.fd)

    # ------------------------------------------------------------ raw I/O
    def write(self, report):
        os.write(self.fd, report)

    def read(self, timeout):
        """Next input report, or ``None`` after ``timeout`` seconds."""
        if not select.select([self.fd], [], [], max(timeout, 0))[0]:
            return None
        return os.read(self.fd, p.REPORT_SIZE)

    def request(self, report, want, match=lambda r: True):
        """Send ``report`` until an answer of kind ``want`` (that satisfies ``match``) arrives.

        Gamepad state reports and unrelated answers are skipped; "busy" answers and silence cause a resend.
        Raises ``IOError`` after :data:`TRIES` sends.
        """
        for _ in range(TRIES):
            self.write(report)
            end = time.time() + RESEND
            while (r := self.read(end - time.time())) is not None:
                if p.busy(r):               # checked first: a busy answer is an ACK too
                    break
                if p.kind(r) == want and match(r):
                    return r
        raise NoAnswer(f"no answer to command {report[1]} (controller busy or disconnected)")

    def heartbeat(self):
        """The app sends this every second while its window has focus (keeps the config session alive)."""
        self.write(p.command(p.HEARTBEAT, 0))

    # ------------------------------------------------------------ status
    def firmware(self):
        """``(controller, dongle)`` firmware versions, e.g. ``("1.2.3", "")``."""
        return p.firmware(self.request(p.command(p.FIRMWARE), p.FIRMWARE_ACK))

    def current_profile(self):
        """Active profile 1-4 (the app treats 0 as 1)."""
        n = self.request(p.command(p.CURRENT), p.CURRENT_ACK)[2]
        return n or 1

    def switch_profile(self, n):
        self.request(p.command(p.SWITCH, n), p.ACK)

    def state(self, timeout=0.5):
        """Decoded gamepad state (see :func:`cyclone2.protocol.state`) or ``None``."""
        end = time.time() + timeout
        while (r := self.read(end - time.time())) is not None:
            if r[0] == p.STATE:
                return p.state(r)
        return None

    def vibrate(self, left, right):
        """Run the motors (0-255 each); the app stops them again after a second."""
        self.write(p.command(p.VIBRATE, 102, 85, left, right))

    def light_preview(self, playing, frame=1):
        """Play the active animation (``playing``) or hold frame ``frame`` (1-8), like the app's LED editor."""
        self.write(p.command(p.LIGHT, int(playing), frame))

    # ------------------------------------------------------------ records
    def read_profile(self, n):
        """The whole record of profile ``n`` (1-4, :data:`~cyclone2.protocol.SHIFT` or :data:`~cyclone2.protocol.LIGHTS`)."""
        buf = bytearray(p.size_of(n))
        for req in p.read_requests(n):
            off = req[3] << 8 | req[4]
            r = self.request(req, p.READ_ACK, lambda r, off=off: p.chunk(r)[:2] == (n, off))
            data = p.chunk(r)[2]
            buf[off:off + len(data)] = data
        return bytes(buf)

    def write_profile(self, n, data, start=0, end=None):
        """Write ``data[start:end]`` of a record (the app writes only the changed range; it is stored at once)."""
        end = len(data) if end is None else end
        assert len(data) == p.size_of(n) and 0 <= start < end <= len(data)
        for req in p.write_requests(n, data[start:end], start):
            self.request(req, p.ACK)
