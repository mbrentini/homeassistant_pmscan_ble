from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_DEVICE_NAME, CONF_ADDRESS

_LOGGER = logging.getLogger(__name__)


class NextPmBleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow avec scan BLE et confirmation du device."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, dict] = {}
        self._selected: dict | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Étape 1 : lancer le scan BLE."""
        if user_input is not None:
            return await self.async_step_scan()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Étape 2 : scan BLE et liste des appareils trouvés."""
        if user_input is not None:
            selected_key = user_input.get("device")
            if selected_key and selected_key in self._discovered:
                self._selected = self._discovered[selected_key]
                return await self.async_step_confirm()
            return self.async_abort(reason="device_not_found")

        # Import lazy de bleak pour éviter un crash au chargement du module
        try:
            from bleak import BleakScanner  # noqa: PLC0415
            devices = await BleakScanner.discover(timeout=8)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Erreur lors du scan BLE : %s", exc)
            return self.async_abort(reason="scan_failed")

        self._discovered = {}
        for d in devices:
            if d.name:
                key = d.address
                rssi = getattr(d, "rssi", None)
                self._discovered[key] = {
                    "name": d.name.strip(),
                    "address": d.address,
                    "rssi": rssi,
                }

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        options = {}
        for key, info in self._discovered.items():
            rssi_str = f" | {info['rssi']} dBm" if info["rssi"] is not None else ""
            options[key] = f"{info['name']}  [{info['address']}]{rssi_str}"

        return self.async_show_form(
            step_id="scan",
            data_schema=vol.Schema(
                {vol.Required("device"): vol.In(options)}
            ),
            description_placeholders={"count": str(len(self._discovered))},
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Étape 3 : confirmation avant ajout."""
        if self._selected is None:
            return self.async_abort(reason="device_not_found")

        if user_input is not None:
            address     = self._selected["address"]
            device_name = self._selected["name"]

            await self.async_set_unique_id(f"{DOMAIN}_{address}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{device_name} ({address})",
                data={
                    "name":            device_name,
                    CONF_DEVICE_NAME:  device_name,
                    CONF_ADDRESS:      address,
                },
            )

        rssi = self._selected.get("rssi")
        rssi_str = f"{rssi} dBm" if rssi is not None else "N/A"

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name":    self._selected["name"],
                "address": self._selected["address"],
                "rssi":    rssi_str,
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return NextPmBleOptionsFlow(config_entry)


class NextPmBleOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))
