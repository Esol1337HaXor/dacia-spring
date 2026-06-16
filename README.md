# Dacia Spring OBD2 ELM327 Emulator - RevHeadz Motorsound

![Status](https://img.shields.io/badge/Status-Working-green)
![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_Zero_2W-blue)
![License](https://img.shields.io/badge/License-MIT-blue)

## 🎯 Projektübersicht

Dieses System gibt einen **Raspberry Pi Zero 2 W** als kompatiblen **ELM327 OBD2-Adapter** aus, um Android Motors Sound-Apps wie **RevHeadz** in einem **Dacia Spring Elektroauto** zu betreiben.

Da ein E-Auto keinen Verbrenner hat, werden **simulierte RPM-Werte** basierend auf Fahrpedal und Geschwindigkeit berechnet und über das Standard OBD2/ELM327 Protokoll an die App gesendet.

### ✅ Was funktioniert

- **RevHeadz** (Version 1.38) verbindet sich erfolgreich per WiFi TCP
- **ELM327 Emulation** mit Command Normalisierung (`AT Z` → `ATZ`)
- **Command Prompt `> `** nach jeder Antwort (ELM327 Standard)
- **RPM Simulation** (850 RPM idle, ±20 Jitter)
- **Supported PIDs** korrekt (PID 0C RPM + PID 0D Speed)
- **Auto-Start** beim Pi Boot via systemd Service

### 🎯 Ziel

- Realistische Motorsounds durch simulierte RPM-Werte
- Echte Fahrzeuggeschwindigkeit (später vom Vgate iCar Pro)
- Plug-and-Play über WiFi TCP

---

## 🏗️ Aktuelle Architektur

```
┌─────────────────────────────────────────────────────┐
│              Dacia Spring E-Auto                     │
│                                                      │
│  ┌──────────────────────┐                           │
│  │  Raspberry Pi        │                           │
│  │  Zero 2 W            │                           │
│  │                      │                           │
│  │  ┌────────────────┐  │                           │
│  │  │ systemd Service│  │                           │
│  │  │ elm327-server  │  │                           │
│  │  │ (Auto-Start)   │  │                           │
│  │  └───────┬────────┘  │                           │
│  │          │           │                           │
│  │  ┌───────▼────────┐  │                           │
│  │  │ TCP Server     │  │                           │
│  │  │ Port 2117      │  │                           │
│  │  │ ELM327emu-     │  │                           │
│  │  │ lation         │  │                           │
│  │  └────────────────┘  │                           │
│  └──────────────────────┘                           │
│           │ WiFi TCP                                │
│           │ 192.168.178.87:2117                     │
│           ▼                                        │
│  ┌──────────────────────┐                           │
│  │  Android Phone       │                           │
│  │  RevHeadz App        │                           │
│  │  - RPM Anzeige       │                           │
│  │  - Motorsound        │                           │
│  └──────────────────────┘                           │
└─────────────────────────────────────────────────────┘
```

### Geplante Erweiterung (Vgate iCar Pro)

```
[PLANED]
Vgate iCar Pro BLE → Pi Zero 2W → RevHeadz
    (Echte OBD2     (BLE Client +   (Simulierter
     Daten vom Auto)  RPM Engine)    Motorsound)
```

Siehe [docs/master_plan.md](docs/master_plan.md) für den vollständigen Integrationsplan.

---

## 📁 Projektstruktur

```
dacia-spring/
├── pi/                           # Raspberry Pi Code
│   ├── elm327_tcp_server_standalone.py  # HAUPTSERVER (revheadz kompatibel)
│   ├── elm327_tcp_server.py            # Original Server
│   ├── elm327_ble_emulator.py          # BLE Emulator (inaktiv)
│   ├── bt_spp_server.py                # Bluetooth SPP (inaktiv)
│   ├── elm327-server.service           # systemd Service
│   └── *.sh                            # Hilfs-Scripts
├── docs/                         # Dokumentation
│   ├── revheadz_fix_protocol.md     # RevHeadz Fix Protokoll
│   ├── pi_system_architecture.md    # System Architektur
│   ├── master_plan.md               # Vgate Integration Plan
│   ├── obd2_pid_reference.md        # OBD2 PID Referenz
│   ├── elm327_commands.md           # ELM327 AT-Befehle
│   ├── can_bus_reference.md         # CAN Bus Referenz
│   └── vgate_icar_pro_reference.md  # Vgate iCar Pro Info
├── memory-bank/                  # Cline Memory Bank
│   ├── activeContext.md           # Aktuelle Arbeit
│   ├── productContext.md          # Produktkontext
│   ├── progress.md                # Fortschritt
│   ├── projectbrief.md            # Projektziele
│   ├── systemPatterns.md          # Systemarchitektur
│   └── techContext.md             # Technologien
├── docs/
└── README.md                       # Diese Datei
```

---

## 🚀 Server starten

### Automatischer Start (empfohlen)

Der Server startet automatisch beim Pi Boot via systemd:

```bash
# Status prüfen
sudo systemctl status elm327-server

# Server stoppen/starten
sudo systemctl stop elm327-server
sudo systemctl start elm327-server

# Auto-Start deaktivieren
sudo systemctl disable elm327-server
```

### Manueller Start

```bash
cd /home/lsd/obd2-adapter
nohup python3 elm327_tcp_server_standalone.py > server.log 2>&1 &
disown
```

### Server Status

```bash
# Prozess prüfen
pgrep -a python3 | grep elm327

# Port prüfen
ss -tlnp | grep 2117

# Log anzeigen
tail -f /home/lsd/obd2-adapter/server.log
```

---

## 📡 RevHeadz Verbindung

### Einstellungen in RevHeadz

- **Verbindungstyp:** WiFi OBD2 Adapter
- **IP Adresse:** `192.168.178.87`
- **Port:** `2117`

### Funktionierende Commands

| Command | Beschreibung | Response |
|---------|-------------|----------|
| `AT Z` | Reset | `ELM327 v1.5a\r\nOK\r\n> ` |
| `AT SP 0` | Protocol Auto | `OK\r\n> ` |
| `AT E0` | Echo off | `OK\r\n> ` |
| `AT S0` | Spaces off | `OK\r\n> ` |
| `AT H0` | Header off | `OK\r\n> ` |
| `01 00` | Supported PIDs | `41 00 98 18 00 00` |
| `01 0C` | Engine RPM | `41 0C XX XX` (~850 RPM) |
| `01 0D` | Vehicle Speed | `41 0D XX` (0 km/h) |

### Supported PIDs

```
41 00 98 18 00 00

Byte1 (0x98): PIDs 01, 04, 05
Byte2 (0x18): PID 0C (RPM) ✓, PID 0D (Speed) ✓
```

---

## 🔧 Server Konfiguration

### RPM Simulation

```python
idle_rpm = 850          # Leerlauf
jitter = ±20            # Natürliche Schwankung
max_rpm = 870           # 850 + 20
```

### TCP Port

Standard: **2117**

Ändern in `pi/elm327_tcp_server_standalone.py`:
```python
TCP_PORT = 2117  # Hier ändern
```

### WiFi IP

Die IP wird automatisch beim Start ermittelt (`hostname -I`).

Aktuelle IP: **192.168.178.87**

---

## 📊 Dokumentationen

### Wichtigste Dokumente

| Dokument | Beschreibung |
|----------|-------------|
| [System Architektur](docs/pi_system_architecture.md) | Alle Dienste, Server Funktionsweise |
| [RevHeadz Fix Protokoll](docs/revheadz_fix_protocol.md) | Detailliertes Debug Protokoll |
| [Master Plan](docs/master_plan.md) | Vgate iCar Pro Integration |

### Memory Bank

- [Aktuelle Arbeit](memory-bank/activeContext.md)
- [Produktkontext](memory-bank/productContext.md)
- [Fortschritt](memory-bank/progress.md)
- [Technologien](memory-bank/techContext.md)

### Technische Referenz

- [OBD2 PID Referenz](docs/obd2_pid_reference.md)
- [ELM327 AT-Befehle](docs/elm327_commands.md)
- [CAN Bus Referenz](docs/can_bus_reference.md)

---

## 🛠️ Troubleshooting

### Server startet nicht

```bash
# Log prüfen
cat /home/lsd/obd2-adapter/server.log

# Alten Prozess stoppen
pkill -f elm327_tcp_server

# Server neu starten
sudo systemctl restart elm327-server
```

### RevHeadz kann sich nicht verbinden

1. Prüfen ob Server läuft: `pgrep -a python3 | grep elm327`
2. Prüfen ob Port offen: `ss -tlnp | grep 2117`
3. WiFi Verbindung am Handy prüfen (muss im selben Netzwerk sein)
4. IP Adresse: `192.168.178.87`

### "Timeout waiting for response"

- Alle AT Commands senden jetzt `> ` Prompt
- `AT Z` und andere Commands funktionieren mit/ohne Leerzeichen
- Server Log prüfen: `tail -f /home/lsd/obd2-adapter/server.log`

---

## 📡 Geplante Features

### Phase 1: Grundlegende Funktion ✅ ABGESCHLOSSEN
- [x] TCP Server implementieren
- [x] ELM327 Emulation mit Prompt
- [x] Command Normalisierung
- [x] RPM Simulation (850 idle)
- [x] RevHeadz Verbindung
- [x] systemd Service für Auto-Start

### Phase 2: Vgate iCar Pro Integration 🔄 IN ARBEIT
- [ ] BLE Client zu Vgate iCar Pro
- [ ] Echte Speed-Daten vom Auto
- [ ] Throttle-Simulation
- [ ] RPM Engine erweitern

### Phase 3: WiFi Access Point 📋 PLANUNG
- [ ] Pi als WiFi AP im Auto
- [ ] SSID: DaciaSpring-OBD2
- [ ] RevHeadz verbindet sich direkt zum Pi

### Phase 4: System Stabilisierung 📋 PLANUNG
- [ ] systemd Services für alle Komponenten
- [ ] Auto-Recovery bei Crash
- [ ] Logging und Monitoring

Siehe [docs/master_plan.md](docs/master_plan.md) für Details.

---

## ⚠️ Disclaimer

- **Nur zu Demonstrations/Entwicklungszwecken**
- **Nicht für den Straßenverkehr bestimmt**
- **Keine Garantie für Kompatibilität mit bestimmten Apps**
- **Auf eigene Gefahr implementieren und testen**

---

## 📄 Lizenz

MIT License

---

## 🤝 Contributing

Issues und Pull Requests sind willkommen!

---

**Letzte Aktualisierung:** 2026-06-16  
**Author:** Esol1337HaXor  
**Repo:** https://github.com/Esol1337HaXor/dacia-spring  
**Status:** ✅ RevHeadz Verbindung funktioniert