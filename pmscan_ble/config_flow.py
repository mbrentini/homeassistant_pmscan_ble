from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, DEVICE_NAME, CONF_ADDRESS, CONF_RH_OFFSET, DEFAULT_RH_OFFSET


class PMScanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _discovered_address: str | None = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> FlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovered_address = discovery_info.address
        return await self.async_step_confirm()

    async def async_step_user(self, user_input=None) -> FlowResult:
        discovered = [i for i in async_discovered_service_info(self.hass) if (i.name or "").strip() == DEVICE_NAME]
        if discovered and not self._discovered_address:
            self._discovered_address = discovered[0].address
        return await self.async_step_confirm(user_input)

    async def async_step_confirm(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            address = user_input.get(CONF_ADDRESS, self._discovered_address)
            rh_offset = user_input.get(CONF_RH_OFFSET, DEFAULT_RH_OFFSET)
            if not address:
                errors[CONF_ADDRESS] = "no_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"TERA PMScan ({address})",
                    data={CONF_ADDRESS: address, CONF_RH_OFFSET: rh_offset},
                )
        schema = vol.Schema({
            vol.Required(CONF_ADDRESS, default=self._discovered_address or ""): str,
            vol.Optional(CONF_RH_OFFSET, default=DEFAULT_RH_OFFSET): vol.Coerce(float),
        })
        return self.async_show_form(step_id="confirm", data_schema=schema, errors=errors,
                                    description_placeholders={"device_name": DEVICE_NAME})
