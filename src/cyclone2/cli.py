"""``c2ctl`` — command-line configurator for the GameSir Cyclone 2."""
import argparse
import json
import sys
import time

from . import device, discovery, light, profile
from . import protocol as p

RECORDS = (*p.PROFILES, p.SHIFT, p.LIGHTS)        # what a backup holds, in file order
BACKUP_SIZE = sum(p.size_of(n) for n in RECORDS)


def parser():
    ap = argparse.ArgumentParser(prog="c2ctl", description="Configure the GameSir Cyclone 2 on Linux.")
    ap.add_argument("--device", help="hidraw node (default: first Cyclone 2 found)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list connected controllers")
    sub.add_parser("info", help="firmware, connection, active profile, battery")
    d = sub.add_parser("dump", help="print a profile (or the lighting) as JSON")
    d.add_argument("-p", "--profile", type=int, choices=(1, 2, 3, 4, 5), help="1-4, 5 = Shift layer (default: active)")
    d.add_argument("--lights", action="store_true", help="dump the lighting record instead")
    a = sub.add_parser("apply", help="write a JSON file (full or partial) produced by dump")
    a.add_argument("file")
    a.add_argument("-p", "--profile", type=int, choices=(1, 2, 3, 4, 5))
    a.add_argument("--lights", action="store_true")
    s = sub.add_parser("switch", help="make a profile the active one")
    s.add_argument("profile", type=int, choices=(1, 2, 3, 4))
    r = sub.add_parser("reset", help="restore app defaults of a profile")
    r.add_argument("-p", "--profile", type=int, choices=(1, 2, 3, 4, 5))
    r.add_argument("--part", choices=("mapping", "sticks", "triggers", "motion", "motors"))
    l = sub.add_parser("light", help="lighting: preset, solid colour, brightness, speed, active animation")
    l.add_argument("--preset", choices=sorted(light.PRESETS))
    l.add_argument("--color", help="solid colour, e.g. #00ffaa")
    l.add_argument("--brightness", type=int, help="0-100")
    l.add_argument("--speed", type=int, help=f"0-{light.MAX_SPEED}")
    l.add_argument("--animation", type=int, choices=range(4), help="animation slot to edit and activate (0-3)")
    v = sub.add_parser("vibrate", help="test the motors")
    v.add_argument("--left", type=int, default=160)
    v.add_argument("--right", type=int, default=160)
    v.add_argument("--time", type=float, default=1.0)
    b = sub.add_parser("backup", help="save every profile and the lighting to a file")
    b.add_argument("file")
    rs = sub.add_parser("restore", help="write a backup file back")
    rs.add_argument("file")
    w = sub.add_parser("watch", help="print pressed buttons, sticks and triggers live (Ctrl+C to stop)")
    w.add_argument("--time", type=float, help="stop after this many seconds")
    return ap


def _store(dev, n, old, new):
    """Write the changed range of a record and read it back; returns the number of bytes written."""
    span = profile.changed_span(old, new)
    if span:
        dev.write_profile(n, new, *span)
        if dev.read_profile(n) != new:
            sys.exit("verification failed: the controller did not keep what was sent")
    return span[1] - span[0] if span else 0


def _target(dev, args):
    return args.profile or dev.current_profile()


def main(argv=None):
    args = parser().parse_args(argv)
    if args.cmd == "list":
        found = list(discovery.find_devices())
        for path, pid in found:
            print(f"{path}  {pid:04x}  {p.PIDS.get(pid, 'GameSir')}")
        if not found:
            print("no GameSir Cyclone 2 found")
        return 0
    dev = device.Device(args.device)
    try:
        return run(dev, args)
    finally:
        dev.close()


def run(dev, args):
    if args.cmd == "info":
        fw, dongle = dev.firmware()
        st = dev.state() or {}
        print(f"device:   {dev.path} ({p.PIDS.get(dev.pid, hex(dev.pid))})")
        print(f"firmware: {fw}" + (f" (dongle {dongle})" if dongle else ""))
        print(f"profile:  {dev.current_profile()}")
        if st:
            print(f"battery:  {st['battery']}%" + (" (charging)" if st["charging"] else ""))
    elif args.cmd == "dump":
        if args.lights:
            doc = light.decode(dev.read_profile(p.LIGHTS))
        else:
            doc = profile.decode(dev.read_profile(_target(dev, args)))
        print(json.dumps(doc, indent=2, ensure_ascii=False))
    elif args.cmd == "apply":
        with open(args.file, encoding="utf-8") as f:
            doc = json.load(f)
        if args.lights:
            n = p.LIGHTS
            old = dev.read_profile(n)
            new = light.encode({**light.decode(old), **doc}, old)
        else:
            n = _target(dev, args)
            old = dev.read_profile(n)
            new = profile.encode(doc, old)
        print(f"profile {n}: {_store(dev, n, old, new)} bytes written")
    elif args.cmd == "switch":
        dev.switch_profile(args.profile)
        print(f"active profile: {dev.current_profile()}")
    elif args.cmd == "reset":
        n = _target(dev, args)
        old = dev.read_profile(n)
        new = profile.encode(profile.reset(profile.decode(old), args.part), old)
        print(f"profile {n}: {_store(dev, n, old, new)} bytes written")
    elif args.cmd == "light":
        old = dev.read_profile(p.LIGHTS)
        doc = light.decode(old)
        if args.animation is not None:
            doc["active"] = args.animation
        if args.preset:
            doc = light.apply_preset(doc, args.preset)
        if args.color:
            doc = light.solid(doc, args.color.lower() if args.color.startswith("#") else "#" + args.color.lower())
        an = doc["animations"][doc["active"]]
        if args.brightness is not None:
            an["brightness"] = min(max(args.brightness, 0), 100)
        if args.speed is not None:
            an["speed"] = args.speed
        print(f"lighting: {_store(dev, p.LIGHTS, old, light.encode(doc, old))} bytes written")
    elif args.cmd == "vibrate":
        dev.vibrate(args.left, args.right)
        time.sleep(args.time)
        dev.vibrate(0, 0)
    elif args.cmd == "backup":
        data = b"".join(dev.read_profile(n) for n in RECORDS)
        with open(args.file, "wb") as f:
            f.write(data)
        print(f"saved {len(data)} bytes to {args.file}")
    elif args.cmd == "restore":
        with open(args.file, "rb") as f:
            data = f.read()
        if len(data) != BACKUP_SIZE:
            sys.exit(f"{args.file}: not a c2ctl backup ({len(data)} bytes, expected {BACKUP_SIZE})")
        off = total = 0
        for n in RECORDS:
            new = data[off:off + p.size_of(n)]
            off += len(new)
            total += _store(dev, n, dev.read_profile(n), new)
        print(f"restored ({total} bytes changed)")
    else:   # watch
        end = time.time() + args.time if args.time else None
        last, beat = None, time.time()
        while end is None or time.time() < end:
            if time.time() - beat > 1:
                dev.heartbeat()
                beat = time.time()
            st = dev.state(0.2)
            if st is None:
                continue
            line = (f"{' '.join(sorted(st['pressed'])) or '-':<30} LT {st['lt']:3} RT {st['rt']:3}  "
                    f"L {st['left'][0]:+.2f} {st['left'][1]:+.2f}  R {st['right'][0]:+.2f} {st['right'][1]:+.2f}")
            if line != last:
                print(line, flush=True)
                last = line
    return 0


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
