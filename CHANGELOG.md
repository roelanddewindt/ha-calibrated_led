# Changelog

All notable changes to this proof-of-concept are documented here.

---

## [0.0.2-poc] - 2026-05-05

### Added

- **XY output mode** (`output_mode: xy`) for Zigbee controllers that accept
  CIE 1931 xy chromaticity natively (e.g. MiBoxer via Zigbee2MQTT).
  Bypasses the lossy RGB→XY→RGB double conversion that occurs when sending
  RGB to a controller that only truly understands XY internally.
- `XyColorProfile` class in `color_profile.py` — same linear
  interpolation and extrapolation logic as the RGB profile, operating on
  (x, y) float pairs instead of (R, G, B) integer tuples.
- `XyAnchorPoint` dataclass for type-safe XY anchor storage.
- `ATTR_XY_COLOR` handling in `light.py` — wrapper passes `xy_color`
  to the underlying entity when `output_mode: xy`.
- Dual anchor schema validation in `__init__.py` — RGB anchors require
  `rgb: [r, g, b]`, XY anchors require `x: float` and `y: float`.
- 5 new unit tests covering XY profile interpolation, extrapolation,
  boundary clamping, factory loading, and unsorted anchor handling.

### Changed

- `output_mode` field added to entry schema (optional, default: `rgb`).
  Fully backwards compatible — existing RGB configurations require no changes.
- `supported_color_modes` in `light.py` now returns `{XY, COLOR_TEMP}`
  for XY mode entities, `{RGB, COLOR_TEMP}` for RGB mode entities.
- README updated with XY mode documentation, instrument calibration
  guidance, and revised configuration examples.
- Total unit tests: 18 (was 13), all passing.

---

## [0.0.1-poc] - 2026-02-23

### Added

- Initial proof of concept.
- RGB calibration profile (`ColorProfile`) with linear interpolation
  between anchor points and linear extrapolation beyond outer anchors,
  clamped to 0–255.
- `CalibratedLedPoc` entity wrapping any existing HA light entity.
  Intercepts `color_temp_kelvin` in `light.turn_on` and re-issues as
  `rgb_color` with calibrated values. All other calls forwarded unchanged.
- State proxying from wrapped entity (brightness, rgb_color, on/off).
- YAML configuration under top-level `calibrated_led_poc:` domain key
  (not as a `light: platform:` entry, which is deprecated in HA 2026.3).
- voluptuous schema validation for all config entries and anchor points.
- 13 unit tests — no HA installation required to run.
- PoC markers throughout: version `0.0.1-poc`, banner comment in all
  Python files, prominent warning in README.
