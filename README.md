# calibrated_led_poc — Proof of Concept

> ⚠️ **This is a proof-of-concept custom component, not a finished integration.**
> It exists to demonstrate feasibility for [HA Discussion #3538](https://github.com/orgs/home-assistant/discussions/3538).
> Expect rough edges. Do not use in production.

Wraps any RGB(WW) light entity and applies a user-defined color calibration
profile to `color_temp_kelvin` commands — correcting the pink/magenta/green
casts that cheap LED strips produce when HA uses its generic Kelvin-to-RGB
formula.

---

## The problem

When you set a color temperature on an RGB strip, HA converts it to RGB using
a formula that assumes standard LED primaries. Real strips — especially cheap
ones — deviate significantly. The result: 2700K "warm white" that looks pink.

There is currently no way to correct this in HA without a template light hack.
This component demonstrates that the fix is simple and fully backwards-compatible.

---

## How it works

1. You measure which RGB values your strip needs to produce a visually correct
   warm white and cool white (and optionally intermediate points).
2. You define those as anchor points in YAML.
3. The component intercepts every `color_temp_kelvin` command, linearly
   interpolates your anchor table, and re-issues the call as `rgb_color`
   with the corrected values.

All other commands (brightness, direct RGB, turn off) are forwarded unchanged.

---

## Installation

1. Copy the `calibrated_led_poc/` folder into `config/custom_components/`.
2. Add the top-level key to `configuration.yaml` (see below).
3. Restart Home Assistant.

Tested on HA 2026.3+. Does not work on earlier versions (mired API removed).

---

## Configuration

```yaml
calibrated_led_poc:
  - name: "Office East Calibrated LED"
    entity_id: light.office_east        # your existing RGB light entity
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
```

### Adjusting the anchor values

The default values are a starting point only — they will vary by LED source and personal preference. To tune them, use Developer Tools → Actions → `light.turn_on` with `rgb_color` directly on the underlying entity, adjust until the result looks right to you at that temperature, and copy those values back into your config.

---

## Running the tests

No Home Assistant installation required:

```bash
pip install pytest
PYTHONPATH=calibrated_led_poc python -m pytest tests/ -v
```

---

## Known limitations (PoC scope)

- No UI for calibration — anchors must be entered manually in YAML
- No config flow — YAML only
- `min_color_temp_kelvin` / `max_color_temp_kelvin` are hardcoded, not derived from the profile anchors
- No support for multi-instance (one entry per strip, no list UI)
- Not tested against Adaptive Lighting, though it should work transparently

---

## Relationship to Adaptive Lighting

Because Adaptive Lighting issues standard `light.turn_on` calls with
`color_temp_kelvin`, it passes through this wrapper automatically. No changes
to Adaptive Lighting are needed.

---

## Roadmap (if adopted into HA core)

| Phase | Scope |
|-------|-------|
| MVP   | 2-anchor linear profile in `configuration.yaml`, hook in `light/__init__.py` |
| v2    | Multi-point LUT, entity registry storage, UI anchor editor in light card |
| v3    | Full 3×3 color matrix (ICC-style) for accurate hue correction across the color wheel |
