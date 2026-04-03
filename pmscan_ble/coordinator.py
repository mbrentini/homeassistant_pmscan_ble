from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from bleak import BleakClient, BleakError
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN, INDICATE_60S, START_CHAR, BATTERY_CHAR,
    RECONNECT_INTERVAL, BATTERY_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)
SIGNAL_UPDATE = f"{DOMAIN}_update"

# EOFError = dbus_fast transport disconnect (not a subclass of BleakError/OSError)
_BLE_ERRORS = (BleakError, asyncio.TimeoutError, OSError, EOFError)


@dataclass
class PMScanData:
    pm1_pcsl:    int   = 0
    pm25_pcsl:   int   = 0
    pm10_pcsl:   int   = 0
    pm1_ugm3:    float = 0.0
    temperature: float = 0.0
    humidity:    float = 0.0
    battery:     int   = 0
    last_update: datetime = field(default_factory=datetime.now)
    available:   bool  = False


class PMScanCoordinator:
    """Manages BLE connection and decoding for TERA PMScan (NextPM)."""

    def __init__(self, hass: HomeAssistant, address: str, rh_offset: float) -> None:
        self.hass      = hass
        self.address   = address
        self.rh_offset = rh_offset
        self.data      = PMScanData()
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def async_start(self) -> None:
        self._stop_event.clear()
        self._task = self.hass.async_create_task(self._run_loop())

    async def async_stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._connect_and_stream()
            except _BLE_ERRORS as err:
                _LOGGER.warning(
                    "PMScan disconnected (%s: %s) — retrying in %ds",
                    type(err).__name__, err, RECONNECT_INTERVAL,
                )
                self.data.available = False
                self._notify_ha()
            except asyncio.CancelledError:
                return
            except Exception:
                _LOGGER.exception("Unexpected PMScan error")
                self.data.available = False
                self._notify_ha()
            if not self._stop_event.is_set():
                await asyncio.sleep(RECONNECT_INTERVAL)

    async def _connect_and_stream(self) -> None:
        _LOGGER.debug("Connecting to PMScan at %s", self.address)
        async with BleakClient(self.address, timeout=15.0) as client:
            _LOGGER.info("PMScan connected: %s", self.address)
            await self._read_battery(client)
            await client.start_notify(INDICATE_60S, self._handle_pm)
            await client.write_gatt_char(START_CHAR, bytes([0x01]), response=True)
            self.data.available = True
            self._notify_ha()
            elapsed = 0
            while not self._stop_event.is_set() and client.is_connected:
                await asyncio.sleep(5)
                elapsed += 5
                if elapsed >= BATTERY_INTERVAL:
                    elapsed = 0
                    await self._read_battery(client)

    @callback
    def _handle_pm(self, sender, data: bytearray) -> None:
        """
        Packet layout (20 bytes):
          [0:2]   counter   little-endian uint16
          [5]     cmd       0x11
          [7:9]   d1        pcs/L  0.3-1 um   big-endian
          [9:11]  d25       pcs/L  1-2.5 um   big-endian
          [11:13] d10       pcs/L  2.5-10 um  big-endian
          [13:15] PM1 ug/m3 x0.1              big-endian
          [15:17] RH raw    x0.1  -> 1.1768x - 4.727 + rh_offset
          [17:19] T  raw    x0.1  -> 0.9754x - 4.2488
        """
        raw = bytes(data)
        if len(raw) < 20 or raw[5] != 0x11:
            return

        d1  = int.from_bytes(raw[7:9],   "big")
        d25 = int.from_bytes(raw[9:11],  "big")
        d10 = int.from_bytes(raw[11:13], "big")

        pm1_ugm3 = int.from_bytes(raw[13:15], "big") * 0.1
        rh_raw   = int.from_bytes(raw[15:17], "big") * 0.1
        temp_raw = int.from_bytes(raw[17:19], "big") * 0.1

        temp_c = 0.9754 * temp_raw - 4.2488
        rh_pct = 1.1768 * rh_raw   - 4.727 + self.rh_offset

        # Discard corrupt frames
        if not (0.0 <= temp_c <= 50.0) or not (0.0 <= rh_pct <= 100.0):
            _LOGGER.debug("PMScan: discarding out-of-range frame (T=%.1f RH=%.1f)", temp_c, rh_pct)
            return

        self.data.pm1_pcsl    = d1
        self.data.pm25_pcsl   = d1 + d25
        self.data.pm10_pcsl   = d1 + d25 + d10
        self.data.pm1_ugm3    = round(pm1_ugm3, 1)
        self.data.temperature = round(temp_c, 1)
        self.data.humidity    = round(rh_pct, 1)
        self.data.last_update = datetime.now()
        self.data.available   = True
        self._notify_ha()

    async def _read_battery(self, client: BleakClient) -> None:
        try:
            val = await client.read_gatt_char(BATTERY_CHAR)
            if val:
                self.data.battery = int(val[0])
                self._notify_ha()
        except _BLE_ERRORS as err:
            _LOGGER.debug("Battery read skipped (%s: %s)", type(err).__name__, err)

    @callback
    def _notify_ha(self) -> None:
        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_{self.address}")
