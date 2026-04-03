# TERA PMScan — Home Assistant BLE Integration

Custom integration for the **TERA SENSOR NextPM** particulate matter sensor,
accessed via Bluetooth LE under the device name **"Picture"**.

## Entities

| Entity | Unit | Description |
|---|---|---|
| PM1 Count | pcs/L | Cumulative 0.3–1 µm |
| PM2.5 Count | pcs/L | Cumulative 0.3–2.5 µm |
| PM10 Count | pcs/L | Cumulative 0.3–10 µm |
| PM1 Mass | µg/m³ | Firmware 10s moving average |
| Temperature | °C | Calibrated: 0.9754×raw - 4.2488 |
| Humidity | % | Calibrated: 1.1768×raw - 4.727 + offset |
| Battery | % | Read every 5 min |

## BLE Packet Layout (reverse-engineered, 20 bytes)

```
[0:2]   counter   little-endian uint16
[5]     cmd       0x11
[7:9]   d1        pcs/L  0.3–1 µm    big-endian
[9:11]  d25       pcs/L  1–2.5 µm    big-endian
[11:13] d10       pcs/L  2.5–10 µm   big-endian
[13:15] PM1 µg/m³ × 0.1              big-endian
[15:17] RH raw    × 0.1 → 1.1768x - 4.727 + offset
[17:19] T  raw    × 0.1 → 0.9754x - 4.2488
```

## BLE Characteristics (service f3641900-00b0-4240-ba50-05ca45bf8abc)

| UUID suffix | Role |
|---|---|
| ...01 | Indicate — 60s average PM data |
| ...04 | Battery % (1 byte read) |
| ...06 | START_CHAR — write 0x01 to start stream |

## Installation

1. Copy `custom_components/pmscan_ble/` into HA `config/custom_components/`.
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → TERA PMScan**
4. Set **humidity offset** = RH_reference − RH_measured (e.g. 14.1).

## Links
- https://github.com/mbrentini/homeassistant_pmscan_ble
- TERA SENSOR NextPM User Guide v3.6
