DOMAIN = "pmscan_ble"
DEVICE_NAME = "Picture"

# UUIDs BLE du PMScan / NextPM
INDICATE_60S = "f3641901-00b0-4240-ba50-05ca45bf8abc"
START_CHAR   = "f3641906-00b0-4240-ba50-05ca45bf8abc"
BATTERY_CHAR = "f3641904-00b0-4240-ba50-05ca45bf8abc"

CONF_ADDRESS   = "address"
CONF_RH_OFFSET = "rh_offset"

# Même offset que dans tes scripts locaux
DEFAULT_RH_OFFSET = 14.1

RECONNECT_INTERVAL = 10   # seconds between reconnect attempts
BATTERY_INTERVAL   = 300  # seconds between battery reads