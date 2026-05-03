# PROOF OF CONCEPT — not production-ready. See https://github.com/orgs/home-assistant/discussions/3538
"""
color_profile.py — RGB calibration profile for LED strips.

A profile consists of anchor points mapping color temperature (Kelvin) to
empirically correct (R, G, B) tuples for a specific strip.  Between anchors,
values are linearly interpolated.  Beyond the outer anchors, values are
linearly extrapolated using the slope of the nearest pair, clamped to 0–255.

Example five-point profile (starting point values — adjust to taste for your specific strip):

    color_profile:
      - kelvin: 1800
        rgb: [255, 145, 0]
      - kelvin: 2200
        rgb: [255, 169, 13]
      - kelvin: 2700
        rgb: [255, 199, 30]
      - kelvin: 4000
        rgb: [255, 231, 125]
      - kelvin: 6500
        rgb: [255, 245, 169]

Anchor points may be in any order; they are sorted on load.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class AnchorPoint:
    kelvin: int
    r: int
    g: int
    b: int


class ColorProfile:
    """Holds a list of calibration anchors and performs interpolation/extrapolation."""

    def __init__(self, anchors: List[AnchorPoint]) -> None:
        if len(anchors) < 2:
            raise ValueError("A color profile requires at least two anchor points.")
        self._anchors = sorted(anchors, key=lambda a: a.kelvin)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rgb_for_kelvin(self, kelvin: float) -> Tuple[int, int, int]:
        """Return interpolated or extrapolated (R, G, B) for the requested color temperature."""
        anchors = self._anchors

        # Extrapolate below minimum anchor using the slope of the first pair
        if kelvin < anchors[0].kelvin:
            return self._interpolate(anchors[0], anchors[1], kelvin)

        # Extrapolate above maximum anchor using the slope of the last pair
        if kelvin > anchors[-1].kelvin:
            return self._interpolate(anchors[-2], anchors[-1], kelvin)

        # Interpolate between bracketing pair
        for lo, hi in zip(anchors, anchors[1:]):
            if lo.kelvin <= kelvin <= hi.kelvin:
                return self._interpolate(lo, hi, kelvin)

        # Should never reach here
        raise RuntimeError(f"Interpolation failed for kelvin={kelvin}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _interpolate(
        lo: AnchorPoint, hi: AnchorPoint, kelvin: float
    ) -> Tuple[int, int, int]:
        """
        Linear interpolation (or extrapolation) between two anchor points.
        t < 0 means extrapolation below lo; t > 1 means extrapolation above hi.
        Result is clamped to 0–255 in all cases.
        """
        t = (kelvin - lo.kelvin) / (hi.kelvin - lo.kelvin)
        r = round(lo.r + t * (hi.r - lo.r))
        g = round(lo.g + t * (hi.g - lo.g))
        b = round(lo.b + t * (hi.b - lo.b))
        return (_clamp(r), _clamp(g), _clamp(b))

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, config: list) -> "ColorProfile":
        """
        Build a ColorProfile from the YAML config list.

        Each entry must have:
            kelvin: int
            rgb: [r, g, b]
        """
        anchors = []
        for entry in config:
            kelvin = int(entry["kelvin"])
            r, g, b = [int(v) for v in entry["rgb"]]
            anchors.append(AnchorPoint(kelvin=kelvin, r=r, g=g, b=b))
        return cls(anchors)


def _clamp(value: int, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, value))
