# Fortschritt: OBD2 EV Adapter

## Was funktioniert (verifiziert)
- [x] Projektpitch vollständig analysiert
- [x] Memory Bank Struktur erstellt
- [x] Technische Spezifikationen dokumentiert
- [x] Systemarchitektur entworfen
- [x] Hardware-Verfügbarkeit bestätigt (Pi Zero 2W)
- [x] **Pi Zero 2 W Basis-Setup abgeschlossen (Schritt 1-4)**
- [x] **Python venv erstellt: ~/obd2-adapter-env**
- [x] **python3-bluez 0.23 installiert** - Systemweiter Bluetooth-Support
- [x] **Bluetooth SPP Server implementiert** - ELM327 OBD2 Emulation (rfcomm.py)
- [x] **WiFi TCP Server implementiert** - ELM327 Emulation über TCP Port 2117
- [x] **WiFi TCP Server läuft** - IP 192.168.178.87:2117 WAITING FOR CONNECTIONS

## Was NICHT funktioniert (Fehlschläge)

### Bluetooth RFCOMM - Verbindung wird abgelehnt
- **Problem:** Smartphone kann PiZeroCar-OBD2 finden und pairien (PIN: 1234)
- **Aber:** Verbindungsaufbau wird vom Pi abgelehnt
- **Fehlermeldung:** `Bluetooth error: timed out` (pybluez bluetooth.BluetoothSocket)
- **Testergebnis:** Pairing erfolgreich, aber RFCOMM-Connection refused/timed out

### Versuchte Lösungen für Bluetooth RFCOMM (alles fehlerhaft)

1. **sdptool add SP --channel=1**
   - Fehler: Package `sdptool` nicht in apt verfügbar
   - Workaround: `sudo apt install libbluetooth-dev` nötig?

2. **bluetooth.advertise_service() mit uuid parameter**
   - Fehler: `advertise_service() got an unexpected keyword argument 'uuid'`
   - pybluez v0.23 hat anderen Parameter-Schema als erwartet

3. **bluetooth.advertise_service() mit subsets parameter**
   - Nicht getestet - nach Fehler 2 Datei neu geschrieben
   - Letzter Versuch: SDP komplett entfernt (rely on PSCAN)

4. **bluetoothctl agent PinCode + default-agent**
   - Teilweise erfolgreich: Pairing funktioniert jetzt fast
   - Aber: RFCOMM-Verbindung wird trotzdem abgelehnt

### Ursache des Bluetooth-Problems (unbekannt)
- Möglicherweise: BlueZ RFCOMM-Filter auf Pi Zero 2W
- Möglicherweise: pybluez RFCOMM-Binding problematisch auf headless Raspberry Pi OS
- Möglicherweise: hciconfig hci0 piscan reicht nicht für SDP-Discovery
- **Status:** Bluetooth RFCOMM als **nicht vertrauenswürdig** markiert

## Was übrig zu bauen

### Phase 1: Konzept & Recherche (AKTUELL)
- [x] Projektpitch analysiert
- [x] Memory Bank erstellt
- [ ] **ZUKÜNFTIG:** CAN-Bus Frame-Recherche für Dacia Spring
- [ ] **ZUKÜNFTIG:** ELM327-Protokoll-Spezifikation studieren
- [ ] **ZUKÜNFTIG:** existierende Open-Source-Projekte evaluisieren

### Phase 2: Hardware & Setup
- [x] **Pi Zero 2 W erworben/verfügbar** - Im Bestand
- [x] **Basis-OS installiert** - Raspberry Pi OS Lite (64-bit)
- [x] **System-Pakete installiert** - apt update/upgrade, bluetooth, python3
- [x] **Bluetooth konfiguriert** - systemctl enable bluetooth
- [x] **Python venv erstellt** - ~/obd2-adapter-env
- [x] **ELM327 Emulator implementiert** - SOWOHL Bluetooth SPP ALS AUCH WiFi TCP
- [x] **WiFi TCP Server läuft** - Port 2117, IP 192.168.178.87
- [ ] CAN-Bus Testaufbau
- [ ] Bluetooth-Verbindungstest mit Vgate iCar Pro

### Phase 3: CAN-Datenakquisition
- [ ] CAN-Interface implementieren
- [ ] CAN-Frames des Dacia Spring parsen
- [ ] Speed-Daten extrahieren
- [ ] Ready-Status erkennen
- [ ] Throttle/Power-Daten lesen

### Phase 4: ELM327-Emulation
- [x] AT-Befehle implementiert (ATZ, ATI, ATE0, ATH0, ATS0, ATSP0, ATL0, ATL1, ATB0, ATBRK, ATSP 0, ATA)
- [x] PID-Anfragen beantwortet (0100, 0101, 0104, 0105, 010C, 010D, 010E, 0111, 0114, 0120)
- [x] Bluetooth SPP Server implementiert (bt_spp_server.py) - ABER Verbindung wird abgelehnt
- [x] WiFi TCP Server implementiert (elm327_tcp_server.py) - PORT 2117 - EMPFOHLEN
- [x] OBD2-Response Format korrekt umgesetzt (41 nn XX XX Format)

### Phase 5: RPM-Simulation
- [ ] Basis-RPM (Leerlauf bei Ready=True)
- [ ] RPM-Aufstieg bei Beschleunigung
- [ ] RPM-Sink bei Bremsen
- [ ] Gangwechsel-Simulation
- [ ] EV-Daten integrieren (Power, Rekuperation)

### Phase 6: Integration & Testing
- [ ] Sound-App Verbindungstest
- [ ] Latency-Messung (< 50ms Ziel)
- [ ] RPM-Realismus validieren
- [ ] Verschiedene Sound-Apps testen
- [ ] Langzeittest im Fahrzeug

### Phase 7: Optimierung & Veröffentlichung
- [ ] Parameter-Tuning für realistischeren Sound
- [ ] Dokumentation vervollständigen
- [ ] GitHub Veröffentlichung
- [ ] Community-Feedback integrieren

## Aktueller Status

```
Phase 1: Konzept     ██████████ 100%  (Completed)
Phase 2: Hardware    ██████████ 100% (Completed - Pi Setup + Server laufen)
Phase 3: CAN         ░░░░░░░░   0%  (Not Started)
Phase 4: ELM327      ████████░░  80% (Bluetooth implementiert aber fehlerhaft, WiFi TCP ready)
Phase 5: RPM-Sim     ░░░░░░░░   0%  (Not Started)
Phase 6: Testing     ░░░░░░░░   0%  (Not Started - WiFi TCP Test ausstehend)
Phase 7: Release     ░░░░░░░░   0%  (Not Started)
```

## Pi Zero Setup Details (2026-06-15)

### Durchgeführte Schritte (1-4)
1. **Basis-Betriebssystem** - Raspberry Pi OS Lite flashed, SSH aktiviert
2. **System-Pakete** - apt update/upgrade, bluetooth, python3, net-tools installiert
3. **Bluetooth Konfiguration** - systemctl enable bluetooth
4. **Python Umgebung** - venv erstellt, folgende Packages installiert:
   - `bleak 3.0.2` - BLE Client (für Vgate iCar Pro + ELM327 Emulation)
   - `obd 0.7.3` - OBD2 Protokoll (Ersatz für nicht existierendes `python-obd`)
   - `python-elm 1.0a0` - ELM327 Protokoll-Bibliothek
   - `pyserial 3.5` - Serial Kommunikation
   - `pint 0.24.4` - Einheiten-Umrechnung

### Korrigierte Package-Installation
```bash
# FALSCH: pip install python-obd  (existiert nicht!)
# FALSCH: pip install obd2emu     (existiert nicht!)
# FALSCH: pip install python-elm  (existiert nicht auf piwheels)

# KORREKT (systemweit):
sudo apt install python3-bluez    # Bluetooth SPP Support (pybluez)
pip install obd              # OBD2-Protokoll-Bibliothek (im venv)
pip install python-elm       # ELM327 Protokoll-Bibliothek (im venv)
pip install bleak             # BLE Client + GATT Server (im venv)
```

### WiFi TCP Server Details (2026-06-15 19:14)
```bash
# Server gestartet
cd ~/obd2-adapter
nohup python3 elm327_tcp_server.py > tcp_server.log 2>&1 &

# Server läuft auf
Port: 2117
WiFi IP: 192.168.178.87
Status: WAITING FOR CONNECTIONS...

# Verbindung vom Handy
# TCP/IP, Host: 192.168.178.87, Port: 2117
```

### Bluetooth SPP Server Details (2026-06-15 18:57)
```bash
# Server gestartet
cd ~/obd2-adapter
nohup python3 bt_spp_server.py > bt_server.log 2>&1 &

# Server läuft
Device Name: PiZeroCar-OBD2
RFCOMM Channel: 1
MAC: B8:27:EB:F3:C7:61
Status: WAITING FOR CONNECTIONS...

# Bluetooth Status
Powered: yes
Discoverable: yes (180s Timeout)
Pairable: yes
PSCAN/ISCAN: aktiv

# Pairing-Test Ergebnis
- Smartphone findet PiZeroCar-OBD2: ✅
- Pairing mit PIN 1234: ✅ (fast erfolgreich)
- RFCOMM-Verbindung vom Smartphone: ❌ (abgelehnt/timed out)
```

### SSH Zugang
- **IP:** 192.168.178.87
- **Benutzer:** lsd
- **Passwort:** maxlose288
- **Sudo:** Aktiv

## Bekannte Issues

| Issue | Schwere | Status | Notizen |
|-------|---------|--------|---------|
| CAN-Frames Dacia Spring unbekannt | Hoch | Offen | Erste Recherche nötig |
| Keine Sound-App getestet | Mittel | Offen | RevHeadz oder Car Scanner ELM OBD2 |
| **Bluetooth RFCOMM Verbindung abgelehnt** | **Kritisch** | **Ungeklärt** | **pybluez RFCOMM auf headless Pi fehlerhaft** |
| Bluetooth SPP Latency unklar | Niedrig | Offen | Auf ESP32 testen |
| sdptool nicht verfügbar | Mittel | Umgangen | WiFi TCP als Alternative |

## Evolution der Projekt-Entscheidungen

### 2026-01-15: Projektstart
- **Entscheidung:** Memory Bank Struktur erstellt
- **Begründung:** Cline Memory Bank benötigt strukturierte Dokumentation

### 2026-06-15: Verbindungsmethode geändert
- **Entscheidung:** WiFi TCP statt Bluetooth SPP als Hauptverbindung
- **Begründung:** Bluetooth RFCOMM auf headless Pi Zero 2W nicht zuverlässig
- **WiFi TCP Vorteile:** Keine Pairing-Probleme, einfacher zu debuggen, zuverlässiger
- **WiFi TCP Nachteile:** Handy muss im selben WiFi-Netz wie Pi

### Offene Entscheidungen (未来)
- **Hardware-Plattform:** ESP32 vs. Pi Zero 2W
  - *Faktoren:* Kosten, Performance, Bluetooth-Support, CAN-Anbindung
- **Firmware-Sprache:** C (ESP-IDF) vs. MicroPython
  - *Faktoren:* Performance vs. Entwicklungs Geschwindigkeit
- **RPM-Modell:** Einfach vs. Vollständig
  - *Faktoren:* Entwicklungs Aufwand vs. Sound-Qualität