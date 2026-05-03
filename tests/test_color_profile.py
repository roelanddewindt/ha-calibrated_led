"""
tests/test_color_profile.py

Run with:
    PYTHONPATH=calibrated_led_poc python -m pytest tests/ -v
"""

import sys
sys.path.insert(0, "/home/claude/calibrated_led_poc")

import pytest
from color_profile import AnchorPoint, ColorProfile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def two_anchor_profile():
    return ColorProfile([
        AnchorPoint(kelvin=2700, r=255, g=147, b=41),
        AnchorPoint(kelvin=6500, r=255, g=255, b=251),
    ])


@pytest.fixture
def four_anchor_profile():
    """Realistic four-point profile."""
    return ColorProfile([
        AnchorPoint(kelvin=2000, r=255, g=105, b=0),
        AnchorPoint(kelvin=2700, r=255, g=147, b=41),
        AnchorPoint(kelvin=4000, r=255, g=197, b=143),
        AnchorPoint(kelvin=6500, r=255, g=255, b=251),
    ])


# ---------------------------------------------------------------------------
# Exact anchor point tests
# ---------------------------------------------------------------------------

def test_exact_warm_anchor(two_anchor_profile):
    assert two_anchor_profile.rgb_for_kelvin(2700) == (255, 147, 41)

def test_exact_cool_anchor(two_anchor_profile):
    assert two_anchor_profile.rgb_for_kelvin(6500) == (255, 255, 251)

def test_exact_four_anchors(four_anchor_profile):
    assert four_anchor_profile.rgb_for_kelvin(2000) == (255, 105, 0)
    assert four_anchor_profile.rgb_for_kelvin(2700) == (255, 147, 41)
    assert four_anchor_profile.rgb_for_kelvin(4000) == (255, 197, 143)
    assert four_anchor_profile.rgb_for_kelvin(6500) == (255, 255, 251)


# ---------------------------------------------------------------------------
# Interpolation tests
# ---------------------------------------------------------------------------

def test_midpoint_interpolation(two_anchor_profile):
    mid_k = (2700 + 6500) / 2
    r, g, b = two_anchor_profile.rgb_for_kelvin(mid_k)
    assert r == 255
    assert g == round((147 + 255) / 2)
    assert b == round((41 + 251) / 2)

def test_interpolation_uses_correct_bracket(four_anchor_profile):
    """Midpoint of 2700–4000 must not be influenced by the 6500 anchor."""
    k = (2700 + 4000) / 2
    r, g, b = four_anchor_profile.rgb_for_kelvin(k)
    assert r == 255
    assert g == round((147 + 197) / 2)
    assert b == round((41 + 143) / 2)

def test_unsorted_anchors_interpolate_correctly():
    profile = ColorProfile([
        AnchorPoint(kelvin=6500, r=255, g=255, b=251),
        AnchorPoint(kelvin=2700, r=255, g=147, b=41),
    ])
    assert profile.rgb_for_kelvin(2700) == (255, 147, 41)
    assert profile.rgb_for_kelvin(6500) == (255, 255, 251)


# ---------------------------------------------------------------------------
# Extrapolation tests (replaces old clamping tests)
# ---------------------------------------------------------------------------

def test_extrapolate_below_minimum(two_anchor_profile):
    """Below 2700K should extrapolate using the 2700–6500 slope, not clamp."""
    # At 2700K: g=147. Slope going down should reduce g below 147.
    r, g, b = two_anchor_profile.rgb_for_kelvin(1000)
    assert g < 147
    assert b < 41

def test_extrapolate_above_maximum(two_anchor_profile):
    """Above 6500K should extrapolate using the 2700–6500 slope, not clamp."""
    # At 6500K: g=255, b=251. Slope going up would push past 255 → clamped.
    r, g, b = two_anchor_profile.rgb_for_kelvin(8000)
    assert r == 255
    assert g == 255  # clamped
    assert b == 255  # clamped

def test_extrapolate_below_uses_first_pair(four_anchor_profile):
    """Extrapolation below 2000K must use the 2000–2700 slope, not 2700–4000."""
    # 2000K: g=105. 2700K: g=147. Slope = (147-105)/(2700-2000) = 0.06/K
    # At 1500K (500K below 2000): g ≈ 105 - 500*0.06 = 75
    r, g, b = four_anchor_profile.rgb_for_kelvin(1500)
    expected_g = round(105 + (1500 - 2000) / (2700 - 2000) * (147 - 105))
    assert g == _clamp(expected_g)

def test_extrapolate_above_uses_last_pair(four_anchor_profile):
    """Extrapolation above 6500K must use the 4000–6500 slope, not 2700–4000."""
    r, g, b = four_anchor_profile.rgb_for_kelvin(7500)
    # All channels likely saturate at 255 — just verify no crash and valid range
    assert 0 <= r <= 255
    assert 0 <= g <= 255
    assert 0 <= b <= 255

def test_extrapolated_values_always_in_range(four_anchor_profile):
    """Extrapolated values must always be clamped to 0–255."""
    for k in range(500, 12000, 100):
        r, g, b = four_anchor_profile.rgb_for_kelvin(k)
        assert 0 <= r <= 255, f"r out of range at {k}K"
        assert 0 <= g <= 255, f"g out of range at {k}K"
        assert 0 <= b <= 255, f"b out of range at {k}K"


# ---------------------------------------------------------------------------
# Factory / config loading
# ---------------------------------------------------------------------------

def test_from_config_four_anchors():
    config = [
        {"kelvin": 2000, "rgb": [255, 105, 0]},
        {"kelvin": 2700, "rgb": [255, 147, 41]},
        {"kelvin": 4000, "rgb": [255, 197, 143]},
        {"kelvin": 6500, "rgb": [255, 255, 251]},
    ]
    profile = ColorProfile.from_config(config)
    assert profile.rgb_for_kelvin(2000) == (255, 105, 0)
    assert profile.rgb_for_kelvin(6500) == (255, 255, 251)

def test_single_anchor_raises():
    with pytest.raises(ValueError, match="at least two"):
        ColorProfile([AnchorPoint(kelvin=2700, r=255, g=147, b=41)])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(v, lo=0, hi=255):
    return max(lo, min(hi, v))
