# Technischer Kontext: OBD2 EV Adapter

## Technologien

### Hardware-Komponenten
- **Mikrocontroller:** ESP32 (mit Bluetooth Classic SPP) oder Raspberry Pi Zero 2 W
- **CAN-Interface:** MCP2515 CAN-Controller oder native CAN-Pins (Je nach Plattform)
- **OBD2-Stecker:** Standard 16-poliger OBD2-Stecker für Fahrzeuggewinnung
- **Stromversorgung:** 12V aus OBD2-Port (Pin 16) oder separater USB-Stromversorgung

### Software-Stack
- **Firmware-Plattform:** ESP-IDF (C) oder MicroPython
- **Alternative (Pi):** Raspberry Pi OS + Python 3
- **Bluetooth:** Bluetooth Classic SPP (RFCOMM) - **AUF PI NICHT VERLASSBAR**
- **WiFi TCP:** Alternative zu Bluetooth (Port 2117) - **EMPFOHLEN**
- **Protokoll:** OBD2/ISO 15765-4 (CAN 11-bit, 500kbps)

### Wichtige technische Erkenntnis (2026-06-24 AKTUALISIERT)

#### BLE GATT Kommunikation — IOS-Vlink Adapter ✅ FUNKTIONIERT!
- **BLE GATT:** IOS-Vlink FSC-BT826N per BLE GATT erreichbar!
- **BLE UUIDs:** 
  - Service: `e7810a71-73ae-499d-8c15-faa9aef0c3f2`
  - Char: `bef8d6c9-9c21-4c9e-b632-bd58c1009f9f`
- **ELM327 Commands:** ATZ, ATI, ATSP0, 0100, 010D erfolgreich gesendet
- **bleak v3.0.2:** Auf Pi installiert, funktioniert als root
- **ERFORDERLICH:** Script MUSS als `sudo python3` ausgeführt werden!
- **Dokumentation:** `docs/ble_gatt_ios_vlink_analysis.md`

#### Bluetooth RFCOMM auf Pi Zero 2W:
- pybluez `bluetooth.BluetoothSocket(bluetooth.RFCOMM)` akzeptiert keine Verbindungen
- Fehler: `Bluetooth error: timed out` bei jedem Verbindungsversuch
- **WORKAROUND:** WiFi TCP Server verwenden (elm327_tcp_server.py)
- **WiFi TCP Server:** Port 2117, IP 192.168.178.87, zuverlässig

- **python3-bluez Installation:**
  - Systemweit: `sudo apt install python3-bluez` (nicht im venv!)
  - Version: 0.23 (aktuellste für Python 3.13)
  - Modul: `bluetooth` (nicht `pybluez`!)
  - `bluetooth.advertise_service()` hat anderes Parameter-Schema als Dokumentiert

### Kommunikationsprotokolle

#### OBD2 PID-Standard
- **PID 0x00:** Supported PIDs 01-20 (Bitfeld)
- **PID 0x0C:** Motordrehzahl (RPM) - Emuliert
- **PID 0x0D:** Fahrzeuggeschwindigkeit - Echt aus CAN
- **PID 0x05:** Temperatur (coolant) - Optional, kann fake sein
- **PID 0x04:** Calculated Engine Load - Optional emuliert

#### ELM327 AT-Befehle
- `ATZ` - Reset Gerät
- `ATI` - Herstellerinfo
- `ATE0` - Echo ausschalten
- `ATH0` - Header ausschalten
- `ATS0` - Space ausschalten
- `ATSP0` - Protokoll automatisch auswählen
- `01nnnn` - PID abfragen (z.B. `010C` für RPM)

### CAN-Bus (Dacia Spring)
- **Baudrate:** 500 kbps (ISO 15765-4)
- **Protokoll:** CAN 2.0B (11-bit Identifier)
- **Pinbelegung OBD2:**
  - Pin 6: CAN-High
  - Pin 14: CAN-Low
  - Pin 4/5: GND

### Entwicklungstools
- **ESP32:** PlatformIO, ESP-IDF Toolchain
- **Python:** pip, venv
- **CAN-Diagnose:** CanZE Plus, CANalyzer, SocketCAN
- **Bluetooth-Test:** Android OBD2 Test Apps

### Abhängigkeiten

#### ESP32 (C/MicroPython)
```
ESP-IDF >= v4.4
bluetooth_lib (SPP Server)
can_driver (MCP2515 oder native)
```

#### ESP32 (MicroPython)
```python
bluetooth  # Standard MicroPython Modul
can        # MicroPython CAN Modul
```

#### Raspberry Pi (AKTUELL - 2026-06-15)
```bash
# Systemweit (nicht im venv!)
sudo apt install python3-bluez      # Bluetooth RFCOMM Support
sudo apt install python3-serial     # Serial Communication

# Im venv (~/obd2-adapter-env)
pip install obd              # OBD2-Protokoll-Bibliothek
pip install python-elm       # ELM327 Protokoll-Bibliothek
pip install bleak             # BLE Client + GATT Server
```

#### WiFi TCP Server (EMPFOHLEN)
```python
import socket
# Kein zusätzlicher Bedarf - nur Standard Library
# Port: 2117
# Protocol: TCP/IP
```

### Testumgebung
- **Android:** Physikalisches Gerät mit Bluetooth/WiFi Support
- **Test-Apps:** RevHeadz, Car Scanner ELM OBD2, Potenza Drive
- **CAN-Emulation:** USB-CAN Adapter für Desktop-Tests
- **Bluetooth-Simulation:** SPP Emulator auf Desktop
- **WiFi TCP Test:** Handy im selben WiFi wie Pi, TCP-App auf 192.168.178.87:2117

### WiFi TCP vs Bluetooth SPP Vergleich

| Feature | Bluetooth SPP | WiFi TCP |
|---------|---------------|----------|
| **Zuverlässigkeit** | ❌ Auf Pi fehlerhaft | ✅ Sehr zuverlässig |
| **Pairing** | Erforderlich (PIN) | Kein Pairing nötig |
| **Reichweite** | ~10m | ~50m ( WiFi-Range) |
| **Einrichtung** | Komplex | Einfach (IP+Port) |
| **Firewall** | Keine Probleme | evtl. WiFi-Firewall |
| **App-Unterstützung** | RevHeadz, Car Scanner | Car Scanner, TCP-Apps |
| **Latenz** | 10-50ms | 5-20ms |
| **Empfehlung** | ❌ Nicht auf Pi Zero 2W | ✅ EMPFOHLEN |

### Technische Einschränkungen
- **ESP32 RAM:** Begrenzt (~350KB verfügbar)
- **Bluetooth-Latency:** SPP kann 10-50ms Latency haben
- **Echtzeit-Anforderungen:** CAN-Daten müssen <50ms verarbeitet werden
- **Pi Zero 2 W:** Kann über USB/CAN-HAT angebunden werden