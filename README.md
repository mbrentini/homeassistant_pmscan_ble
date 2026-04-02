# TERA PMScan — Home Assistant BLE Integration

Custom integration for the **TERA SENSOR NextPM** particulate matter sensor,
accessed via Bluetooth LE under the device name **"Picture"**.

## Features

| Entity | Unit | Notes |
|---|---|---|
| PM1 Count | pcs/L | Cumulative (0.3–1 µm) |
| PM2.5 Count | pcs/L | Cumulative (0.3–2.5 µm) |
| PM10 Count | pcs/L | Cumulative (0.3–10 µm) |
| PM1 Mass | µg/m³ | Firmware 10s moving average |
| Temperature | °C | Calibrated (NextPM v3.6 formula) |
| Humidity | % | Calibrated + personal offset |
| Battery | % | |

## Installation

1. Copy `custom_components/pmscan_ble/` into `config/custom_components/`.
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → TERA PMScan**
4. Set **humidity offset** = RH_real − RH_measured (e.g. 14.1).

## BLE Packet Layout (reverse-engineered)

```
[0:2]   counter  little-endian uint16
[5]     cmd      0x11
[7:9]   d1       pcs/L  0.3-1 um   (big-endian)
[9:11]  d25      pcs/L  1-2.5 um   (big-endian)
[11:13] d10      pcs/L  2.5-10 um  (big-endian)
[13:15] PM1      ug/m3  x0.1
[15:17] RH raw   x0.1  -> y = 1.1768x - 4.727 + offset
[17:19] T  raw   x0.1  -> y = 0.9754x - 4.2488
```

## References
- TERA SENSOR NextPM User Guide v3.6
- https://github.com/mbrentini/homeassistant_pmscan_ble
