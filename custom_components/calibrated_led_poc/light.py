# PROOF OF CONCEPT — not production-ready. See https://github.com/orgs/home-assistant/discussions/3538
"""
light.py — CalibratedLedPoc entity.

Wraps an existing HA light entity.  Forwards all service calls unchanged,
except light.turn_on with a color_temp_kelvin argument: those are intercepted,
the color temperature is run through the calibration profile, and the call
is re-issued as an rgb command against the underlying entity.

Requires HA 2026.3+.  Mired-based APIs (ATTR_COLOR_TEMP, min_mireds,
max_mireds) were removed in that release; this file uses only Kelvin.

State is proxied from the underlying entity so HA sees a single light.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .color_profile import ColorProfile

_LOGGER = logging.getLogger(__name__)

LIGHT_DOMAIN = "light"


class CalibratedLedPoc(LightEntity):
    """A light entity that applies a color calibration profile."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        wrapped_entity_id: str,
        profile: ColorProfile,
    ) -> None:
        self._hass = hass
        self._attr_name = name
        self._wrapped_entity_id = wrapped_entity_id
        self._profile = profile
        self._attr_unique_id = f"calibrated_{wrapped_entity_id}"

        # Proxy state
        self._is_on: bool = False
        self._brightness: int | None = None
        self._rgb_color: tuple[int, int, int] | None = None
        self._color_temp_kelvin: int | None = 2700  # default to warm white so UI shows temp slider

    # ------------------------------------------------------------------
    # HA lifecycle
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        """Subscribe to state changes of the wrapped entity."""
        self._sync_state()

        @callback
        def _handle_state_change(event):
            self._sync_state()
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self._hass, [self._wrapped_entity_id], _handle_state_change
            )
        )

    # ------------------------------------------------------------------
    # State proxying
    # ------------------------------------------------------------------

    @callback
    def _sync_state(self) -> None:
        """Pull current state from the wrapped entity."""
        state = self._hass.states.get(self._wrapped_entity_id)
        if state is None or state.state == STATE_UNAVAILABLE:
            self._is_on = False
            self._brightness = None
            self._rgb_color = None
            return

        self._is_on = state.state == STATE_ON
        attrs = state.attributes
        self._brightness = attrs.get(ATTR_BRIGHTNESS)
        self._rgb_color = attrs.get(ATTR_RGB_COLOR)

    # ------------------------------------------------------------------
    # LightEntity properties
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> int | None:
        return self._brightness

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self._rgb_color

    @property
    def color_temp_kelvin(self) -> int | None:
        """Expose last requested Kelvin so the UI temperature slider tracks correctly."""
        return self._color_temp_kelvin

    @property
    def min_color_temp_kelvin(self) -> int:
        return 1000  # extrapolation handles anything below the lowest anchor

    @property
    def max_color_temp_kelvin(self) -> int:
        return 6500

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        # RGB for direct color; COLOR_TEMP is intercepted and translated to RGB
        return {ColorMode.RGB, ColorMode.COLOR_TEMP}

    @property
    def color_mode(self) -> ColorMode:
        if self._color_temp_kelvin is not None:
            return ColorMode.COLOR_TEMP
        return ColorMode.RGB

    # ------------------------------------------------------------------
    # Service calls
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on, intercepting color_temp_kelvin to apply calibration."""
        service_data: dict[str, Any] = {ATTR_ENTITY_ID: self._wrapped_entity_id}

        if ATTR_BRIGHTNESS in kwargs:
            service_data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            kelvin: float = kwargs[ATTR_COLOR_TEMP_KELVIN]
            self._color_temp_kelvin = int(kelvin)

            # --- THE CORE LOGIC ---
            r, g, b = self._profile.rgb_for_kelvin(kelvin)
            _LOGGER.debug(
                "Calibrated %s: %dK -> RGB(%d, %d, %d)",
                self._wrapped_entity_id,
                int(kelvin),
                r, g, b,
            )
            service_data[ATTR_RGB_COLOR] = (r, g, b)
            # Do NOT pass color_temp_kelvin to the underlying entity — it's an RGB strip

        elif ATTR_RGB_COLOR in kwargs:
            # Direct RGB pass-through (user picked a hue on the color wheel)
            self._color_temp_kelvin = None
            service_data[ATTR_RGB_COLOR] = kwargs[ATTR_RGB_COLOR]

        elif ATTR_RGBW_COLOR in kwargs:
            self._color_temp_kelvin = None
            service_data[ATTR_RGBW_COLOR] = kwargs[ATTR_RGBW_COLOR]

        elif ATTR_RGBWW_COLOR in kwargs:
            self._color_temp_kelvin = None
            service_data[ATTR_RGBWW_COLOR] = kwargs[ATTR_RGBWW_COLOR]

        await self._hass.services.async_call(
            LIGHT_DOMAIN, SERVICE_TURN_ON, service_data, blocking=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Forward turn-off to the wrapped entity."""
        await self._hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._wrapped_entity_id},
            blocking=True,
        )


# ---------------------------------------------------------------------------
# Platform setup — called by discovery from __init__.async_setup
# ---------------------------------------------------------------------------

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up CalibratedLedPoc entities from hass.data populated by async_setup."""
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from .color_profile import ColorProfile
    from . import DOMAIN

    entries = hass.data.get(DOMAIN, [])
    entities = []
    for entry in entries:
        wrapped_entity_id = entry["entity_id"]
        name = entry.get("name", f"Calibrated {wrapped_entity_id}")
        profile = ColorProfile.from_config(entry["color_profile"])
        entities.append(CalibratedLedPoc(hass, name, wrapped_entity_id, profile))

    async_add_entities(entities)
