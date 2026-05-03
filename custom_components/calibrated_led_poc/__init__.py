# PROOF OF CONCEPT — not production-ready. See https://github.com/orgs/home-assistant/discussions/3538
"""
calibrated_led_poc — custom component entry point.

Loaded as a top-level integration, not as a light platform.

configuration.yaml:

    calibrated_led_poc:
      - name: "Office East Calibrated LED"
        entity_id: light.office_east
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
"""

from __future__ import annotations

import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import discovery

from .color_profile import ColorProfile

_LOGGER = logging.getLogger(__name__)

DOMAIN = "calibrated_led_poc"

ANCHOR_SCHEMA = vol.Schema(
    {
        vol.Required("kelvin"): vol.All(int, vol.Range(min=1000, max=10000)),
        vol.Required("rgb"): vol.All(
            list,
            vol.Length(min=3, max=3),
            [vol.All(int, vol.Range(min=0, max=255))],
        ),
    }
)

ENTRY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Optional("name"): cv.string,
        vol.Required("color_profile"): vol.All(
            list, vol.Length(min=2), [ANCHOR_SCHEMA]
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(cv.ensure_list, [ENTRY_SCHEMA]),
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
