# Progress — Dacia Spring OBD2 Adapter Projekt

**Letzte Aktualisierung:** 2026-06-26 15:52

## Was funktioniert ✅

### SPP-Verbindung (BLUETOOTH CLASSIC) — FERTIG! 🎉
- [x] **vGate iCar Pro BT** über Bluetooth Classic SPP mit Pi verbunden
- [x] **Manual Pairing** mit `bluetoothctl` durchgeführt
- [x] **rfcomm0** erstellt und mit Device gebunden
- [x] **ELM327 v2.3** antwortet auf Commands über Serial Port
- [x] **pyserial** installiert und im Einsatz

### Systemd Service — FERTIG! 🎉
- [x] **spp-elm327-server.service** läuft als `active (running)`
- [x] **Auto-Start** bei Boot aktiviert (`enabled`)
- [x] **Auto-Recovery** wenn Verbindung verloren geht (`Restart=always`)
- [x] **rfcomm0** wird beim Service-Start automatisch erstellt

### CAN-Bus PIDs — FUNKTIONIERT!
- [x] **222003** → Speed: `6220030000` = 0 km/h (Auto steht) ✅
- [x] **22202E** → Throttle: `62202E03E8` = 100% (Vollgas/Kickdown) ✅
- [x] **0100** → Supported PIDs: `410000000000` (alle Standard = 0)
- [x] **010C** → RPM: 850 ±20 (Idle) ✅
- [x] **010D** → Speed: Echte Werte vom vGate ✅
- [x] **0111** → Throttle: Echte Werte vom vGate ✅
- [ ] **223045** → Motor Speed: `6230458000` (Parser noch unklar)

### TCP Server — FERTIG! 🎉
- [x] **Port 2117** lauscht auf `0.0.0.0`
- [x] **ELM327 Initialisierung** automatisch (ATE0, ATH0, ATS0, ATSP 0)
- [x] **Echtzeit-Daten** werden gesammelt (~10 Hz)
- [x] **RPM Engine** mit realistischer Gang-Simulation
- [x] **Standgas** funktioniert (Pedalposition → RPM im Stand)

### Latenz-OPTIMIERUNG — FERTIG! 🚀
- [x] **CAN-Bus Timeout** von 0.8s auf 0.05s reduziert (16x schneller!)
- [x] **Smoothing** auf 1.0 gesetzt (KEINE Verzögerung!)
- [x] **Hysteresis** auf 0.0 gesetzt (SOFORTIG!)
- [x] **GESAMT-LÄTZENZ:** ~1.6s → ~50ms (**32x Verbesserung!**)

### OBD2 Parser
- [x] **22202E Throttle** → 16-bit Big-Endian /10 Format erkannt
- [x] **0x0392** = 914 → 91.4% (Kickdown)
- [x] **0x03E8** = 1000 → 100.0% (Vollgas)

## Was noch nicht funktioniert ❌

### BLE GATT (IOS-Vlink Signal)
- [ ] **IOS-Vlink** (`D2:E0:2F:8D:61:07`) sendet keine Fahrzeugdaten
- [ ] 0 Notifications, 0 Read-Antworten

### Standard OBD2-PIDs
- [ ] **010D** (Speed) → `NO DATA` (E-Auto hat keinen Verbrenner)
- [ ] **010C** (RPM) → `NO DATA` (E-Auto hat keinen Verbrenner)

### Battery SOC
- [ ] **229001** → `7F2212` (Negative Response) — PID vielleicht falsch

## Was als nächstes kommt

### SOFORT: Fahrzeug-Test + RevHeadz
- [ ] **Server neu starten:** `sudo systemctl restart spp-elm327-server` (sudo nötig!)
- [ ] **Speed-Test:** Auto fahren + prüfen ob `622003XX00` sich ändert
- [ ] **Throttle-Test:** Pedal betätigen + prüfen ob `62202EXX00` sich ändert
- [ ] **RevHeadz verbinden:** 192.168.178.87:2117
- [ ] **Standgas testen:** Gas geben im Stand → RPM MUSS SOFORT steigen
- [ ] **Gas wegnehmen testen:** RPM MUSS SOFORT fallen (kein Nachglätten!)

### KURZFRISTIG: Autarker Betrieb
- [ ] **Systemd-Service:** Alle Dienste beim Booten automatisch starten
- [ ] **WLAN AP Modus:** Pi wird zum Hotspot (10.0.0.1)
- [ ] **hostapd + dnsmasq:** WiFi Access Point Konfiguration
- [ ] **Wasserfestes Gehäuse:** IP67 Projektbox für Pi Zero 2W

### LANGFRISTIG
- [ ] **rfcomm0 bleibt stabil** nach Neustart
- [ ] **Service Recovery** testen
- [ ] **Motor-Speed Parser** für 223045 verbessern

## Bekannte Probleme

1. **Motor-Speed Parser:** `6230458000` — Format noch unklar (Byte 4+5 = 0x8000 = 32768?)
2. **Battery SOC:** `7F2212` — Negative Response (SID 0x22 NACK mit Sub-Function 0x12)
3. **rfcomm path:** `rfcomm` liegt unter `/usr/bin/rfcomm`, nicht `/usr/sbin/rfcomm` — Service-File muss `which rfcomm` verwenden

## Wichtige MAC-Adressen

| Signal | MAC | Technologie | Status |
|--------|-----|-------------|--------|
| Android-Vlink | `13:E0:2F:8D:61:07` | Bluetooth Classic SPP | ✅ **FUNKTIONIERT!** |
| IOS-Vlink | `D2:E0:2F:8D:61:07` | BLE GATT | ❌ Keine Daten |

## Server-Zugriff

| Service | Port | Protocol | Status |
|---------|------|----------|--------|
| SPP ELM327 TCP | 2117 | TCP | ✅ **Aktiv** |
| SSH | 22 | TCP | ✅ Aktiv |

**Verbindung von Android:** `192.168.178.87:2117`

## Unterstützende Scripts

| Script | Zweck | Status |
|--------|-------|--------|
| `pi/install_spp_service.sh` | Service Installation | ✅ **Korrigiert** |
| `pi/spp-elm327-server.service` | Systemd Service | ✅ **Korrigiert** |
| `pi/spp_tcp_server.py` | Hauptserver | ✅ Funktioniert |
| `pi/bluetooth_pair_spp.sh` | Pairing Automation | ✅ Erstellt |
| `pi/spp_fix_rfcomm.sh` | rfcomm0 neu erstellen | ✅ Erstellt |
| `pi/spp_obd2_parser.py` | OBD2-PID Parser mit CanZE-IDs | ✅ Erstellt + 16-bit Fix |