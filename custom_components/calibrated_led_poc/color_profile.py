# PROOF OF CONCEPT — not production-ready. See https://github.com/orgs/home-assistant/discussions/3538
"""
color_profile.py — RGB and XY calibration profiles for LED strips.

Two profile types are supported:

RGB profile — maps Kelvin to (R, G, B) tuples.
Use for raw RGB strips where HA controls channels directly.

    color_profile:
      - kelvin: 1800
        rgb: [255, 175, 15]
      - kelvin: 2700
        rgb: [255, 230, 60]
      - kelvin: 6500
        rgb: [183, 255, 117]

XY profile — maps Kelvin to CIE 1931 xy chromaticity.
Use for controllers that accept xy natively (e.g. Zigbee color light
with XY color mode), bypassing lossy RGB→XY→RGB conversions.

    output_mode: xy
    color_profile:
      - kelvin: 1800
        x: 0.532
        y: 0.432
      - kelvin: 2700
        x: 0.453
        y: 0.408
      - kelvin: 4000
        x: 0.378
        y: 0.375

Anchor points may be in any order; they are sorted on load.
Between anchors: linear interpolation.
Beyond outer anchors: linear extrapolation, clamped to valid range.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


# ---------------------------------------------------------------------------
# RGB profile
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AnchorPoint:
    kelvin: int
    r: int
    g: int
    b: int


class ColorProfile:
    """Calibration profile mapping Kelvin → (R, G, B)."""

    def __init__(self, anchors: List[AnchorPoint]) -> None:
        if len(anchors) < 2:
            raise ValueError("A color profile requires at least two anchor points.")
        self._anchors = sorted(anchors, key=lambda a: a.kelvin)

    def rgb_for_kelvin(self, kelvin: float) -> Tuple[int, int, int]:
        """Return interpolated or extrapolated (R, G, B)."""
        anchors = self._anchors
        if kelvin < anchors[0].kelvin:
            return self._interpolate(anchors[0], anchors[1], kelvin)
        if kelvin > anchors[-1].kelvin:
            return self._interpolate(anchors[-2], anchors[-1], kelvin)
        for lo, hi in zip(anchors, anchors[1:]):
            if lo.kelvin <= kelvin <= hi.kelvin:
                return self._interpolate(lo, hi, kelvin)
        raise RuntimeError(f"Interpolation failed for kelvin={kelvin}")

    @staticmethod
    def _interpolate(lo: AnchorPoint, hi: AnchorPoint, kelvin: float) -> Tuple[int, int, int]:
        t = (kelvin - lo.kelvin) / (hi.kelvin - lo.kelvin)
        r = round(lo.r + t * (hi.r - lo.r))
        g = round(lo.g + t * (hi.g - lo.g))
        b = round(lo.b + t * (hi.b - lo.b))
        return (_clamp(r), _clamp(g), _clamp(b))

    @classmethod
    def from_config(cls, config: list) -> "ColorProfile":
        anchors = []
        for entry in config:
            kelvin = int(entry["kelvin"])
            r, g, b = [int(v) for v in entry["rgb"]]
            anchors.append(AnchorPoint(kelvin=kelvin, r=r, g=g, b=b))
        return cls(anchors)


# ---------------------------------------------------------------------------
# XY profile
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class XyAnchorPoint:
    kelvin: int
    x: float
    y: float


class XyColorProfile:
    """Calibration profile mapping Kelvin → CIE 1931 (x, y) chromaticity."""

    def __init__(self, anchors: List[XyAnchorPoint]) -> None:
        if len(anchors) < 2:
            raise ValueError("A color profile requires at least two anchor points.")
        self._anchors = sorted(anchors, key=lambda a: a.kelvin)

    def xy_for_kelvin(self, kelvin: float) -> Tuple[float, float]:
        """Return interpolated or extrapolated (x, y) chromaticity."""
        anchors = self._anchors
        if kelvin < anchors[0].kelvin:
            return self._interpolate(anchors[0], anchors[1], kelvin)
        if kelvin > anchors[-1].kelvin:
            return self._interpolate(anchors[-2], anchors[-1], kelvin)
        for lo, hi in zip(anchors, anchors[1:]):
            if lo.kelvin <= kelvin <= hi.kelvin:
                return self._interpolate(lo, hi, kelvin)
        raise RuntimeError(f"Interpolation failed for kelvin={kelvin}")

    @staticmethod
    def _interpolate(lo: XyAnchorPoint, hi: XyAnchorPoint, kelvin: float) -> Tuple[float, float]:
        t = (kelvin - lo.kelvin) / (hi.kelvin - lo.kelvin)
        x = lo.x + t * (hi.x - lo.x)
        y = lo.y + t * (hi.y - lo.y)
        # Clamp to valid CIE xy range
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        return (round(x, 6), round(y, 6))

    @classmethod
    def from_config(cls, config: list) -> "XyColorProfile":
        anchors = []
        for entry in config:
            kelvin = int(entry["kelvin"])
            x = float(entry["x"])
            y = float(entry["y"])
            anchors.append(XyAnchorPoint(kelvin=kelvin, x=x, y=y))
        return cls(anchors)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _clamp(value: int, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, value))
