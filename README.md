# calibrated_led_poc — Proof of Concept

> ⚠️ **This is a proof-of-concept custom component, not a finished integration.**
> It exists to demonstrate feasibility for [HA Discussion #3538](https://github.com/orgs/home-assistant/discussions/3538).
> Expect rough edges. Do not use in production.

Wraps any RGB or XY-capable light entity and applies a user-defined color
calibration profile to `color_temp_kelvin` commands — correcting the color
casts that LED strips produce when HA uses its generic Kelvin-to-RGB formula.

---

## The problem

When you set a color temperature on an RGB LED strip, HA converts the Kelvin
value to RGB using a formula that assumes standard LED channel primaries. Real
strips deviate significantly from those assumptions. The result: 2700K
"warm white" that looks pink, magenta, or greenish depending on the strip.

There is currently no way to correct this in HA without a template light hack.
This component demonstrates that the fix is simple and fully backwards-compatible.

A second related problem exists for Zigbee LED controllers (e.g. MiBoxer) that
expose XY color control: sending RGB causes a lossy double conversion
(HA: RGB→XY, controller: XY→RGB) before the signal reaches the LEDs.
The XY output mode bypasses this entirely.

---

## How it works

### RGB mode (default)

1. You determine which RGB values your strip needs to produce correct light at
   a given color temperature — by eye, or with a spectrophotometer.
2. You define those as anchor points in YAML.
3. The component intercepts every `color_temp_kelvin` command, linearly
   interpolates your anchor table, and re-issues the call as `rgb_color`
   with the corrected values.

### XY mode

For Zigbee controllers that accept CIE 1931 xy chromaticity natively:

1. You measure the xy values that produce correct light at each target Kelvin,
   using a spectrophotometer (e.g. Argyll `spotread`).
2. The component intercepts `color_temp_kelvin` and re-issues as `xy_color`,
   bypassing the RGB→XY→RGB double conversion entirely.

In both modes, all other commands (brightness, direct color, turn off) are
forwarded unchanged.

---

## Installation

1. Copy the `calibrated_led_poc/` folder into `config/custom_components/`.
2. Add the configuration to `configuration.yaml` (see below).
3. Restart Home Assistant.

Tested on HA 2026.3+. Does not work on earlier versions (mired API removed).

---

## Configuration

### RGB mode

```yaml
calibrated_led_poc:
  - name: "Office East Calibrated"
    entity_id: light.office_east
    color_profile:
      - kelvin: 1800
        rgb: [255, 175, 15]
      - kelvin: 2200
        rgb: [255, 198, 33]
      - kelvin: 2700
        rgb: [255, 230, 60]
      - kelvin: 4000
        rgb: [224, 255, 84]
      - kelvin: 6500
        rgb: [183, 255, 117]
```

### XY mode

For Zigbee controllers with native XY color support. Add `output_mode: xy`
and define anchor points with `x` and `y` chromaticity values instead of `rgb`.

```yaml
calibrated_led_poc:
  - name: "Living TV Calibrated"
    entity_id: light.miboxer_zl5_living_tv
    output_mode: xy
    color_profile:
      - kelvin: 1800
        x: 0.532
        y: 0.432
      - kelvin: 2200
        x: 0.508
        y: 0.426
      - kelvin: 2700
        x: 0.453
        y: 0.408
      - kelvin: 4000
        x: 0.378
        y: 0.375
```

Multiple strips with different modes can be configured simultaneously.

### Finding your anchor values

Anchor values vary by LED source and personal preference. Two approaches:

**By eye (RGB mode):** Use Developer Tools → Actions → `light.turn_on` with
`rgb_color` directly on the underlying entity. Adjust until the result looks
correct at that color temperature, then copy those values into your config.

**By instrument (both modes):** Use a spectrophotometer (e.g. Argyll `spotread
-x -e -T`) to measure the actual CCT and xy of each test value. Iterate until
the measured CCT matches your target. The xy values from each measurement can
be used directly as XY mode anchor points.

### Anchor interpolation and extrapolation

Between anchor points: linear interpolation.
Beyond the outer anchors: linear extrapolation using the slope of the nearest
pair, clamped to valid range (0–255 for RGB, 0.0–1.0 for XY).

A minimum of two anchor points is required. More anchors improve accuracy.

---

## Running the tests

No Home Assistant installation required:

```bash
pip install pytest
PYTHONPATH=calibrated_led_poc python -m pytest tests/ -v
```

18 tests covering both RGB and XY profiles.

---

## Known limitations (PoC scope)

- No UI for calibration — anchors must be entered manually in YAML
- No config flow — YAML only
- `min_color_temp_kelvin` / `max_color_temp_kelvin` are hardcoded, not derived from profile anchors
- Not tested against Adaptive Lighting, though it should work transparently since AL uses standard `light.turn_on` service calls

---

## Relationship to Adaptive Lighting

Because Adaptive Lighting issues standard `light.turn_on` calls with
`color_temp_kelvin`, it passes through this wrapper automatically. No changes
to Adaptive Lighting are needed. Confirmed working in practice.

---

## Roadmap (if adopted into HA core)

| Phase | Scope |
|-------|-------|
| MVP   | Per-entity calibration profile in `configuration.yaml`, hook in `light/__init__.py`, RGB and XY output modes |
| v2    | Multi-point LUT, entity registry storage, UI anchor editor in light card |
| v3    | Full 3×3 color matrix (ICC-style) for accurate hue correction across the color wheel |
