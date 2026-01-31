# Gimdow Smart Lock for Home Assistant

<p align="center">
  <img src="images/icon.svg" alt="Gimdow Lock" width="128" height="128">
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/shrynx/gimdow-tuya.svg)](https://github.com/shrynx/gimdow-tuya/releases)

Home Assistant integration for Gimdow A1 Pro and other Tuya-based smart locks.

## Features

- Lock/Unlock your door remotely
- Battery level monitoring with dynamic icons
- Lock state display (locked/unlocked) with dynamic icons
- Easy setup via UI config flow
- Automatic device discovery from your Tuya account

## Requirements

Before installing, you need:

1. A [Tuya IoT Platform](https://iot.tuya.com) account
2. A Cloud Project with your lock linked
3. "Smart Lock Open Service" API enabled

## Tuya IoT Platform Setup

1. Go to [iot.tuya.com](https://iot.tuya.com) and create an account
2. Create a new **Cloud Project**:
   - Select your region (Europe, US, China, or India)
   - Choose "Smart Home" as the industry
3. Get your credentials from the project **Overview** page:
   - **Client ID** (Access ID)
   - **Client Secret** (Access Secret)
4. Enable APIs:
   - Go to **Service API** → **Go to Authorize**
   - Subscribe to: **Smart Lock Open Service** and **IoT Core**
5. Link your Tuya/Smart Life app:
   - Go to **Devices** → **Link Tuya App Account**
   - Click **Add Device with App Account**
   - Scan the QR code with your Tuya/Smart Life app

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add this repository URL: `https://github.com/shrynx/gimdow-tuya`
4. Select category: **Integration**
5. Click **Add**
6. Search for "Gimdow" and install
7. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/gimdow_lock` folder
2. Copy it to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Gimdow"
4. Enter your Tuya credentials:
   - Client ID
   - Client Secret
   - Region
5. Select your lock from the list
6. Done!

## Supported Devices

- Gimdow A1 Pro
- Other Tuya-based smart locks (category: ms, jtmspro, etc.)

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| lock.door_lock | Lock | Lock/unlock control |
| sensor.door_lock_battery | Sensor | Battery level (%) |

## Services

Standard Home Assistant lock services:

```yaml
# Lock the door
service: lock.lock
target:
  entity_id: lock.door_lock

# Unlock the door
service: lock.unlock
target:
  entity_id: lock.door_lock
```

## CLI Tool

A standalone Python CLI tool is included for testing outside of Home Assistant:

```bash
# Set your credentials
export TUYA_CLIENT_ID="your_client_id"
export TUYA_CLIENT_SECRET="your_client_secret"
export TUYA_DEVICE_ID="your_device_id"
export TUYA_REGION="eu"  # or us, cn, in

# Use
./gimdow unlock
./gimdow lock
./gimdow status
./gimdow info
```

## Troubleshooting

### "No smart locks found"

- Ensure you linked your Tuya/Smart Life app to the cloud project
- Check that "Smart Lock Open Service" API is enabled
- Verify the lock appears in the Tuya IoT Platform devices list

### "Invalid credentials"

- Double-check your Client ID and Secret (no extra spaces)
- Make sure you're using credentials from the correct project

### Lock/Unlock not working

1. Enable remote unlock in the Tuya/Smart Life app:
   - Open lock settings
   - Enable "Remote Unlock"
2. Check the lock is online in the Tuya app
3. Ensure "Smart Lock Open Service" API is subscribed

### Battery shows unknown

Some lock models use different data point codes. Please open an issue with your lock model.

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

MIT License
