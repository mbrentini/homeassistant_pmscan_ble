from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_DEVICE_NAME,
    CONF_ADDRESS,
    START_CHAR_UUID,
    NOTIFY_CHAR_UUID,
    ATTR_STATE,
    ATTR_COUNTER,
    ATTR_PM1_PCSL,
    ATTR_PM25_PCSL,
    ATTR_PM10_PCSL,
)

_LOGGER = logging.getLogger(__name__)

UNIT_MICROGRAMS_M3 = "µg/m³"
UNIT_PCSL          = "pcs/L"
UNIT_DBM           = "dBm"

# Intervalle de mise à jour des entités HA (en secondes)
UPDATE_INTERVAL = 60


@dataclass
class NextPmValues:
    counter: int | None = None
    state: int | None = None
    pm1_pcsl: int | None = None
    pm25_pcsl: int | None = None
    pm10_pcsl: int | None = None
    pm1_ugm3: float | None = None
    pm25_ugm3: float | None = None
    pm10_ugm3: float | None = None
    rssi: int | None = None


class NextPmBleCoordinator:
    """Gère la connexion BLE et le parsing NextPM."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        device_name: str,
        address: str,
    ) -> None:
        self._hass = hass
        self._name = name
        self._device_name = device_name
        self._address = address.upper()

        self._client = None
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._callbacks: list[Callable[[NextPmValues], None]] = []
        self.values = NextPmValues()

        # Timestamp de la dernière mise à jour envoyée aux entités HA
        self._last_update: float = 0.0

    def add_callback(self, cb: Callable[[NextPmValues], None]) -> None:
        self._callbacks.append(cb)

    def _fire(self) -> None:
        """Notifie les entités HA — appelé seulement si l'intervalle est écoulé."""
        now = time.monotonic()
        if now - self._last_update >= UPDATE_INTERVAL:
            self._last_update = now
            for cb in self._callbacks:
                cb(self.values)

    def _fire_force(self) -> None:
        """Notifie les entités sans vérifier l'intervalle (ex: RSSI, premier démarrage)."""
        self._last_update = time.monotonic()
        for cb in self._callbacks:
            cb(self.values)

    async def async_start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = self._hass.loop.create_task(self._run())

    async def async_stop(self) -> None:
        self._stop_event.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except asyncio.TimeoutError:
                pass
        if self._client and self._client.is_connected:
            await self._client.disconnect()

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._connect_and_listen()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("PMSCAN: erreur dans la boucle: %s", exc)
            if not self._stop_event.is_set():
                await asyncio.sleep(5)

    async def _refresh_rssi(self, BleakScanner) -> None:
        """Scan passif pour récupérer le RSSI via AdvertisementData (bleak 2.x)."""
        try:
            results = await BleakScanner.discover(timeout=5, return_adv=True)
            entry = results.get(self._address)
            if entry is not None:
                _device, adv_data = entry
                rssi = getattr(adv_data, "rssi", None)
                if rssi is not None:
                    self.values.rssi = int(rssi)
                    self._fire_force()
                    _LOGGER.debug("PMSCAN: RSSI = %d dBm", rssi)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("PMSCAN: RSSI non récupéré: %s", exc)

    async def _connect_and_listen(self) -> None:
        from bleak import BleakScanner  # noqa: PLC0415
        from bleak_retry_connector import (  # noqa: PLC0415
            establish_connection,
            BleakClientWithServiceCache,
        )
        from homeassistant.components import bluetooth  # noqa: PLC0415

        _LOGGER.info("PMSCAN: connexion à %s (%s)", self._device_name, self._address)

        # RSSI avant connexion
        await self._refresh_rssi(BleakScanner)

        # Récupérer le BLEDevice depuis le stack Bluetooth de HA (proxy ESPHome inclus)
        ble_device = bluetooth.async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )
        if ble_device is None:
            # Fallback : scan direct
            ble_device = await BleakScanner.find_device_by_address(
                self._address, timeout=10
            )
        if ble_device is None:
            raise RuntimeError(f"PMSCAN: appareil {self._address} introuvable")

        def _on_disconnect(_client: object) -> None:
            _LOGGER.warning("PMSCAN: déconnexion inattendue de %s", self._address)

        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self._address,
            disconnected_callback=_on_disconnect,
            max_attempts=3,
        )
        self._client = client

        try:
            _LOGGER.info("PMSCAN: connecté à %s", self._address)

            # ⚠ pair() retiré : peut provoquer une déconnexion sur certains firmwares.
            # Appairer manuellement une fois via bluetoothctl si nécessaire.

            _LOGGER.debug("PMSCAN: activation des notifications sur %s", NOTIFY_CHAR_UUID)
            await client.start_notify(NOTIFY_CHAR_UUID, self._notification_handler)

            _LOGGER.debug("PMSCAN: envoi commande START sur %s", START_CHAR_UUID)
            await client.write_gatt_char(START_CHAR_UUID, bytes([0x01]), response=True)

            _LOGGER.info(
                "PMSCAN: streaming activé (mise à jour HA toutes les %ds).",
                UPDATE_INTERVAL,
            )

            tick = 0
            while not self._stop_event.is_set() and client.is_connected:
                await asyncio.sleep(1)
                tick += 1
                if tick % UPDATE_INTERVAL == 0:
                    await self._refresh_rssi(BleakScanner)

        finally:
            try:
                if client.is_connected:
                    await client.disconnect()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("PMSCAN: erreur déconnexion: %s", exc)
            _LOGGER.info("PMSCAN: déconnecté de %s", self._address)

    def _parse_frame(self, raw: bytes) -> NextPmValues | None:
        # Trame BLE : 4 octets header | 0x81 adresse | cmd | état | données | checksum
        # cmd accepté : 0x11 (10s), 0x12 (60s), 0x13 (15min)
        # Données PM encodées en big-endian (protocole série Tera Sensor)
        if len(raw) < 20 or raw[5] not in (0x11, 0x12, 0x13):
            return None
        return NextPmValues(
            counter   = int.from_bytes(raw[0:2],   "little"),   # header BLE, little-endian
            state     = raw[6],
            pm1_pcsl  = int.from_bytes(raw[7:9],   "big"),
            pm25_pcsl = int.from_bytes(raw[9:11],  "big"),
            pm10_pcsl = int.from_bytes(raw[11:13], "big"),
            pm1_ugm3  = round(int.from_bytes(raw[13:15], "big") * 0.1, 1),
            pm25_ugm3 = round(int.from_bytes(raw[15:17], "big") * 0.1, 1),
            pm10_ugm3 = round(int.from_bytes(raw[17:19], "big") * 0.1, 1),
            rssi      = self.values.rssi,
        )

    def _notification_handler(self, _sender: int, data: bytearray) -> None:
        """Reçoit chaque trame BLE — ne met à jour HA que si l'intervalle est écoulé."""
        raw = bytes(data)
        _LOGGER.debug(
            "PMSCAN raw frame (%d bytes): %s",
            len(raw),
            " ".join(f"{b:02X}" for b in raw),
        )
        vals = self._parse_frame(raw)
        if vals is None:
            return
        self.values = vals
        self._fire()  # throttlé à UPDATE_INTERVAL secondes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    name: str        = entry.data["name"]
    device_name: str = entry.data[CONF_DEVICE_NAME]
    address: str     = entry.data[CONF_ADDRESS]

    coordinator = NextPmBleCoordinator(hass, name, device_name, address)
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    entities = [
        NextPmBleSensor(coordinator, entry, f"{name} PM1",   "pm1"),
        NextPmBleSensor(coordinator, entry, f"{name} PM2.5", "pm25"),
        NextPmBleSensor(coordinator, entry, f"{name} PM10",  "pm10_pcsl"),
        NextPmBleSensor(coordinator, entry, f"{name} RSSI",  "rssi"),
    ]

    async_add_entities(entities)
    await coordinator.async_start()


class NextPmBleSensor(SensorEntity):
    """Entité capteur PMSCAN."""

    _attr_should_poll = False

    def __init__(
        self,
        coordinator: NextPmBleCoordinator,
        entry: ConfigEntry,
        name: str,
        kind: str,
    ) -> None:
        self._coordinator = coordinator
        self._kind = kind

        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{kind}"
        self._attr_state_class = SensorStateClass.MEASUREMENT

        if kind in ("pm1", "pm25"):
            self._attr_native_unit_of_measurement = UNIT_MICROGRAMS_M3
            self._attr_device_class = SensorDeviceClass.PM25
        elif kind == "pm10_pcsl":
            self._attr_native_unit_of_measurement = UNIT_MICROGRAMS_M3
            self._attr_device_class = SensorDeviceClass.PM10
        elif kind == "rssi":
            self._attr_native_unit_of_measurement = UNIT_DBM
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data["name"],
            manufacturer="Tera Sensor",
            model="PMSCAN bridge",
        )

        coordinator.add_callback(self._on_update)

    @callback
    def _on_update(self, _vals: NextPmValues) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        v = self._coordinator.values
        match self._kind:
            case "pm1":       return v.pm1_ugm3
            case "pm25":      return v.pm25_ugm3
            case "pm10_pcsl": return v.pm10_ugm3
            case "rssi":      return v.rssi
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        v = self._coordinator.values
        return {
            ATTR_COUNTER:   v.counter,
            ATTR_STATE:     f"0x{v.state:02x}" if v.state is not None else None,
            ATTR_PM1_PCSL:  v.pm1_pcsl,
            ATTR_PM25_PCSL: v.pm25_pcsl,
            ATTR_PM10_PCSL: v.pm10_pcsl,
        }
