from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_ADDRESS
from .coordinator import PMScanCoordinator, PMScanData, SIGNAL_UPDATE

UNIT_PCS_L = "pcs/L"


@dataclass(frozen=True)
class PMScanSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PMScanData], float | int | None] = lambda d: None


SENSORS: tuple[PMScanSensorDescription, ...] = (
    PMScanSensorDescription(
        key="pm1_pcsl",
        name="PM1 Count",
        native_unit_of_measurement=UNIT_PCS_L,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=lambda d: d.pm1_pcsl,
    ),
    PMScanSensorDescription(
        key="pm25_pcsl",
        name="PM2.5 Count",
        native_unit_of_measurement=UNIT_PCS_L,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=lambda d: d.pm25_pcsl,
    ),
    PMScanSensorDescription(
        key="pm10_pcsl",
        name="PM10 Count",
        native_unit_of_measurement=UNIT_PCS_L,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=lambda d: d.pm10_pcsl,
    ),
    PMScanSensorDescription(
        key="pm1_ugm3",
        name="PM1 Mass",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM1,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.pm1_ugm3,
    ),
    PMScanSensorDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.temperature,
    ),
    PMScanSensorDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.humidity,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PMScanCoordinator = hass.data[DOMAIN][entry.entry_id]
    address = entry.data[CONF_ADDRESS]
    async_add_entities([
        PMScanSensor(coordinator, desc, address) for desc in SENSORS
    ])


class PMScanSensor(SensorEntity):
    entity_description: PMScanSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PMScanCoordinator,
        description: PMScanSensorDescription,
        address: str,
    ) -> None:
        self.entity_description = description
        self._coordinator = coordinator
        self._attr_unique_id = f"{address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name="TERA PMScan",
            manufacturer="TERA SENSOR",
            model="NextPM",
        )

    @property
    def available(self) -> bool:
        return self._coordinator.data.available

    @property
    def native_value(self):
        return self.entity_description.value_fn(self._coordinator.data)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_UPDATE}_{self._coordinator.address}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
    PMScanSensorDescription(
        key="battery",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.battery,
    ),

