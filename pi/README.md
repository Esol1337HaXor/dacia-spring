# OBD2 EV Adapter - Pi Zero Code

## Overview

This directory contains all Python code for the Raspberry Pi Zero 2 W OBD2 adapter project.

## Files

| File | Description | Usage |
|------|-------------|-------|
| `elm327_tcp_server.py` | **Main ELM327 emulator over TCP** | `python elm327_tcp_server.py` |
| `elm327_ble_emulator.py` | BLE GATT Server approach (limited on Pi Zero) | `sudo python elm327_ble_emulator.py` |
| `test_elm327_protocol.py` | Protocol test suite (no server needed) | `python test_elm327_protocol.py` |

## Quick Start

### 1. Test the Protocol Locally

```bash
cd ~/obd2-adapter
source ~/obd2-adapter-env/bin/activate
python test_elm327_protocol.py
```

### 2. Start the TCP Server

```bash
cd ~/obd2-adapter
source ~/obd2-adapter-env/bin/activate
python elm327_tcp_server.py --port 4000
```

### 3. Test with Telnet/Netcat

From another terminal or your PC:

```bash
# Telnet
telnet 192.168.178.87 4000

# Netcat (one-shot test)
echo -e "ATZ\r010C\r" | nc 192.168.178.87 4000
```

## Architecture

```
OBD2-Port im Auto
    ↓
Vgate iCar Pro BLE (liest OBD2-Daten vom Fahrzeug)
    ↓ BLE 4.0
Raspberry Pi Zero 2 W
    ├── bleak (BLE Client) ← liest Daten von Vgate
    ├── RPM Simulator      ← berechnet fake RPM
    └── ELM327 TCP Server  ← emuliert OBD2-Adapter
         ↓ TCP Port 4000
Android Phone (RevHeadz App)
```

## ELM327 Commands Implemented

### AT Commands
- `ATZ` - Reset
- `ATI` - Product info ("iCar Pro BLE")
- `ATE0/ATE1` - Echo off/on
- `ATH0/ATH1` - Header off/on
- `ATS0/ATS1` - Space off/on
- `ATSP0` - Auto protocol selection

### OBD2 PIDs
- `0100` - Supported PIDs
- `0104` - Calculated Engine Load
- `0105` - Coolant Temperature
- `010C` - Engine RPM (simulated)
- `010D` - Vehicle Speed (static 0)
- `010E` - Throttle Position

## Pi Zero Setup Status

### Completed (Schritt 1-4)
- ✅ Raspberry Pi OS Lite installed
- ✅ System packages installed
- ✅ Bluetooth configured
- ✅ Python venv with packages:
  - `bleak 3.0.2` - BLE Client
  - `obd 0.7.3` - OBD2 Protocol
  - `python-elm 1.0a0` - ELM327 Protocol
  - `pyserial 3.5` - Serial Communication

### Pi Zero Access
- **IP:** 192.168.178.87
- **User:** lsd
- **Password:** maxlose288
- **SSH:** Available

## Known Issues

1. **BLE GATT Server** on Pi Zero 2W is limited - use TCP instead
2. **`python-obd`** does not exist on PyPI - use `obd`
3. **`obd2emu`** does not exist on PyPI - use custom implementation
4. **CAN bus connection** not yet implemented - RPM is simulated

## Next Steps

1. Test ELM327 TCP server with Android app
2. Implement Vgate BLE client (bleak)
3. Connect CAN bus for real OBD2 data
4. Implement RPM algorithm from spec