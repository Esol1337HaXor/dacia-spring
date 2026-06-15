# Kontext: Aktuelle Arbeit

## Aktueller Fokus
**Phase:** Phase 3 - RevHeadz Verbindung erfolgreich! (Stand: 2026-06-16 01:43)

## Kürzlich durchgeführte Änderungen
- **REVHEADZ VERBINDUNG FUNKTIONIERT! ✅**
- **3 Ursachen identifiziert und gefixt:**
  1. Command Normalisierung: `AT Z` → `ATZ`, `01 0C` → `010C`
  2. Command Prompt `> ` nach jeder Antwort (ELM327 Standard)
  3. Supported PIDs korrigiert: `41 00 98 18 00 00` (PID 0C RPM + PID 0D Speed)
- **Standalone Server erstellt:** `pi/elm327_tcp_server_standalone.py` (keine Dependencies)
- **SSH Key Setup** für Passwortlosen Zugang zum Pi
- **Dokumentation erstellt:** `docs/revheadz_fix_protocol.md` (umfangreiches Protokoll)

## Kürzlich durchgeführte Änderungen
- Projektpitch analysiert und strukturiert
- Memory Bank Struktur erstellt
- Technische Kontextdokumentation initialisiert
- **PI ZERO 2W SETUP ABGESCHLOSSEN** - SSH Zugang, Python venv, python3-bluez installiert
- **Bluetooth SPP Server implementiert** - ELM327 OBD2 Emulation (rfcomm Channel 1)
- **WiFi TCP Server implementiert** - Alternative zu Bluetooth (Port 2117, IP 192.168.178.87)
- **Bluetooth Pairing-Tests mit Smartphone** - Partnerisierung fast erfolgreich, aber RFCOMM-Verbindung wird vom Pi abgelehnt

## Hardware-Status (AKTUALISIERT - 2026-06-15 23:00)

### Vorhandene Hardware
- ✅ **Raspberry Pi Zero 2 W** - Setup abgeschlossen, SSH-Zugang, Server laufen
- ✅ **Vgate iCar Pro Bluetooth 4.0 (BLE) OBD2** - OBD2-Adapter (noch nicht in Tests verwendet)
- ⚠️ **Smartphone (Android)** - Testgerät für Bluetooth/WiFi-Verbindung

### Pi Zero Zugang (AKTIV)
- **IP:** 192.168.178.87
- **Benutzer:** lsd
- **Passwort:** maxlose288
- **Sudo:** Aktiv (keine Passwortabfrage bei sudo Befehlen)
- **SSH:** Verfügbar

### Vgate iCar Pro Spezifikationen
- **Protokoll:** Bluetooth 4.0 BLE (Low Energy)
- **Chip:** ELM327 kompatibel
- **OBD2-Standard:** Unterstützt ISO 15765-4 (CAN 11/500) - Dacia Spring kompatibel
- **Android App Support:** Kann mit OBD2-Apps verbunden werden

## Zielkonfiguration (BESTÄTIGT)

### Datenfluss (FINAL)
```
OBD2-Port am Auto
    ↓
Vgate iCar Pro BLE (liest OBD2-Daten)
    ↓ BLE 4.0
Raspberry Pi Zero 2 W (liest + berechnet + emuliert)
    ↓ WiFi TCP (empfohlen) oder Bluetooth SPP
Android Phone (RevHeadz App)
```

### Aktuelle Verbindungsmethode (EMPFOHLEN: WiFi TCP)
- **WiFi TCP Server** läuft auf Pi (Port 2117)
- **Pi IP:** 192.168.178.87
- **Vorteil:** Keine Pairing-Probleme, zuverlässig
- **Nachteil:** Handy muss im selben WiFi-Netz sein

### Ziel-App
- **RevHeadz** - Motorsound-Simulation App
- **Anforderung:** RevHeadz erkennt Pi als OBD2-Adapter
- **Benötigte PIDs:** RPM (010C), Speed (010D)

## Offene Entscheidungen

### Hardware-Plattform ✅ ENTSCHEIDUNG
- [x] **Raspberry Pi Zero 2 W** - **BESCHAFFT** - Verwendung vorhanden
- [x] **Vgate iCar Pro BLE** - **BESCHAFFT** - OBD2-Adapter für Fahrzeugkommunikation

### Datenzugriff-Methode ✅ BESTÄTIGT
- [x] **Vgate iCar Pro BLE OBD2** - Liest OBD2-Daten vom Auto
- [x] **Pi emuliert ELM327** - Für Android Phone (RevHeadz)
- [x] **OBD2 PIDs:** Speed (010D) echt von Vgate, RPM (010C) simuliert vom Pi

### Firmware-Plattform
- [ ] **MicroPython** - Vorteile: Schnelle Iteration, einfach zu debuggen
- [ ] **ESP-IDF (C)** - Vorteile: Bessere Performance, vorhersagbare Echtzeit

### RPM-Simulationsansatz
- [ ] **Einfaches Mapping** - Speed + Throttle → RPM (Quick'n'Dirty)
- [ ] **Gangwechsel-Simulation** - Vollständiges Getriebemodell mit Shift Points

## Wichtige Muster und Präferenzen
- **Code-Stil:** Modular aufgebaut, jede Komponente als separater Modul
- **Dokumentation:** Alles wird in Memory Bank dokumentiert
- **Git:** Conventional Commits (`feat:`, `fix:`, `docs:`)
- **Open Source:** Ziel ist Veröffentlichung auf GitHub (Esol1337HaXor)

## Gelernte Erkenntnisse / Insights
- Der Dacia Spring verwendet CAN 2.0B mit 11-bit Identifiern
- CanZE Plus beweist dass CAN-Auslesen funktioniert
- ELM327-Emulation ist machbar - es gibt existierende Open-Source-Projekte
- Sound-Apps brauchen primär: RPM (0x0C) + Speed (0x0D)

## Relevantes Wissen
- OBD2 PID 0x0C (RPM) Formel: `RPM = (A*256 + B) / 4`
- OBD2 PID 0x0D (Speed) Formel: `Speed = A` (km/h)
- ELM327 Response Format für PID: `41 nn XX XX` (41 = response prefix)
- Bluetooth SPP auf ESP32 mit ESP-IDF v4.4+ verfügbar

## Blocker / Risiken

### Erfolge
- ✅ **ELM327 Emulation implementiert** - Sowie WiFi TCP Server
- ✅ **Pi Zero 2W Setup abgeschlossen** - SSH, Python, bluetooth, WiFi
- ✅ **WiFi TCP Server läuft** - Port 2117, IP 192.168.178.87

### Aktuelle Probleme
- ⚠️ **AKTUELL:** Bluetooth RFCOMM-Verbindung wird vom Pi abgelehnt (BlueZ RFCOMM-Filter)
  - Smartphone kann PiZeroCar-OBD2 finden und pairien (PIN: 1234)
  - Aber: Verbindungsaufbau wird vom Pi mit "Bluetooth error: timed out" abgelehnt
  - Fehler: pybluez `bluetooth.BluetoothSocket(bluetooth.RFCOMM)` akzeptiert keine Verbindungen
  - Versuchte Lösungen: sdptool (nicht installiert), bluetooth.advertise_service() (Parameter-Fehler)
- ⚠️ **AKTUELL:** Handy per WiFi TCP mit Pi verbinden (Alternative zu Bluetooth)
- ⚠️ **KRITISCH:** CAN-Bus Frame-Spezifikation des Dacia Spring unbekannt
- ⚠️ Kompatibilität mit verschiedenen Sound-Apps nicht garantiert

## Nächste Schritte
1. **RPM auf Throttle reagieren lassen** - Aktuelles Problem: immer 850 RPM
2. **Speed Simulation** - Wenn CAN-Daten vom Vgate iCar Pro verfügbar
3. **Optionale AT Commands** - AT ST, AT AL, AT L0 implementieren
4. **Bluetooth RFCOMM Problem** - Später analysieren (WiFi TCP funktioniert)

## Diskussionsthemen für nächstes Meeting
1. Hardware-Budget und Beschaffung
2. Priorität: Quick'n'Dirty PoC vs. qualitativ hochwertige Implementierung
3. Gibt es bereits CAN-Dokumentation für den Dacia Spring?
4. Welche Sound-App als erste Test-Plattform?