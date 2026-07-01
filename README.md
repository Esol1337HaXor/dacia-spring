# Dacia Spring OBD2 Adapter

Ein System, das einen **Raspberry Pi Zero 2 W** als **ELM327 OBD2-Adapter** ausgeben lässt, um Android-Motorsound-Apps wie **RevHeadz** im **Dacia Spring** (und anderen E-Fahrzeugen) zu betreiben.

Der Pi liest echte CAN-Bus-Daten vom Auto über einen **vGate iCar Pro BT** Bluetooth-Adapter und stellt sie als ELM327 über WiFi bereit. RevHeadz erkennt den Pi als Standard-OBD2-Adapter — Plug-and-Play.

---

## 🎯 Funktionsübersicht

| Komponente | Wert |
|------------|------|
| **Hardware** | Raspberry Pi Zero 2 W + vGate iCar Pro BT |
| **Datenquelle** | Echte CAN-Bus-Daten vom Fahrzeug |
| **Schnittstelle zu App** | WiFi TCP, Port 2117 |
| **ELM327-Emulation** | Vollständig konform (Prompt `> `, Command Normalisierung) |
| **Kompatible Apps** | RevHeadz, Car Scanner, Potenza Drive |
| **Betriebssystem** | Raspberry Pi OS Trixie |

---

## 🔌 Systemarchitektur

```
Auto OBD2 Port
      │
      ▼
┌──────────────────────┐
│  vGate iCar Pro BT   │
│  Bluetooth Classic   │
│  MAC: 13:E0:2F:8D:61:07 │
└──────────┬───────────┘
           │ Bluetooth SPP
           │ RFCOMM Channel 1
           ▼
┌─────────────────────────────────┐
│  Raspberry Pi Zero 2 W          │
│                                 │
│  /dev/rfcomm0 → SPP Reader      │
│  CAN-PIDs: 222003 (Speed)       │
│            22202E (Throttle)    │
│                                 │
│  spp_tcp_server.py              │
│  → Bridgebt CAN zu TCP          │
│  → RPM Engine (Speed+Throttle)  │
│                                 │
│  Port: 2117 / TCP               │
└──────────┬──────────────────────┘
           │ WiFi TCP
           │ Port 2117
           ▼
┌─────────────────────────────────┐
│  Android Phone / Tablet         │
│  RevHeadz / Car Scanner         │
│  - RPM Anzeige                  │
│  - Speed (echt vom CAN-Bus)     │
│  - Throttle (echt vom CAN-Bus)  │
│  - Motorsound-Synthese          │
└─────────────────────────────────┘
```

---

## 🚀 Installation

### Voraussetzungen

- **Hardware:** Raspberry Pi Zero 2 W
- **Hardware:** vGate iCar Pro BT (Bluetooth Classic, NICHT WiFi)
- **OS:** Raspberry Pi OS Trixie (oder neuer)
- **Network:** WiFi mit dem gleichen Netzwerk wie das Android-Gerät

### 1. Repository klonen

```bash
git clone https://github.com/Esol1337HaXor/dacia-spring.git
cd dacia-spring
```

### 2. Installationsskript ausführen

```bash
cd setup
sudo bash install.sh
```

Das Skript führt durch:
- Bluetooth aktivieren
- Pairing mit vGate Adapter (MAC `13:E0:2F:8D:61:07`)
- RFCOMM Device `/dev/rfcomm0` erstellen
- systemd Service installieren und starten

**Falls Pairing manuell nötig:**
```bash
sudo bluetoothctl
[bluetooth]# trust 13:E0:2F:8D:61:07
[bluetooth]# pair 13:E0:2F:8D:61:07
# PIN: 1234 oder 0000
```

### 3. Nach Neustart: RFCOMM neu erstellen

Da `/dev/rfcomm0` nicht persistent ist, nach jedem Neustart:

```bash
cd setup
sudo bash rfcomm_setup.sh
sudo systemctl restart spp-elm327-server
```

---

## 📱 App verbinden

### RevHeadz

1. Verbindungstyp: **WiFi OBD2 Adapter**
2. IP: Pi-Adresse ermitteln (auf dem Pi: `hostname -I`)
3. Port: `2117`
4. Verbinden — fertig

### Car Scanner ELM OBD2

1. Verbindung: **WiFi / TCP**
2. Device: Manuelles Device
3. IP: Pi-Adresse (`hostname -I`)
4. Port: `2117`
5. Protokoll: ELM327

---

## 📡 Echte CAN-Bus-Daten

| CAN-PID | Funktion | Format | Beispiel |
|---------|----------|--------|----------|
| `222003` | Speed (km/h) | 16-bit Big-Endian | `6220030000` → 0 km/h |
| `22202E` | Throttle (%) | 16-bit Big-Endian /10 | `62202E03E8` → 100.0% |

**Throttle-Test:**
- 0 % = Leerlauf (`62202E0000`)
- 91.4 % = Kickdown (`62202E0392`)
- 100 % = Vollgas (`62202E03E8`)

### ELM327 PIDs (an App gesendet)

| PID | Beschreibung | Antwort-Format |
|-----|-------------|----------------|
| `01 00` | Supported PIDs | `41 00 98 18 02 00` |
| `01 0C` | Engine RPM | `41 0C XX XX` (berechnet aus Speed+Throttle) |
| `01 0D` | Vehicle Speed | `41 0D XX` (echt vom CAN-Bus) |
| `01 11` | Throttle Position | `41 11 XX` (echt vom CAN-Bus) |

---

## 🔧 Server verwalten

```bash
# Status prüfen
sudo systemctl status spp-elm327-server

# Neustarten
sudo systemctl restart spp-elm327-server

# Logs
sudo journalctl -u spp-elm327-server -f
```

### SSH-Zugriff auf den Pi

```bash
# Standard-Pi-Login
ssh pi@<PI_IP>
# Standard-Passwort des Pi betreffen

# Service-Status remote
ssh pi@<PI_IP> "systemctl status spp-elm327-server --no-pager"

# Logs remote
ssh pi@<PI_IP> "journalctl -u spp-elm327-server --no-pager -n 50"
```

---

## ✅ Funktionsstatus

| Komponente | Status |
|------------|--------|
| Echte CAN-Bus-Daten vom vGate Adapter | ✅ Funktioniert |
| Bluetooth Classic SPP über RFCOMM | ✅ Funktioniert |
| ELM327 Emulation über WiFi TCP | ✅ Funktioniert |
| RevHeadz Verbindung | ✅ Funktioniert |
| Command Normalisierung | ✅ Funktioniert |
| RPM basierend auf Speed+Throttle | ✅ Funktioniert |
| Speed echt vom CAN-Bus | ✅ Funktioniert |
| Throttle echt vom CAN-Bus | ✅ Funktioniert |
| systemd Auto-Start | ✅ Funktioniert |
| WiFi Access Point (Hotspot) | ❌ Nicht implementiert |

**Zusammengefasst:** Das System funktioniert vollumfänglich mit echten CAN-Bus-Daten. Einziger Punkt, der nicht existiert: der Pi kann keinen eigenen WiFi-Hotspot aufsetzen. Für den typischen Einsatz (Pi im gleichen Heimnetz wie Handy, oder im Auto mit Mobilhotspot) ist das kein Problem.

---

## 🛠️ Probleme lösen

### App verbindet sich nicht

```bash
# Läuft der Server?
pgrep -a python3 | grep spp

# Ist Port offen?
ss -tlnp | grep 2117

# Gleiches WiFi?
hostname -I  # Pi-Adresse mit der des Handys vergleichen
```

### vGate Adapter verbindet sich nicht

```bash
# Pairing-Status prüfen
sudo bluetoothctl info 13:E0:2F:8D:61:07

# RFCOMM neu erstellen
cd setup
sudo bash rfcomm_setup.sh
sudo systemctl restart spp-elm327-server
```

---

## 📁 Projektstruktur

```
dacia-spring/
├── README.md                        # ← Diese Datei
├── Projektpitch.md                  # Projekt-Pitch (deutsch)
├── .gitignore
│
├── setup/                           # Setup-Skripte
│   ├── install.sh                   # Vollständige Installation
│   └── rfcomm_setup.sh              # RFCOMM Device neu erstellen
│
├── pi/                              # Produktions-Code
│   ├── spp_tcp_server.py            # Hauptserver (CAN → ELM327 over TCP)
│   ├── rpm_simulation_engine.py     # RPM-Berechnung aus Speed+Throttle
│   └── spp-elm327-server.service    # systemd Service
│
└── docs/                            # Produktions-Dokumentation
    ├── spp_bluetooth_classic_connection_guide.md  # vGate Einrichtung
    ├── pi_system_architecture.md      # Systemarchitektur
    ├── elm327_commands.md             # ELM327 Befehle
    ├── obd2_pid_reference.md          # OBD2 PID-Referenz
    ├── can_bus_reference.md           # CAN-Bus Referenz
    └── vgate_icar_pro_reference.md    # vGate iCar Pro Info
```

---

## 📚 Dokumentation

| Dokument | Inhalt |
|----------|--------|
| [Bluetooth SPP Guide](docs/spp_bluetooth_classic_connection_guide.md) | vGate iCar Pro BT Einrichtung, Pairing, CAN-PIDs |
| [Systemarchitektur](docs/pi_system_architecture.md) | Alle Dienste, Command-Flows, Debugging |
| [ELM327 Befehle](docs/elm327_commands.md) | Komplette AT-Befehlsreferenz |
| [OBD2 PIDs](docs/obd2_pid_reference.md) | Alle PIDs und Formeln |
| [CAN Bus Referenz](docs/can_bus_reference.md) | CAN-Frame-Formate, Dacia Spring |
| [Vgate iCar Pro](docs/vgate_icar_pro_reference.md) | BLE-UUIDs, Protokoll-Details |

---

## ⚠️ Haftungsausschluss

Dieses Projekt ist nur zu Demonstrations- und Entwicklungszwecken bestimmt.

- Nicht für den Straßenverkehr geeignet
- Keine Zulassung als Diagnosegerät
- Auf eigene Gefahr implementieren und testen
- Nur im privaten, nicht-kommerziellen Einsatz

---

**Repository:** https://github.com/Esol1337HaXor/dacia-spring
**Autor:** Esol1337HaXor
**Letzte Aktualisierung:** 2026-07-01