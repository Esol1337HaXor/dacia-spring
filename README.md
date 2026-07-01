# Dacia Spring OBD2 Adapter

![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Platform](https://img. shields.io/badge/Platform-Raspberry%20Pi%20Zero%202W-blue)
![License](https://img.shields.io/badge/License-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.13-informational)

Ein Open-Source-System, das einen **Raspberry Pi Zero 2 W** als **ELM327 OBD2-Adapter** emuliert, um Android-Motorsound-Apps wie **RevHeadz** in Elektrofahrzeugen — speziell dem **Dacia Spring** — betriebsfähig zu machen.

Da E-Fahrzeuge keine Verbrennerdrehzahl bereitstellen können, synthetisiert dieses System virtuelle OBD2-PIDs (RPM, Geschwindigkeit, Drosselklappe) in Echtzeit und stellt sie über standardkonforme ELM327-Kommunikation bereit.

---

## 📋 Inhaltsverzeichnis

- [Überblick](#überblick)
- [Was funktioniert](#was-funktioniert)
- [Systemarchitektur](#systemarchitektur)
- [Schnellstart](#schnellstart)
- [Verbindungsherstellung](#verbindungsherstellung)
- [Unterstützte Commands](#unterstützte-commands)
- [Konfiguration](#konfiguration)
- [Dokumentation](#dokumentation)
- [Projektstruktur](#projektstruktur)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Disclaimer](#disclaimer)

---

## 🎯 Überblick

### Das Problem

Android-Motorsound-Apps (RevHeadz, Potenza Drive, Car Scanner etc.) erwarten OBD2-Daten eines Verbrennungsmotors — insbesondere **RPM (PID 0x0C)** und **Fahrzeuglast (PID 0x04)**. Elektrofahrzeuge wie der Dacia Spring besitzen keinen Verbrenner und liefern diese Werte nativ nicht.

### Die Lösung

Dieses System emuliert einen **ELM327 OBD2-Adapter** auf einem Raspberry Pi Zero 2 W. Es generiert realistische, fahrdynamische RPM- und Geschwindigkeitswerte und stellt sie über **WiFi TCP** (oder alternativ BLE/Bluetooth) bereit. Die Android-App erkennt den Pi als Standard-OBD2-Adapter — Plug-and-Play.

### Betriebsmodi

Das System unterstützt **zwei Betriebsmodi** — wahlweise simuliert oder mit echten Fahrzeugdaten:

#### Modus A: Simulationsmodus (Stand-Alalone)

```
┌──────────────────────────────────────────────────────────────┐
│              Dacia Spring (E-Auto) — Simulationsmodus           │
│                                                                │
│  ┌────────────────────────────────────────────────┐           │
│  │  Raspberry Pi Zero 2 W                          │           │
│  │                                                 │           │
│  │  ┌─────────────────────────────────────────┐   │           │
│  │  │  systemd Service: elm327-server         │   │           │
│  │  │  elm327_tcp_server_standalone.py        │   │           │
│  │  │  (Auto-Start bei Systemstart)           │   │           │
│  │  └────────────────┬────────────────────────┘   │           │
│  │                   │                             │           │
│  │  ┌────────────────▼────────────────────────┐   │           │
│  │  │  Simulierte RPM Engine                  │   │           │
│  │  │  Basis-RPM: 850 (Leerlauf)              │   │           │
│  │  │  Jitter: ±20 RPM                        │   │           │
│  │  │  Supported PIDs: 01, 04, 05, 0C, 0D     │   │           │
│  │  └─────────────────────────────────────────┘   │           │
│  └────────────────────────────────────────────────┘           │
│                        │ WiFi TCP                              │
│                        │ 192.168.x.x:2117                      │
│                        ▼                                      │
│  ┌─────────────────────────────────────────┐                 │
│  │  Android Phone / Tablet                  │                 │
│  │  RevHeadz / Car Scanner / Potenza Drive  │                 │
│  │  - RPM Anzeige (simuliert)               │                 │
│  │  - Motorsound-Synthese                   │                 │
│  └─────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

#### Modus B: Echte Fahrzeugdaten (vGate iCar Pro BT)

```
┌──────────────────────────────────────────────────────────────┐
│              Dacia Spring (E-Auto) — Echte Fahrzeugdaten        │
│                                                                │
│  ┌────────────────────────────────────────────────┐           │
│  │  OBD2 Port im Auto                               │           │
│  │                                                 │           │
│  │  ┌──────────────────────┐                       │           │
│  │  │  vGate iCar Pro BT   │                       │           │
│  │  │  (Bluetooth Classic) │                       │           │
│  │  │  MAC: 13:E0:2F:      │                       │           │
│  │  │     8D:61:07         │                       │           │
│  │  └──────────┬───────────┘                       │           │
│  │             │ Bluetooth Classic SPP             │           │
│  │             │ RFCOMM Channel 1                  │           │
│  │             ▼                                   │           │
│  │  ┌─────────────────────────────────────────┐   │           │
│  │  │  Raspberry Pi Zero 2 W                   │   │           │
│  │  │                                          │   │           │
│  │  │  /dev/rfcomm0 → SPP Reader               │   │           │
│  │  │  PIDs: 222003 (Speed), 22202E (Throttle) │   │           │
│  │  │                                          │   │           │
│  │  │  ┌─────────────────────────────────────┐ │   │           │
│  │  │  │ spp_tcp_server.py                   │ │   │           │
│  │  │  │ → Bridgebt CAN-Daten zu TCP Server  │ │   │           │
│  │  │  │ → RPM Engine (Speed + Throttle)     │ │   │           │
│  │  │  └──────────────┬──────────────────────┘ │   │           │
│  │  │                 │                         │   │           │
│  │  │                 │ WiFi TCP                │   │           │
│  │  │                 │ Port 2117               │   │           │
│  │  │                 ▼                         │   │           │
│  │  └────────────────┬─────────────────────────┘   │           │
│  │                   │                             │           │
│  └───────────────────┼─────────────────────────────┘           │
│                      │ WiFi TCP                                │
│                      │ 192.168.x.x:2117                         │
│                      ▼                                         │
│  ┌─────────────────────────────────────────┐                  │
│  │  Android Phone / Tablet                  │                  │
│  │  RevHeadz / Car Scanner / Potenza Drive  │                  │
│  │  - RPM Anzeige (fahrzeugbasiert)         │                  │
│  │  - Speed (echt vom CAN-Bus)              │                  │
│  │  - Throttle (echt vom CAN-Bus)           │                  │
│  │  - Motorsound-Synthese                   │                  │
│  └─────────────────────────────────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

---

## ✅ Was funktioniert

| Feature | Status | Details |
|---------|--------|---------|
| **RevHeadz Verbindung** | ✅ Working | WiFi TCP zu Port 2117 |
| **ELM327 Emulation** | ✅ Working | Vollständig konform, Prompt `> ` |
| **Command Normalisierung** | ✅ Working | `AT Z` → `ATZ`, `01 0C` → `010C` |
| **RPM Simulation** | ✅ Working | 850 RPM idle, ±20 Jitter |
| **Supported PIDs** | ✅ Working | PID 01, 04, 05, 0C (RPM), 0D (Speed) |
| **AT Commands** | ✅ Working | ATZ, ATI, ATE0, ATH0, ATS0, ATSP0, etc. |
| **systemd Auto-Start** | ✅ Working | Server startet mit Pi-Boot |
| **WiFi TCP Server** | ✅ Working | ELM327 Emulation über TCP Port 2117 |
| **Bluetooth Classic SPP** | ✅ Working | vGate iCar Pro BT über RFCOMM + TCP Bridge |
| **BLE GATT (Vgate iCar Pro WiFi)** | ✅ Working | Echte OBD2-Daten lesbar (root erforderlich) |
| **BLE GATT (IOS-VLink)** | ✅ Working | ELM327 Commands erfolgreich (root erforderlich) |
| **WiFi Access Point** | ⚠️ Vorhanden | Setup-Script verfügbar, noch nicht integriert |

---

## 🚀 Schnellstart

### Betriebsmodus wählen

| Modus | Server | Daten | Erfordert |
|-------|--------|-------|-----------|
| **A: Simulation** | `elm327_tcp_server_standalone.py` | Simuliert (850 RPM idle) | Keine |
| **B: Echte Daten** | `spp_tcp_server.py` | Echt vom vGate iCar Pro BT | vGate iCar Pro BT + Pairing |

### Modus A: Simulationsmodus installieren

```bash
# Auf dem Raspberry Pi: Repository klonen
git clone https://github.com/Esol1337HaXor/dacia-spring.git
cd dacia-spring/pi

# systemd Service installieren (Simulation)
sudo cp elm327-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable elm327-server
sudo systemctl start elm327-server
```

### Modus B: Echte Fahrzeugdaten installieren

```bash
# vGate iCar Pro BTpairing (einmalig)
sudo bluetoothctl
[bluetooth]# trust 13:E0:2F:8D:61:07
[bluetooth]# pair 13:E0:2F:8D:61:07

# RFCOMM erstellen
sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1

# spp_tcp_server starten
cd ~/obd2-adapter
sudo python3 spp_tcp_server.py

# Oder als systemd Service (empfohlen)
sudo cp spp-elm327-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable spp-elm327-server
sudo systemctl start spp-elm327-server
```

### Status prüfen

```bash
# Service-Status
sudo systemctl status elm327-server

# Server-Prozess
pgrep -a python3 | grep elm327

# Offener Port
ss -tlnp | grep 2117

# Live-Log
tail -f /home/lsd/obd2-adapter/server.log
```

### Manuellden Start

```bash
cd /home/lsd/obd2-adapter
nohup python3 elm327_tcp_server_standalone.py > server.log 2>&1 &
disown
```

---

## 🔌 Verbindungsherstellung

### RevHeadz Konfiguration

| Einstellung | Wert |
|-------------|------|
| **Verbindungstyp** | WiFi OBD2 Adapter |
| **IP Adresse** | Automatisch ermitteln (`hostname -I` auf dem Pi) |
| **Port** | `2117` |

### Car Scanner ELM OBD2 Konfiguration

| Einstellung | Wert |
|-------------|------|
| **Verbindung** | WiFi / TCP |
| **Device** | Manuelles Device |
| **IP** | Pi-Adresse |
| **Port** | `2117` |
| **Protokoll** | ELM327 |

### Pi-Adresse ermitteln

```bash
hostname -I
# Ausgabe: 192.168.178.87
```

---

## 📡 Unterstützte Commands

### AT Commands

| Command | Beschreibung | Antwort |
|---------|-------------|---------|
| `AT Z` | Reset Gerät | `OK` |
| `AT I` | Herstellerinfo | `ELM327 v1.5a` |
| `AT E0` | Echo aus | `OK` |
| `AT E1` | Echo an | `OK` |
| `AT H0` | Header aus | `OK` |
| `AT H1` | Header an | `OK` |
| `AT S0` | Spaces aus | `OK` |
| `AT S1` | Spaces an | `OK` |
| `AT SP 0` | Protokoll Auto | `OK` |
| `AT SP 4` | CAN 11/500 | `OK` |

### OBD2 PIDs

| PID | Beschreibung | Antwort-Format | Status |
|-----|-------------|----------------|--------|
| `01 00` | Supported PIDs | `41 00 98 18 00 00` | ✅ |
| `01 04` | Engine Load | `41 04 XX` | ✅ |
| `01 05` | Coolant Temp | `41 05 XX` | ✅ |
| `01 0C` | Engine RPM | `41 0C XX XX` | ✅ |
| `01 0D` | Vehicle Speed | `41 0D XX` | ✅ |

### Supported PIDs Detail (Antwort auf `01 00`)

```
41 00 98 18 00 00

Byte1 (0x98 = 1001 1000): PIDs 01-08
  Bit 7 → PID 01 (Status)           ✓
  Bit 4 → PID 04 (Engine Load)      ✓
  Bit 3 → PID 05 (Coolant Temp)     ✓

Byte2 (0x18 = 0001 1000): PIDs 09-16
  Bit 3 → PID 0C (Engine RPM)       ✓
  Bit 4 → PID 0D (Vehicle Speed)    ✓
```

---

## ⚙️ Konfiguration

### RPM Simulation

```python
# elm327_tcp_server_standalone.py
idle_rpm = 850          # Leerlauf-Drehzahl (RPM)
jitter_range = 20       # Natürliche Schwankung (± RPM)
max_rpm = 870           # idle_rpm + jitter_range
```

**RPM-Berechnung:**
```python
rpm = idle_rpm + random.randint(-jitter_range, jitter_range)
value = rpm * 4         # ELM327 Formel
a = (value >> 8) & 0xFF  # High Byte
b = value & 0xFF         # Low Byte
response = f"41 0C {a:02X} {b:02X}"
```

### TCP Port ändern

```python
TCP_PORT = 2117  # Standard-Port ändern hier
```

### WiFi IP

Die IP wird zur Laufzeit automatisch ermittelt. Keine manuelle Konfiguration nötig.

```bash
# Aktuelle IP prüfen
hostname -I
```

### systemd Service anpassen

```ini
# /etc/systemd/system/elm327-server.service
[Service]
User=lsd
WorkingDirectory=/home/lsd/obd2-adapter
ExecStart=/usr/bin/python3 /home/lsd/obd2-adapter/elm327_tcp_server_standalone.py
Restart=always
RestartSec=5
```

Änderungen aktivieren:
```bash
sudo systemctl daemon-reload
sudo systemctl restart elm327-server
```

---

## 📚 Dokumentation

### Systemdokumentation

| Dokument | Inhalt |
|----------|--------|
| [Systemarchitektur](docs/pi_system_architecture.md) | Vollständige Dienstearchitektur, Command-Flows, Debugging |
| [Master Plan](docs/master_plan.md) | Vgate iCar Pro BLE-Integration, Phasenplan |
| [RevHeadz Fix Protokoll](docs/revheadz_fix_protocol.md) | Detailliertes Debug-Protokoll für RevHeadz-Kompatibilität |

### Technische Referenz

| Dokument | Inhalt |
|----------|--------|
| [OBD2 PID Referenz](docs/obd2_pid_reference.md) | Alle OBD2-PIDs und ihre Formeln |
| [ELM327 Befehle](docs/elm327_commands.md) | Komplette AT-Befehlsreferenz |
| [CAN Bus Referenz](docs/can_bus_reference.md) | CAN-Frame-Formate, Dacia Spring |
| [Vgate iCar Pro](docs/vgate_icar_pro_reference.md) | BLE-UUIDs, Protokoll-Details |
| [BLE GATT iOS Vlink](docs/ble_gatt_ios_vlink_analysis.md) | iOS-kompatible BLE-Emulation |

### Anleitungen

| Dokument | Inhalt |
|----------|--------|
| [Android App Setup](docs/android_app_setup.md) | Konfiguration für RevHeadz, Car Scanner |
| [Pi Setup Checklist](docs/pi_setup_checklist.md) | Ersteinrichtung des Raspberry Pi |
| [Adapter Validation](docs/elm327_adapter_validation.md) | Testing- und Validierungstools |

### Memory Bank

| Datei | Inhalt |
|-------|--------|
| [Active Context](memory-bank/activeContext.md) | Aktuelle Arbeitsschwerpunkte |
| [Product Context](memory-bank/productContext.md) | Produktzweck und User Experience |
| [Progress](memory-bank/progress.md) | Fortschrittsübersicht |
| [Project Brief](memory-bank/projectbrief.md) | Projektziele und Scope |
| [System Patterns](memory-bank/systemPatterns.md) | Architektur-Entscheidungen |
| [Tech Context](memory-bank/techContext.md) | Technologien und Abhängigkeiten |
| [Decisions Log](memory-bank/decisionsLog.md) | Chronologische Entscheidungsprotokolle |

---

## 📁 Projektstruktur

```
dacia-spring/
├── README.md                                # ← Diese Datei
├── Projektpitch.md                          # Projekt-Pitch (deutsch)
├── .gitignore                               # Git Ignore-Regeln
│
├── pi/                                      # Raspberry Pi Code
│   ├── elm327_tcp_server_standalone.py      # ← HAUPTSERVER (Production)
│   ├── elm327_tcp_server.py                 # Original TCP Server
│   ├── elm327_ble_emulator.py               # BLE GATT Server (inaktiv)
│   ├── bt_spp_server.py                     # Bluetooth SPP (inaktiv)
│   ├── elm327_simple.py                     # Einfacher ELM327 Test
│   ├── dynamic_sim_engine.py                # Dynamische Simulations-Engine
│   ├── rpm_simulation_engine.py             # RPM/Gang Engine (E-Auto Modell)
│   ├── obd2_data_pipeline.py                # Daten-Pipeline (Vgate-Integration)
│   │
│   ├── can_bus_sniffer.py                   # CAN-Bus Mitschneider
│   ├── vgate_wifi_can_sniffer.py            # Vgate WiFi CAN Sniffer
│   ├── vgate_bt_rfcomm.py                   # Vgate Bluetooth RFCOMM
│   ├── adapter_validator.py                 # Adapter-Validierungstool
│   │
│   ├── test_*.py                            # Test-Skripte
│   ├── *_test.py                            # Weitere Tests
│   │
│   ├── elm327-server.service                # systemd Service (Production)
│   ├── spp-elm327-server.service            # Bluetooth SPP Service
│   ├── wifi-auto-boot.service               # WiFi Auto-Boot Service
│   │
│   ├── setup_*.sh                           # Setup-Skripte
│   ├── start_*.sh                           # Start-Skripte
│   ├── check_*.sh                           # Status-Prüfung
│   ├── fix_*.sh                             # Reparatur-Skripte
│   └── debug_*.sh                           # Debug-Skripte
│
├── docs/                                    # Dokumentation
│   ├── pi_system_architecture.md            # Systemarchitektur
│   ├── master_plan.md                       # Integrationsplan
│   ├── revheadz_fix_protocol.md             # RevHeadz-Kompatibilität
│   ├── obd2_pid_reference.md                # PID-Referenz
│   ├── elm327_commands.md                   # AT-Befehle
│   ├── can_bus_reference.md                 # CAN-Frame-Formate
│   ├── vgate_icar_pro_reference.md          # Vgate iCar Pro
│   ├── ble_gatt_ios_vlink_analysis.md       # BLE GATT Analyse
│   ├── android_app_setup.md                 # Android-Setup
│   ├── pi_setup_checklist.md                # Pi-Ersteinrichtung
│   ├── vehicle_readout_status.md            # Fahrzeug-Lese-Status
│   ├── spp_bluetooth_classic_connection_guide.md  # Bluetooth Guide
│   └── elm327_adapter_validation.md         # Validierung
│
└── memory-bank/                            # Cline Memory Bank
    ├── projectbrief.md                      # Projektbrief
    ├── productContext.md                    # Produktkontext
    ├── activeContext.md                     # Aktuelle Arbeit
    ├── systemPatterns.md                    # Systemmuster
    ├── techContext.md                       # Technologiekontext
    ├── progress.md                          # Fortschritt
    └── decisionsLog.md                      # Entscheidungsprotokoll
```

---

## 🛠️ Troubleshooting

### Server startet nicht

```bash
# Logs prüfen
sudo journalctl -u elm327-server -n 50 --no-pager
cat /home/lsd/obd2-adapter/server.log

# Alten Prozess stoppen
pkill -f elm327_tcp_server

# Service neu starten
sudo systemctl restart elm327-server
```

### RevHeadz verbindet sich nicht

1. **Server läuft?**
   ```bash
   pgrep -a python3 | grep elm327
   ```

2. **Port offen?**
   ```bash
   ss -tlnp | grep 2117
   # Sollte zeigen: LISTEN 0  128  0.0.0.0:2117
   ```

3. **WiFi im selben Netzwerk?**
   - Pi und Handy müssen im gleichen Subnetz sein
   - Pi-Adresse: `hostname -I`

4. **Firewall?**
   ```bash
   sudo ufw allow 2117/tcp
   ```

### "Timeout waiting for response"

```bash
# Command Normalisierung funktioniert
# Alle Antworten enden mit "> " Prompt

# Logs prüfen
tail -f /home/lsd/obd2-adapter/server.log
```

### RPM wird nicht angezeigt

```python
# 01 00 Antwort muss Byte2 = 0x18 enthalten
# 41 00 98 18 00 00 → Bit 3+4 von Byte2 = RPM + Speed

# Prüfen im Server-Log nach Verbindung
# Suche nach: "01 00" und "01 0C" Requests
```

### SSH-Verbindung instabil

```bash
# Aktive SSH-Sessions prüfen
who
w

# Alte Sessions beenden
pkill -u lsd -t pts/0
```

---

## 🗺️ Roadmap

### Phase 1: Grundlegende Funktion ✅ ABGESCHLOSSEN

- [x] TCP Server implementieren
- [x] ELM327 Emulation mit `> ` Prompt
- [x] Command Normalisierung (`AT Z` → `ATZ`)
- [x] RPM Simulation (850 RPM idle, ±20 Jitter)
- [x] RevHeadz Verbindung erfolgreich
- [x] systemd Service für Auto-Start
- [x] WiFi-basierte Kommunikation

### Phase 2: Echte Fahrzeugdaten-Integration ✅ TEILWEISE ABGESCHLOSSEN

- [x] vGate iCar Pro BT gefunden (Android-Vlink, MAC `13:E0:2F:8D:61:07`)
- [x] Bluetooth Classic Pairing funktioniert
- [x] RFCOMM SPP Verbindung (Channel 1) erfolgreich
- [x] ELM327 v2.3 auf Adapter identifiziert
- [x] CAN-Bus PIDs gelesen: Speed (222003), Throttle (22202E)
- [x] Throttle-Format entschlüsselt (16-bit Big-Endian /10)
- [x] Gasgeben getestet: 0% → 91.4% (Kickdown) → 100% (Vollgas)
- [x] BLE GATT Kommunikation mit vGate iCar Pro WiFi getestet
- [x] BLE GATT Kommunikation mit IOS-VLink getestet

**Status:** Echte CAN-Bus-Daten vom vGate iCar Pro BT lesbar. SPP TCP Server bridgebt die Daten zu RevHeadz. Dokumentation siehe [docs/spp_bluetooth_classic_connection_guide.md](docs/spp_bluetooth_classic_connection_guide.md).

**Bekannte Einschränkungen:**
- Manual Pairing erforderlich vor SPP-Verbindung
- rfcomm0 muss nach jedem Neustart neu erstellt werden
- Server muss als `sudo python3 spp_tcp_server.py` gestartet werden

### Phase 3: WiFi Access Point 📋 PLANUNG

- [ ] Pi als WiFi AP im Auto betreiben
- [ ] SSID: `DaciaSpring-OBD2`
- [ ] DHCP-Server (dnsmasq) konfigurieren
- [ ] Android-Gerät verbindet sich direkt mit Pi
- [ ] hostapd Service einrichten

### Phase 4: System Stabilisierung 📋 PLANUNG

- [ ] systemd Services für alle Komponenten
- [ ] Auto-Recovery bei Crash (Restart=always)
- [ ] Zentrale Logging-Strategie
- [ ] 24h-Dauerlauf-Testing

### Phase 5: Erweiterte Funktionen 📋 VISION

- [ ] Multi-Client Support (mehrere Apps gleichzeitig)
- [ ] Web Dashboard für Live-Monitoring
- [ ] CAN-Bus-Daten direkt lesen (echte Fahrzeugdaten)
- [ ] Dacia Spring-spezifische CAN-Frame-Parsing
- [ ] Adaptives RPM-Modell (Lernende Algorithmen)

---

## ⚠️ Disclaimer

> **Dieses Projekt ist nur zu Demonstrations- und Entwicklungszwecken bestimmt.**
>
> - ❌ **Nicht für den Straßenverkehr geeignet**
> - ❌ **Keine Zulassung als Diagnosegerät**
> - ⚠️ **Auf eigene Gefahr implementieren und testen**
> - 📌 **Keine Garantie für Kompatibilität mit allen Apps**
> - 🔒 **Nur im privaten, nicht-kommerziellen Einsatz**

---

## 📄 Lizenz

[MIT License](LICENSE)

---

## 🤝 Contributing

Issues und Pull Requests sind herzlich willkommen! Bitte lesen Sie vor größeren Änderungen die [Systemarchitektur](docs/pi_system_architecture.md) und den [Master Plan](docs/master_plan.md).

---

## 📬 Kontakt

- **Repository:** https://github.com/Esol1337HaXor/dacia-spring
- **Author:** Esol1337HaXor
- **Letzte Aktualisierung:** 2026-07-01