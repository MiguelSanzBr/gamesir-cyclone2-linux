from cyclone2 import discovery, protocol as p

DESC = b"\x05\x01" + p.USAGE_PAGE + b"\x09\x01"


def node(root, name, hid_id, desc=DESC):
    d = root / "class" / "hidraw" / name / "device"
    d.mkdir(parents=True)
    if hid_id is not None:
        (d / "uevent").write_text(f"DRIVER=hid\nHID_ID={hid_id}\n")
    if desc is not None:
        (d / "report_descriptor").write_bytes(desc)


def test_finds_only_vendor_interface(tmp_path, monkeypatch):
    monkeypatch.setattr(discovery, "SYS", str(tmp_path))
    monkeypatch.setattr(discovery, "DEV", "/devx")
    node(tmp_path, "hidraw3", "0003:00003537:0000101D")
    node(tmp_path, "hidraw1", "0003:00003537:0000102A")
    node(tmp_path, "hidraw0", "0003:00003537:0000101D", desc=b"\x05\x01\x09\x05")   # gamepad interface
    node(tmp_path, "hidraw2", "0003:0000045E:0000101D")                              # other vendor
    node(tmp_path, "hidraw4", "garbage")
    node(tmp_path, "hidraw5", None)                                                  # no uevent at all
    node(tmp_path, "hidraw6", "0003:00003537:0000101D", desc=None)                   # no descriptor
    assert list(discovery.find_devices()) == [("/devx/hidraw1", 0x102A), ("/devx/hidraw3", 0x101D)]


def test_no_sysfs(tmp_path, monkeypatch):
    monkeypatch.setattr(discovery, "SYS", str(tmp_path / "nothing"))
    assert list(discovery.find_devices()) == []
    assert discovery._read(str(tmp_path / "missing")) == b""


def test_defaults_are_real_roots():
    assert (discovery.SYS, discovery.DEV) == ("/sys", "/dev")
