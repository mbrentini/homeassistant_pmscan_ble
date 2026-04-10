# TERA PMScan (NextPM) — Home Assistant Integration

Custom integration for the **TERA Sensor PMScan (NextPM)** BLE air quality monitor.

This integration connects directly over Bluetooth and exposes PM and climate data
as Home Assistant sensors.

## Features

- Auto-discovery via the Bluetooth integration (device name `Picture`)
- BLE connection using the same protocol as the reference Python scripts
- Sensors:
  - PM1 / PM2.5 / PM10 **particle count** (pcs/L)
  - PM1 **mass concentration** (µg/m³)
  - Temperature (°C)
  - Humidity (%)

> **Note**: Battery level is not exposed yet. Battery reads can destabilize the
> BLE link on some setups, so they are disabled in this version.

## Installation (HACS)

1. In HACS, add a custom repository:
   - URL: `https://github.com/mbrentini/homeassistant_pmscan_ble`
   - Category: `Integration`
2. Search for **TERA PMScan** in HACS and install it.
3. Restart Home Assistant.

The integration will be installed under:

```text
/config/custom_components/pmscan
```

## Configuration

1. Make sure the PMScan/NextPM bridge is powered on and advertising.
2. In Home Assistant, go to **Settings → Devices & Services → Add Integration**.
3. Search for **TERA PMScan**.
4. If the device is discovered via Bluetooth, its address will be pre-filled.
5. Optionally adjust the **Humidity offset** (default `14.1` as calibrated
   from the reference script).
6. Confirm to create the config entry and sensors.

## Entities

The integration exposes the following sensors per device:

- `sensor.<name>_pm1_count` (pcs/L)
- `sensor.<name>_pm25_count` (pcs/L)
- `sensor.<name>_pm10_count` (pcs/L)
- `sensor.<name>_pm1_mass` (µg/m³)
- `sensor.<name>_temperature` (°C)
- `sensor.<name>_humidity` (%)

Availability reflects the BLE connection state and valid frame decoding.

## Known Limitations

- Battery level is not exposed yet. The characteristic is known, but in
  practice some combinations of BlueZ / BLE adapter / HA cause instability
  when reading it periodically.
- Only one HA instance should connect to the PMScan at a time.

## Debugging

To enable debug logs:

```yaml
logger:
  default: warning
  logs:
    custom_components.pmscan: debug
```

Then restart Home Assistant and check the logs for lines starting with
`PMScan connected` and PM frame details.
