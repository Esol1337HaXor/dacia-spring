# Vgate iCar Pro BLE OBD2 - Referenzdokumentation

## Produktinformation

- **Name:** Vgate iCar Pro Bluetooth 4.0 (BLE) OBD2
- **Chipset:** ELM327 (kompatibel)
- **Schnittstelle:** Bluetooth Low Energy 4.0
- **OBD2-Standard:** ISO 15765-4 (CAN 11/500), ISO 9141-2, KWP2000
- **Kompatibel mit:** Dacia Spring (CAN 11/500 OBD2)

## Technische Spezifikationen

### Bluetooth BLE
- **Version:** Bluetooth 4.0 BLE
- **Reichweite:** Bis zu 10 Meter (line of sight)
- **Latency:** ~10-30ms (BLE typisch)
- **Verbindungstyp:** GATT Serial Port Profile (SPS)

### OBD2-Unterstützung
- **ISO 15765-4 (CAN 11/500):** ✅ Ja - Dacia Spring kompatibel
- **ISO 9141-2:** ✅ Ja
- **KWP2000:** ✅ Ja
- **SAE J1850:** ❌ Nein (nicht für EV relevant)

## Android App Integration

### BLE-Verbindung vom Pi aus
Der Vgate iCar Pro kann über BLE von einem Raspberry Pi aus angesprochen werden:

#### Python BLE OBD2 Bibliotheken
```python
# Empfohlene Bibliotheken:
# 1. obd2 (pip install obd2)
# 2. bluepy (für Pi: pip install bluepy)
# 3. bleak (cross-platform BLE: pip install bleak)
```

#### Beispiel: BLE-Verbindung mit bleak
```python
import asyncio
from bleak import BleakClient

# Vgate iCar Pro BLE UUIDs (typisch für ELM327)
SERVICE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

ADDRESS = "XX:XX:XX:XX:XX:XX"  # BLE Address des Vgate

async def connect_and_send():
    async with BleakClient(ADDRESS) as client:
        await client.connect()
        # AT-Befehl senden
        await client.write_gatt_char(CHAR_UUID, b"ATZ\r".encode())
        # Antwort lesen
        response = await client.read_gatt_char(CHAR_UUID)
        print(response.decode())
```

### Verfügbare OBD2-PIDs beim Dacia Spring

#### Direkt verfügbar (Standard OBD2)
| PID | Befehl | Bedeutung | Verfügbarkeit |
|-----|--------|-----------|---------------|
| 0x0D | `010D` | Vehicle Speed | ✅ Ja - direkt vom Vgate lesbar |
| 0x0A | `010A` | Engine Load (Fake) | ⚠️ EV: 0% |
| 0x05 | `0105` | Coolant Temp (Fake) | ⚠️ EV: 0°C oder 40°C |
| 0x0C | `010C` | Engine RPM | ❌ EV: 0 (kein Motor) |
| 0x0B | `010B` | Engine Load (alt) | ⚠️ EV: 0% |
| 0x11 | `0111` | Throttle Position | ⚠️ EV: Fahrpedal-Stellung |

#### EV-spezifische Einschränkung
Da der Dacia Spring ein Elektrofahrzeug ist, können viele Verbrenner-PIDs **nicht** direkt ausgelesen werden:
- RPM = 0 (kein Verbrennungsmotor)
- Engine Load ≈ 0 (andere Logik bei EV)
- Airflow = 0 (kein Luftstrom wie bei Verbrennern)

## Architektur: Pi als BLE OBD2 Client + ELM327 Server

### Datenfluss
```
Vgate iCar Pro (BLE OBD2)
    ↓ BLE Socket
Raspberry Pi Zero 2 W
    ↓ Python BLE Client
RPM-Simulator (Echtzeit-Berechnung)
    ↓ ELM327 Emulation
Bluetooth/WLAN SPP Server
    ↓ ELM327 Protokoll
Android Sound-App
```

### Pi Rollen
1. **BLE OBD2 Client:** Liest Speed von Vgate iCar Pro
2. **ELM327 Server:** Emuliert OBD2-Adapter für Sound-App
3. **Daten-Translator:** Konvertiert EV-Speed → simulierte RPM

## BLE-Verbindung vom Pi zum Vgate

### Voraussetzungen auf Pi Zero 2 W
```bash
# Erforderliche Pakete
sudo apt update
sudo apt install bluetooth bluez python3-pip

# Python Bibliotheken
pip3 install bleak
```

### BLE-Discovery
```python
import asyncio
from bleak import BleakScanner

async def find_vgate():
    devices = await BleakScanner.discover()
    for d in devices:
        if "vgate" in d.name.lower() or "icarus" in d.name.lower():
            print(f"Found: {d.address} - {d.name}")
            return d.address
    return None
```

### Pairing
```bash
# Erstes Pairing mit bluetoothctl
bluetoothctl
> scan on
> pair XX:XX:XX:XX:XX:XX
> trust XX:XX:XX:XX:XX:XX
> connect XX:XX:XX:XX:XX:XX
```

## Alternativen wenn Vgate nicht ausreicht

### Option A: Zusätzliche CAN-Daten via CanZE Plus Android App
- CanZE Plus auf Android installieren
- Daten via WiFi/Netzwerk an Pi weiterleiten
- Nachteil: Komplexere Setup

### Option B: Direkter CAN-Zugriff mit CAN-HAT
- Pican 2 CAN-HAT für Pi Zero 2 W
- Direkter CAN-Bus-Zugriff
- Nachteil: Zusätzliche Hardware (~€25)

### Option C: Hybrid (empfohlen)
- Vgate iCar Pro für Speed (010D)
- CanZE Plus oder eigene App für EV-Daten (Pedal, Power)
- Pi sammelt alles und emuliert ELM327

## Testing vom Vgate iCar Pro

### Manuelles Testen mit Minicom
```bash
# BLE-Verbindung herstellen
minicom -D /dev/rfcomm0 -b 115200

# AT-Befehle testen
ATZ          # Reset
ATI          # Info
ATSP0        # Protokoll auto
0100         # Supported PIDs
010D         # Vehicle Speed
```

### Python Test-Skript
```python
import asyncio
from bleak import BleakClient

async def test_vgate():
    async with BleakClient(ADDRESS) as client:
        # Reset
        await client.write_gatt_char(CHAR_UUID, b"ATZ\r".encode())
        await asyncio.sleep(0.5)
        
        # Info
        await client.write_gatt_char(CHAR_UUID, b"ATI\r".encode())
        await asyncio.sleep(0.5)
        
        # Speed PID
        await client.write_gatt_char(CHAR_UUID, b"010D\r".encode())
        await asyncio.sleep(0.5)
        
        response = await client.read_gatt_char(CHAR_UUID)
        print(f"Speed PID Response: {response.decode()}")

asyncio.run(test_vgate())
```

## Bekannte Probleme

### 1. BLE-Verbindung instabil
- **Lösung:** Pi nah am Vgate platzieren (< 5cm)
- **Lösung:** Externe BLE-Antenne am Pi

### 2. ELM327 Timeouts
- **Lösung:** Timeout auf 500ms+ setzen
- **Lösung:** Retry-Logik implementieren

### 3. Mehrere BLE-Geräte
- **Lösung:** MAC-Adresse des Vgate fixieren
- **Lösung:** BLE-Service-UUID filtern

## Hardware-Setup

### Physische Installation
```
┌─────────────────────────────────────┐
│        Dacia Spring OBD2 Port       │
│         (Fahrzeugmitte, Lenkrad)     │
│              │                      │
│         Vgate iCar Pro              │
│         (direkt eingesteckt)        │
│              │ BLE (Funk)           │
│         Raspberry Pi Zero 2 W       │
│         (im Fahrzeuginneren)        │
│         + USB Stromversorgung       │
└─────────────────────────────────────┘
```

### Stromversorgung Pi
- **Quelle:** OBD2 Pin 16 (12V) → USB-Ladegerät → Micro-USB Pi
- **Oder:** Zigaretteanzünder-Lader → Micro-USB Pi
- **Stromverbrauch:** ~100mA im Betrieb