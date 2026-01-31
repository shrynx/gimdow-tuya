"""Constants for Gimdow Lock integration."""

DOMAIN = "gimdow_lock"

# Configuration keys
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_NAME = "device_name"
CONF_REGION = "region"

# Tuya API regions
TUYA_REGIONS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}

# Lock categories in Tuya
LOCK_CATEGORIES = ["ms", "jtmspro", "jtmsbh", "wf_jtmspro", "videolock", "lock"]

# Update interval in seconds
UPDATE_INTERVAL = 30
