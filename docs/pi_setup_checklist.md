# Raspberry Pi Zero 2 W - Installations-Checkliste

## Übersicht

Dieser Checkliste listet alles auf, was auf dem Pi Zero 2 W installiert und konfiguriert werden muss, um:
1. OBD2-Daten vom Vgate iCar Pro BLE auszulesen
2. RPM zu simulieren
3. Einen ELM327-Adapter für RevHeadz zu emulieren

---

## 1. Basis-Betriebssystem

### Raspberry Pi OS Lite (64-bit)
```bash
# Download: https://www.raspberrypi.com/software/
# Empfohlen: Raspberry Pi OS Lite (64-bit) - minimal ohne Desktop
# Flashen mit: Raspberry Pi Imager oder BalenaEtcher
```

### Basis-Konfiguration nach erstem Boot
```bash
# SSH aktivieren (Datei "ssh" in /boot erstellen)
# Oder per raspi-config:
sudo raspi-config

# Empfohlene Einstellungen:
# - Interface Options → SSH → Enable
# - Interface Options → Bluetooth → Enable
# - Advanced Options → Expand Filesystem
# - Change User Password (falls gewünscht)
# - Update完成
```

---

## 2. System-Pakete

### Basis-Tools installieren
```bash
sudo apt update
sudo apt upgrade -y

# Netzwerkwerkzeuge
sudo apt install -y net-tools iputils-ping curl wget git

# Bluetooth-Tools
sudo apt install -y bluetooth bluez blueman

# Python und Entwicklungswerkzeuge
sudo apt install -y python3 python3-pip python3-venv

# USB-Tools (für ggf. späteres USB-OTG)
sudo apt install -y usbutils

# Serial/Comm-Tools
sudo apt install -y minicom screen picocom
```

---

## 3. Bluetooth Konfiguration

### BLE-Unterstützung aktivieren
```bash
# Bluetooth-Dienst starten und aktivieren
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Bluetooth-Status prüfen
bluetoothctl

# In bluetoothctl:
> power on
> agent on
> default-agent
> scan on
```

### BLE-Policy für Headless-Mode
```bash
# BLE-Verbindungen ohne GUI erlauben
sudo sed -i 's/^#Enable.*/Enable=Source,/g' /etc/bluetooth/main.conf
```

---

## 4. Python-Umgebung

### Virtuelle Umgebung erstellen
```bash
# Python-Venv erstellen
python3 -m venv ~/obd2-adapter-env

# Umgebung aktivieren
source ~/obd2-adapter-env/bin/activate

#pip updaten
pip install --upgrade pip

# Python BLE Bibliothek
pip install bleak

# Zusätzliche OBD2-Bibliotheken (optional)
# HINWEIS: "python-obd" existiert NICHT auf PyPI!
# Korrekter Package-Name: "obd"
pip install obd

# ELM327 Emulation
# HINWEIS: "obd2emu" existiert NICHT auf PyPI!
# Verwende python-elm + bleak für eigene ELM327-Emulation
pip install python-elm

# Weitere nützliche Pakete
pip install pyserial  # Für ggf. späteres USB-Serial
pip install asyncio   # Oft schon in Python 3.11+ enthalten
```

---

## 5. ELM327 Emulation

### Option A: Python-basiert (empfohlen)
```bash
# HINWEIS: "python-serial-server" und "obd2-emu" existieren nicht auf PyPI!
# Verwende bleak für BLE GATT Server ELM327-Emulation:
pip install python-elm    # ELM327 Protokoll-Handling
pip install bleak         # BLE GATT Server Implementierung
```

### Option B: System-Dienst für BT-SPP Emulation
```bash
# rfcomm für Bluetooth Serial Port
sudo apt install -y rfcomm

# rfcomm Device erstellen (nach Pairing)
sudo rfcomm bind /dev/rfcomm0 XX:XX:XX:XX:XX:XX 1

# Automatisch beim Boot laden
echo "/dev/rfcomm0 XX:XX:XX:XX:XX:XX 1" | sudo tee -a /etc/bluetooth/rfcomm.conf
```

---

## 6. systemd Services

### OBD2 BLE Reader Service
```bash
sudo tee /etc/systemd/system/obd2-ble-reader.service << EOF
[Unit]
Description=Vgate iCar Pro BLE OBD2 Reader
After=bluetooth.target
Requires=bluetooth.service

[Service]
Type=simple
User=pi
ExecStart=/home/pi/obd2-adapter-env/bin/python /home/pi/obd2-adapter/ble_reader.py
WorkingDirectory=/home/pi/obd2-adapter
Environment=PATH=/home/pi/obd2-adapter-env/bin:/usr/bin:/bin
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### RPM Simulator Service
```bash
sudo tee /etc/systemd/system/rpm-simulator.service << EOF
[Unit]
Description=RPM Simulator für EV-OBD2-Adapter
After=obd2-ble-reader.service

[Service]
Type=simple
User=pi
ExecStart=/home/pi/obd2-adapter-env/bin/python /home/pi/obd2-adapter/rpm_simulator.py
WorkingDirectory=/home/pi/obd2-adapter
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### ELM327 Emulation Service
```bash
sudo tee /etc/systemd/system/elm327-emulator.service << EOF
[Unit]
Description=ELM327 OBD2 Emulator for RevHeadz
After=bluetooth.target rpm-simulator.service

[Service]
Type=simple
User=pi
ExecStart=/home/pi/obd2-adapter-env/bin/python /home/pi/obd2-adapter/elm327_server.py
WorkingDirectory=/home/pi/obd2-adapter
Environment=PATH=/home/pi/obd2-adapter-env/bin:/usr/bin:/bin
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### Services aktivieren
```bash
sudo systemctl daemon-reload
sudo systemctl enable obd2-ble-reader.service
sudo systemctl enable rpm-simulator.service
sudo systemctl enable elm327-emulator.service
```

---

## 7. RevHeadz Verbindung (Android)

### WLAN-Verbindung (empfohlen für RevHeadz)
```bash
# Wenn RevHeadz über WLAN connected:
# Pi als Access Point oder mit Hostapd
sudo apt install -y hostapd dnsmasq

# Hostapd konfigurieren
sudo tee /etc/hostapd/hostapd.conf << EOF
interface=wlan0
driver=nl80211
ssid=OBD2-Adapter
channel=6
wmm_access=0
ieee80211n=1
hw_mode=g
EOF
```

### Bluetooth-SPP für RevHeadz
```bash
# RevHeadz kann über Bluetooth mit OBD2-Adapter connecten
# Pi muss als serial port device erkannt werden
# Siehe oben: rfcomm Konfiguration
```

---

## 8. Auto-Start beim Boot

### Alles auf einmal starten
```bash
sudo systemctl daemon-reload
sudo systemctl enable obd2-ble-reader.service
sudo systemctl enable rpm-simulator.service
sudo systemctl enable elm327-emulator.service

# Automatisch mit Boot starten
sudo raspi-config
# Interface Options → SSH → Enable
```

---

## 9. Projekt-Quellcode

```bash
# Repository klonen (wenn verfügbar)
cd /home/pi
git clone /pfad/zum/repo obd2-adapter

# Oder Dateien manuell kopieren
# structure:
# /home/pi/obd2-adapter/
# ├── ble_reader.py           # Vgate BLE Client
# ├── rpm_simulator.py        # RPM-Algorithmus
# ├── elm327_server.py        # ELM327 Emulation
# ├── config.json             # Konfiguration
# ├── obd2-adapter-env/       # Python venv
# └── logs/                   # Protokolldateien
```

### config.json Beispiel
```json
{
  "vgate": {
    "ble_address": "XX:XX:XX:XX:XX:XX",
    "service_uuid": "0000ffe1-0000-1000-8000-00805f9b34fb",
    "characteristic_uuid": "0000ffe1-0000-1000-8000-00805f9b34fb",
    "scan_interval_ms": 1000
  },
  "rpm_simulator": {
    "idle_rpm": 850,
    "shift_trigger_rpm": 5500,
    "shift_target_rpm": 2800,
    "max_rpm": 7500,
    "smoothing_factor": 0.3
  },
  "elm327": {
    "emulation_mode": "bluetooth_spp",
    "bluetooth_mac": "XX:XX:XX:XX:XX:XX",
    "wifi_mode": false,
    "wifi_ssid": "OBD2-Adapter",
    "wifi_password": ""
  },
  "obd2_pids": {
    "speed_interval_ms": 100,
    "throttle_interval_ms": 200,
    "supported_pids": ["0x00", "0x0C", "0x0D"]
  }
}
```

---

## 10. Tests und Validierung

### BLE-Verbindung testen
```bash
# BLE-Discovery
python3 -c "
import asyncio
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover()
    for d in devices:
        print(f'{d.address} - {d.name}')

asyncio.run(scan())
"
```

### OBD2-PID testen
```bash
# BLE-Verbindung und PID 010D (Speed) lesen
python3 ble_test.py
```

### ELM327-Emulation testen
```bash
# Mit minicom oder telnet
telnet localhost 4000

# AT-Befehle testen:
ATZ
ATI
0100
010D
010C
```

### RevHeadz Verbindung testen
- RevHeadz auf Android öffnen
- OBD2-Verbindung suchen
- Pi als Adapter erkennen
- RPM und Speed anzeigen

---

## Installations-Skript

Ein automatisches Setup-Skript wird erstellt unter:
`scripts/pi_setup.sh`

Dieses Skript führt alle obigen Schritte automatisch aus.

---

## Zusammenfassung der Abhängigkeiten

### System-Pakete (10)
1. net-tools
2. iputils-ping
3. curl
4. wget
5. git
6. bluetooth
7. bluez
8. blueman
9. python3
10. python3-pip

### Python-Pakete (korrigiert)
1. **bleak** - BLE Client + GATT Server (für Vgate iCar Pro + ELM327 Emulation)
2. **obd** - OBD2-Protokoll-Bibliothek (NICHT "python-obd"!)
3. **python-elm** - ELM327 Protokoll-Bibliothek (NICHT "obd2-emu"!)
4. **pyserial** - Serial-Kommunikation
5. **asyncio** - Async I/O (oft schon in Python 3.11+ enthalten)
6. **pint** - Einheiten-Umrechnung (für OBD2 Berechnungen)
7. **pyyaml** - Config-Files
8. **logging** - Logging (stdlib)
9. **json** - Config-Parsing (stdlib)
10. **requests** - HTTP-Client für ggf. Updates

**NICHT auf PyPI verfügbar (stattdessen eigene Implementierung):**
- ~~python-obd~~ → verwende `obd`
- ~~obd2emu~~ → verwende `bleak` GATT Server + `python-elm`
- ~~python-serial-server~~ → verwende `pyserial` + eigene Server-Logik
- ~~obd2-emu~~ → verwende `bleak` + `python-elm`
