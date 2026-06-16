# Kontext: Aktuelle Arbeit

## Aktueller Fokus
**Phase:** Phase 4 - Master Plan: Vgate iCar Pro BLE → RPM/Gang Simulation (Stand: 2026-06-16 02:15)

## Erfolge (AKTUELL FUNKTIONIERT)

### ✅ RevHeadz TCP/IP Verbindung - VOLLSTÄNDIG FUNKTIONIEREND
- **Server:** `pi/elm327_tcp_server_standalone.py` (PID auf Pi)
- **Port:** 2117 (TCP)
- **IP:** 192.168.178.87 (WiFi)
- **Protocol:** ELM327 Emulation mit Command Normalisierung
- **Features:**
  - Command Normalisierung: `AT Z` → `ATZ`, `01 0C` → `010C`
  - Command Prompt `> ` nach JEDER Antwort
  - RPM Simulation: 850 RPM idle (±20 Jitter)
  - Supported PIDs: `41 00 98 18 00 00` (PID 0C + 0D enthalten)
- **Tested:** RevHeadz Version 1.38 verbindet sich vollständig
- **Log:** `docs/revheadz_fix_protocol.md` (sekundengenaues Protokoll)

### ✅ Server Architektur Dokumentation
- **File:** `docs/pi_system_architecture.md` (~600 Zeilen)
- **Inhalt:** Alle Dienste, Server Architektur, Command Flow, Troubleshooting
- **Dienste:**
  - ✅ ELM327 TCP Server (Port 2117) - AKTIV
  - ⚠️ Bluetooth SPP Server - Inaktiv
  - ⚠️ BLE Emulator - Inaktiv

---

## NÄCHSTER SCHRITT: Vgate iCar Pro Integration

### Ziel
**Vgate iCar Pro BLE Daten als Input für RPM/Gang Simulation verwenden**

### Konzept
```
Vgate iCar Pro (BLE) → Pi Zero 2W → RevHeadz App (WiFi TCP)
    OBD2 CAN Daten       │              Simulator Sound
                         │
                    - BLE Client (bleak)
                    - CAN Bus Parse
                    - RPM Engine
                    - TCP Server
```

### Technische Herausforderung
**Pi Zero 2W BLE Controller (CYC004335B0):**
- Supportt ENTWEDER Central Mode ODER Peripheral Mode
- NICHT gleichzeitig beides!

**Lösung:**
- **BLE:** Pi als Central Mode Client zu Vgate iCar Pro
- **WiFi TCP:** RevHeadz verbindet sich als TCP Client zum Pi
- **WiFi AP (Optional):** Pi als Access Point im Auto

---

## Master Plan: Vgate iCar Pro Integration

### Phase 1: Research & Setup
- [ ] Vgate iCar Pro BLE Protocol analysieren
- [ ] bleak BLE Client Dokumentation prüfen
- [ ] CAN Bus Frame Format Dacia Spring recherchieren
- [ ] hostapd WiFi AP Setup auf Pi Zero 2W testen

### Phase 2: BLE Client Implementierung
- [ ] `pi/ble_client_vgate.py` erstellen
- [ ] Verbindung zu Vgate iCar Pro testen
- [ ] CAN Bus Daten parsen
- [ ] Speed (010D) und Motor RPM (010C) extrahieren

### Phase 3: RPM/Gang Simulation Engine
- [ ] `pi/rpm_simulation_engine.py` erstellen
- [ ] E-Auto Modell (Ein-Pedal-Fahren)
- [ ] RPM/Gear Berechnung implementieren
- [ ] Test mit manuellen Input

### Phase 4: Data Pipeline Integration
- [ ] `pi/data_pipeline.py` erstellen
- [ ] BLE Client + RPM Engine verbinden
- [ ] TCP Server mit echten Daten versorgen
- [ ] RevHeadz Test mit echten OBD2 Daten

### Phase 5: WiFi Access Point (Auto-Einsatz)
- [ ] hostapd + dnsmasq konfigurieren
- [ ] Pi als WiFi AP betreiben
- [ ] RevHeadz im Auto testen

### Phase 6: System Stabilisierung
- [ ] systemd Service für alle Services
- [ ] Auto-Start bei Boot
- [ ] Auto-Recovery bei Crash

---

## Dokumentierter Status (GESICHERT)

### TCP/IP Kommunikation - FUNKTIONIERT ✅
**Test-Protokoll:** `docs/revheadz_fix_protocol.md`

```
0.00  RevHeadz (Android) Version: 1.38, Build: 69
0.74  Connected ✅
0.77  AT Z → OK + Prompt ✅
0.77  AT SP 0 → OK + Prompt ✅
0.84  01 00 → 41 00 98 18 00 00 (RPM+Speed supported) ✅
0.85  01 0C → 41 0C 0D 7C (863 RPM) ✅
0.95  01 0D → 41 0D 00 (0 km/h) ✅
1.02  Initialization complete ✅🎉
```

### Server Dateien (Bereits auf Pi deployed)
- `pi/elm327_tcp_server_standalone.py` - Hauptserver
- `pi/elm327_tcp_server.py` - Original Server
- Start Script: `nohup python3 elm327_tcp_server_standalone.py > server.log 2>&1 &`
- Server Log: `/home/lsd/obd2-adapter/server.log`

### Git Status
- **Repo:** https://github.com/Esol1337HaXor/dacia-spring
- **Branch:** main
- **Letzter Commit:** 9dfdf6c
- **Files:** 8 Dokumentation Files, Server Code, Scripts

---

## Wichtige Technologien

### Aktuell Im Einsatz
- Python 3 (Standard Python auf Pi)
- socket (TCP Server)
- threading (Multi-Client)
- random (RPM Jitter)

### Für Vgate Integration Benötigt
- bleak (BLE Client für Python)
  - Installation: `pip install bleak`
  - Dokumentation: https:// bleak-api.readthedocs.io/
- subprocess (CAN Bus Kommandos)

### Für WiFi AP Optional
- hostapd (WiFi Access Point)
- dnsmasq (DHCP + DNS)

---

## Nächste Immediate Steps

1. **Dokumentation erstellen** (docs/master_plan.md)
2. **bleak Library auf Pi installieren** (für BLE Client)
3. **Vgate iCar Pro BLE Scan durchführen** (Service UUIDs finden)
4. **Proof of Concept: BLE Client testen** (Speed vom Vgate lesen)

---

## Wichtige IPs und Zugänge

### Pi Zero 2W
- **IP:** 192.168.178.87
- **User:** lsd
- **Password:** maxlose288
- **SSH:** ssh lsd@192.168.178.87
- **SSH Key:** ~/.ssh/id_ed25519 (passwortlos)

### Server
- **Port:** 2117
- **Protocol:** TCP/IP ELM327 Emulation

### RevHeadz App
- **Verbindung:** WiFi TCP
- **IP:** 192.168.178.87
- **Port:** 2117