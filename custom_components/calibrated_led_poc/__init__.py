# PROOF OF CONCEPT — not production-ready. See https://github.com/orgs/home-assistant/discussions/3538
"""
calibrated_led_poc — custom component entry point.

Loaded as a top-level integration, not as a light platform.

RGB mode (default) — intercepts color_temp_kelvin and re-issues as rgb_color.
Use for raw RGB strips where HA controls channels directly.

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

XY mode — intercepts color_temp_kelvin and re-issues as xy_color.
Use for Zigbee controllers that accept xy natively, bypassing lossy
RGB→XY→RGB double conversion.

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
"""

from __future__ import annotations

import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import discovery

from .color_profile import ColorProfile, XyColorProfile

_LOGGER = logging.getLogger(__name__)

DOMAIN = "calibrated_led_poc"
OUTPUT_MODE_RGB = "rgb"
OUTPUT_MODE_XY = "xy"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

RGB_ANCHOR_SCHEMA = vol.Schema({
    vol.Required("kelvin"): vol.All(int, vol.Range(min=1000, max=10000)),
    vol.Required("rgb"): vol.All(
        list, vol.Length(min=3, max=3),
        [vol.All(int, vol.Range(min=0, max=255))],
    ),
})

XY_ANCHOR_SCHEMA = vol.Schema({
    vol.Required("kelvin"): vol.All(int, vol.Range(min=1000, max=10000)),
    vol.Required("x"): vol.All(float, vol.Range(min=0.0, max=1.0)),
    vol.Required("y"): vol.All(float, vol.Range(min=0.0, max=1.0)),
})

def _validate_entry(value):
    """Validate a single strip entry, choosing anchor schema based on output_mode."""
    mode = value.get("output_mode", OUTPUT_MODE_RGB)
    if mode == OUTPUT_MODE_XY:
        anchor_schema = XY_ANCHOR_SCHEMA
    else:
        anchor_schema = RGB_ANCHOR_SCHEMA
    schema = vol.Schema({
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("name"): cv.string,
        vol.Optional("output_mode", default=OUTPUT_MODE_RGB): vol.In(
            [OUTPUT_MODE_RGB, OUTPUT_MODE_XY]
        ),
        vol.Required("color_profile"): vol.All(
            list, vol.Length(min=2), [anchor_schema]
        ),
    })
    return schema(value)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(cv.ensure_list, [_validate_entry]),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up calibrated_led_poc from configuration.yaml."""
    entries = config.get(DOMAIN, [])
    hass.data[DOMAIN] = entries

    if entries:
        hass.async_create_task(
            discovery.async_load_platform(
                hass, Platform.LIGHT, DOMAIN, {}, config
            )
        )

    return True
