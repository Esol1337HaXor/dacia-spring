# Active Context — Dacia Spring OBD2 Adapter

**Letzte Aktualisierung:** 2026-06-26 15:53

## 🎉 MEILENSTEIN 1: SPP-Service läuft als Systemd Service!

Am 2026-06-26 13:38 wurde der SPP ELM327 TCP Server als stabilen Systemd Service installiert und gestartet!

## 🚀 MEILENSTEIN 2: Latenz-OPTIMIERUNG — 32x Verbesserung!

Am 2026-06-26 15:52 wurden KRYTISCHE Latenz-Optimierungen durchgeführt:

### Zusammenfassung der heutigen Fixes

1. **rfcomm0 erstellt:**
   ```bash
   sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1
   ```
   - Device `13:E0:2F:8D:61:07` (Android-Vlink) ist gepaired, bonded, trusted
   - `/dev/rfcomm0` wurde mit Permissions `crw-rw---- 1 root dialout` erstellt

2. **Permissions korrigiert:**
   ```bash
   sudo chmod 755 /home/lsd/obd2-adapter  # Owner kann jetzt rein
   sudo usermod -aG dialout lsd            # User kann Serial Port nutzen
   ```

3. **Service-File korrigiert:**
   - `Type=forking` → `Type=simple` (Server läuft im Vordergrund)
   - `User=root` → `User=lsd`
   - Security restrictions entfernt (`ProtectSystem=no`, `ProtectHome=no`)
   - rfcomm bind mit `which rfcomm` für korrekten Pfad

4. **SPP Verbindung getestet:**
   ```
   Port opened: True
   AT -> OK
   Speed (222003) -> 6220030000 (0 km/h)
   Throttle (22202E) -> 62202E0000 (0%)
   ```

5. **Service läuft:**
   ```
   Active: active (running)
   TCP Port: 2117
   WiFi IP: 192.168.178.87
   Modus: ECHTE SPP-DATEN
   RPM Engine: Idle 850, Max 6500
   ```

### LATENZ-OPTIMIERUNGEN (15:52)

| Komponente | Vorher | Nachher | Faktor |
|------------|--------|---------|--------|
| CAN-Bus Timeout | 0.8s | 0.05s | **16x** |
| Smoothing | 0.3 (70% alt) | 1.0 (0% alt) | **Eliminiert** |
| Hysteresis | 0.5s | 0.0s | **Eliminiert** |
| **GESAMT-LÄTZENZ** | **~1.6s** | **~50ms** | **32x!** |

### STANDGAS-OPTIMIERUNG

- Pedalposition → RPM im Stand (Speed < 0.5 km/h)
- Formel: RPM = 850 + (Pedal * 24)
- Bei 25% Pedal: 1450 RPM
- Bei 50% Pedal: 2050 RPM
- Bei 100% Pedal: 3250 RPM
- Alpha = 1.0 = SOFORTIGE Reaktion!

### GANG-LOGIK-UPGRADE

- ALT: Speed-only (<5→1, <12→2, etc.)
- NEU: RPM-basiert (realistische Shift-Points)
- 6 Gänge basierend auf RPM + Speed
- WICHTIG: RevHeadz fragt KEINE Gang-PID ab!


### Zusammenfassung der heutigen Fixes

1. **rfcomm0 erstellt:**
   ```bash
   sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1
   ```
   - Device `13:E0:2F:8D:61:07` (Android-Vlink) ist gepaired, bonded, trusted
   - `/dev/rfcomm0` wurde mit Permissions `crw-rw---- 1 root dialout` erstellt

2. **Permissions korrigiert:**
   ```bash
   sudo chmod 755 /home/lsd/obd2-adapter  # Owner kann jetzt rein
   sudo usermod -aG dialout lsd            # User kann Serial Port nutzen
   ```

3. **Service-File korrigiert:**
   - `Type=forking` → `Type=simple` (Server läuft im Vordergrund)
   - `User=root` → `User=lsd`
   - Security restrictions entfernt (`ProtectSystem=no`, `ProtectHome=no`)
   - rfcomm bind mit `which rfcomm` für korrekten Pfad

4. **SPP Verbindung getestet:**
   ```
   Port opened: True
   AT -> OK
   Speed (222003) -> 6220030000 (0 km/h)
   Throttle (22202E) -> 62202E0000 (0%)
   ```

5. **Service läuft:**
   ```
   Active: active (running)
   TCP Port: 2117
   WiFi IP: 192.168.178.87
   Modus: ECHTE SPP-DATEN
   RPM Engine: Idle 850, Max 6500
   ```

### Service-File Änderungen im Detail

| Setting | Alt | Neu | Grund |
|---------|-----|-----|-------|
| `Type` | `forking` | `simple` | Server läuft im Vordergrund |
| `User` | `root` | `lsd` | Ordner gehört lsd |
| `ExecStartPre` | `rfcomm watch` mit Zombie-Prozessen | `rfcomm bind || true` | Keine Zombies |
| `ProtectSystem` | `strict` | `no` | Serial Port Zugriff |
| `ProtectHome` | `yes` | `no` | Zugriff auf /home/lsd |
| `TimeoutStartSec` | 90s (default) | 30s | Schnelleres Failure Detection |

### SOFORT: Server NEUSTARTEN! (ERFORDERLICH!)
- [ ] **SPP-Server neu starten:** `sudo systemctl restart spp-elm327-server` (sudo nötig!)
- [ ] **Status prüfen:** `sudo systemctl status spp-elm327-server --no-pager`
- [ ] **Log prüfen:** `tail -20 /home/lsd/obd2-adapter/server.log`

### REVHEADZ TEST (nach Neustart)
- [ ] Android App (RevHeadz) verbinden mit `192.168.178.87:2117`
- [ ] **Standgas testen:** Gas geben im Stand → RPM MUSS SOFORT steigen
- [ ] **Gas wegnehmen testen:** RPM MUSS SOFORT fallen (kein Nachglätten!)
- [ ] Prüfen ob Speed + Throttle Daten ankommen
- [ ] Motorsound bei Gasgeben testen

### FAHRZEUG-TEST
- [ ] Speed-Test: Auto fahren + prüfen ob Speed sich ändert
- [ ] Throttle-Test: Pedal betätigen + prüfen ob Throttle sich ändert
- [ ] Motor-Speed (223045) im echten Betrieb analysieren

### KURZFRISTIG: Autarker Betrieb
- [ ] Systemd-Service: Alle Dienste beim Booten automatisch starten
- [ ] WLAN AP Modus: Pi wird zum Hotspot (10.0.0.1)
- [ ] hostapd + dnsmasq: WiFi Access Point Konfiguration
- [ ] Wasserfestes Gehäuse: IP67 Projektbox für Pi Zero 2W

## Wichtige Patterns & Präferenzen

- **Bluetooth Classic SPP** über `/dev/rfcomm0` für vGate iCar Pro BT
- **rfcomm0 wird beim Booten automatisch erstellt** (Service ExecStartPre)
- **pyserial** für Serial Port Zugriff
- **CAN-Bus PIDs wie CanZE:** `222003`, `22202E`, `223045`
- **TCP Socket Port 2117** als RevHeadz Server
- **Service läuft als User `lsd`** mit `Restart=always`

## Server-Zugriff

| Service | Port | Protocol | Status |
|---------|------|----------|--------|
| SPP ELM327 TCP | 2117 | TCP | ✅ Aktiv |
| SSH | 22 | TCP | ✅ Aktiv |

**Verbindung von Android:** `192.168.178.87:2117`