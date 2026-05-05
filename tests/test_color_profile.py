"""
tests/test_color_profile.py

Run with:
    PYTHONPATH=calibrated_led_poc python -m pytest tests/ -v
"""

import sys
sys.path.insert(0, "/home/claude/calibrated_led_poc")

import pytest
from color_profile import AnchorPoint, ColorProfile, XyAnchorPoint, XyColorProfile


# ===========================================================================
# RGB profile tests
# ===========================================================================

@pytest.fixture
def two_anchor_profile():
    return ColorProfile([
        AnchorPoint(kelvin=2700, r=255, g=147, b=41),
        AnchorPoint(kelvin=6500, r=255, g=255, b=251),
    ])

@pytest.fixture
def four_anchor_profile():
    return ColorProfile([
        AnchorPoint(kelvin=2000, r=255, g=105, b=0),
        AnchorPoint(kelvin=2700, r=255, g=147, b=41),
        AnchorPoint(kelvin=4000, r=255, g=197, b=143),
        AnchorPoint(kelvin=6500, r=255, g=255, b=251),
    ])

def test_exact_anchors(two_anchor_profile):
    assert two_anchor_profile.rgb_for_kelvin(2700) == (255, 147, 41)
    assert two_anchor_profile.rgb_for_kelvin(6500) == (255, 255, 251)

def test_midpoint_interpolation(two_anchor_profile):
    mid_k = (2700 + 6500) / 2
    r, g, b = two_anchor_profile.rgb_for_kelvin(mid_k)
    assert r == 255
    assert g == round((147 + 255) / 2)
    assert b == round((41 + 251) / 2)

def test_correct_bracket_used(four_anchor_profile):
    k = (2700 + 4000) / 2
    r, g, b = four_anchor_profile.rgb_for_kelvin(k)
    assert g == round((147 + 197) / 2)
    assert b == round((41 + 143) / 2)

def test_extrapolate_below(two_anchor_profile):
    r, g, b = two_anchor_profile.rgb_for_kelvin(1000)
    assert g < 147
    assert b < 41

def test_extrapolate_above(two_anchor_profile):
    r, g, b = two_anchor_profile.rgb_for_kelvin(8000)
    assert r == 255
    assert g == 255
    assert b == 255

def test_extrapolate_uses_first_pair(four_anchor_profile):
    r, g, b = four_anchor_profile.rgb_for_kelvin(1500)
    expected_g = round(105 + (1500 - 2000) / (2700 - 2000) * (147 - 105))
    assert g == max(0, min(255, expected_g))

def test_rgb_always_in_range(four_anchor_profile):
    for k in range(500, 12000, 100):
        r, g, b = four_anchor_profile.rgb_for_kelvin(k)
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255

def test_rgb_from_config():
    config = [
        {"kelvin": 2700, "rgb": [255, 147, 41]},
        {"kelvin": 6500, "rgb": [255, 255, 251]},
    ]
    profile = ColorProfile.from_config(config)
    assert profile.rgb_for_kelvin(2700) == (255, 147, 41)

def test_rgb_unsorted_anchors():
    profile = ColorProfile([
        AnchorPoint(kelvin=6500, r=255, g=255, b=251),
        AnchorPoint(kelvin=2700, r=255, g=147, b=41),
    ])
    assert profile.rgb_for_kelvin(2700) == (255, 147, 41)

def test_rgb_single_anchor_raises():
    with pytest.raises(ValueError, match="at least two"):
        ColorProfile([AnchorPoint(kelvin=2700, r=255, g=147, b=41)])


# ===========================================================================
# XY profile tests
# ===========================================================================

@pytest.fixture
def xy_profile():
    """Four-point profile matching Living TV measured anchors."""
    return XyColorProfile([
        XyAnchorPoint(kelvin=1800, x=0.532, y=0.432),
        XyAnchorPoint(kelvin=2200, x=0.508, y=0.426),
        XyAnchorPoint(kelvin=2700, x=0.453, y=0.408),
        XyAnchorPoint(kelvin=4000, x=0.378, y=0.375),
    ])

def test_xy_exact_anchors(xy_profile):
    assert xy_profile.xy_for_kelvin(1800) == (0.532, 0.432)
    assert xy_profile.xy_for_kelvin(2700) == (0.453, 0.408)
    assert xy_profile.xy_for_kelvin(4000) == (0.378, 0.375)

def test_xy_midpoint_interpolation(xy_profile):
    x, y = xy_profile.xy_for_kelvin(2450)  # midpoint 2200–2700
    assert round(x, 4) == round((0.508 + 0.453) / 2, 4)
    assert round(y, 4) == round((0.426 + 0.408) / 2, 4)

def test_xy_extrapolate_below(xy_profile):
    x, y = xy_profile.xy_for_kelvin(1000)
    # Should extrapolate warmer than 1800K anchor (higher x)
    assert x > 0.532

def test_xy_extrapolate_above(xy_profile):
    x, y = xy_profile.xy_for_kelvin(6500)
    # Should extrapolate cooler than 4000K anchor (lower x)
    assert x < 0.378

def test_xy_always_in_range(xy_profile):
    for k in range(500, 10000, 100):
        x, y = xy_profile.xy_for_kelvin(k)
        assert 0.0 <= x <= 1.0, f"x out of range at {k}K: {x}"
        assert 0.0 <= y <= 1.0, f"y out of range at {k}K: {y}"

def test_xy_from_config():
    config = [
        {"kelvin": 2700, "x": 0.453, "y": 0.408},
        {"kelvin": 4000, "x": 0.378, "y": 0.375},
    ]
    profile = XyColorProfile.from_config(config)
    assert profile.xy_for_kelvin(2700) == (0.453, 0.408)

def test_xy_unsorted_anchors():
    profile = XyColorProfile([
        XyAnchorPoint(kelvin=4000, x=0.378, y=0.375),
        XyAnchorPoint(kelvin=2700, x=0.453, y=0.408),
    ])
    assert profile.xy_for_kelvin(2700) == (0.453, 0.408)

def test_xy_single_anchor_raises():
    with pytest.raises(ValueError, match="at least two"):
        XyColorProfile([XyAnchorPoint(kelvin=2700, x=0.453, y=0.408)])
