"""theme (fonts, skins) plus sanity checks of the constant tables in catalog and geometry."""
import pytest

from cyclone2 import keys, light
from cyclone2.gui import catalog, geometry, theme


@pytest.mark.parametrize("families,expected", [([], "Sans"), (["Foo", "Noto Sans", "Cantarell"], "Cantarell"),
                                               (["DejaVu Sans", "Inter"], "Inter")])
def test_pick_family(monkeypatch, families, expected):
    monkeypatch.setattr(theme.tkfont, "families", lambda root=None: families)
    assert theme.pick_family(None) == expected


def test_font(monkeypatch):
    monkeypatch.setattr(theme, "FAMILY", "Foo")
    assert theme.font(10) == ("Foo", 10, "normal")
    assert theme.font(9, "bold") == ("Foo", 9, "bold")


def test_skins_are_complete():
    roles = set(geometry.ROLES.values()) | {"btn"}
    assert theme.DEFAULT_SKIN in theme.SKINS
    for sk in theme.SKINS.values():
        assert roles <= set(sk) and len(sk["body"]) == 3 and set(sk["zones"]) <= set(geometry.ZONE_SHAPES)


def test_catalog():
    assert [k for _, k in catalog.SECTIONS][0] == "buttons" and "None" in dict(catalog.TARGETS)
    assert set(catalog.BUTTONS) == set(geometry.PARTS) - {"M"} and set(catalog.GYRO_KEYS) <= set(keys.PAD.values())
    assert [z for z, _ in catalog.ZONES] == [z for z in light.LEDS if z != "home"][:2] + ["upper_left", "upper_right", "home"]
    assert {n for n, _ in catalog.PRESETS} == set(light.PRESETS)


def test_geometry_parts_fit_the_box():
    assert set(geometry.BEHIND) <= set(geometry.PARTS) and set(geometry.ROLES) <= set(geometry.PARTS)
    for pts in (geometry.BODY, geometry.LB_PTS):
        assert all(0 <= x <= geometry.WIDTH and 0 <= y <= geometry.HEIGHT for x, y in pts)
    assert all(target in geometry.PARTS or target in ("sticks", "leds") for *_, target in geometry.CALLOUTS)
