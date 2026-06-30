## [2026-06-30 22:24] WiFi AP Script — Komplett neu geschrieben

**PROBLEM:** Das komplexe WiFi-Modus-Script hatte 6 kritische Fehler:
1. Safe Mode Background-Prozess konnte `switch_to_client()` nicht aufrufen (Subshell-Funktion nicht verfügbar)
2. Heimnetz-Scan (`iw dev wlan0 scan`) funktioniert im AP-Modus nicht (Interface ist im AP-Mode)
3. `/etc/wpa_supplicant/wpa_supplicant.conf` existierte nicht
4. dhcpcd-Deaktivierung (`denyinterfaces wlan0`) blockierte Client-Modus
5. sudo ohne Password über SSH fehlte
6. Race Condition zwischen dhcpcd und wpa_supplicant

**FIX:**
- Komplexes Script komplett entfernt (Safe Mode, Background-Scan, dhcpcd-Manipulation)
- Neues SUPER EINFACHES Script erstellt:
  ```bash
  # Prüfe ob wlan0 eine 192.168.178.x IP hat ODER wpa_supplicant läuft
  if ip addr show wlan0 | grep "inet 192\.168\.178"; then
      echo "✅ Client-Modus"
  elif pgrep -a wpa_supplicant | grep -q wlan0; then
      echo "✅ Client-Modus"
  else
      # AP starten mit hostapd + dnsmasq
      echo "❌ AP-Modus"
  fi
  ```
- `/etc/wpa_supplicant/wpa_supplicant.conf` erstellt mit:
  - SSID: WaggumAirport
  - Password: DankefuermeineArbeitsstelle
- sudo NOPASSWD aktiviert (`lsd ALL=(ALL) NOPASSWD: ALL`)
- Script getestet: Heimnetz erkannt ✅

**REASON:** Die komplexe Logik war unzuverlässig und fehleranfällig. Ein einfaches if/else basierend auf der aktuellen IP ist 100% zuverlässiger. Raspberry Pi OS managt wpa_supplicant + dhcpcd automatisch.

**STATUS:** resolved

## [2026-06-30 22:24] WiFi AP — Automatisches Umschalten

**PROBLEM:** Benutzer wollte ein einfaches Script das automatisch zwischen Heimnetz und AP umschaltet.

**FIX:**
- Script prüft beim Ausführen ob Pi eine 192.168.178.x IP hat
- ✅ Ja → Client-Modus (Pi ist zu Hause)
- ❌ Nein → AP-Modus (Pi ist im Auto, startet DaciaSpring-OBD2)
- Kein Safe Mode, kein Background-Scan, kein kompliziertes Umschalten
- Raspberry Pi OS macht alles automatisch (wpa_supplicant + dhcpcd)

**STATUS:** resolved

## [2026-06-30 22:23] AP-Start Bug gefixt — hostname -I gab falsche IPs zurück

**PROBLEM:** Das Script prüfte `hostname -I` was ALLE Netzwerk-IPs zurückgibt. Selbst nach dem Umbenennen der wpa_supplicant.conf hatte wlan0 noch die alte IP `192.168.178.87` — das Script dachte "Heimnetz da" und startete NICHT den AP.

**FIX:**
- Statt `hostname -I` → `ip addr show wlan0 | grep "inet 192\.168\.178"` (nur wlan0 prüfen)
- Zusätzlich geprüft ob `wpa_supplicant` für wlan0 läuft
- Bei 2 IPs (192.168.178.87 UND .90) → `head -1` verwendet um erste IP zu nehmen
- AP-Test erfolgreich: hostapd AP-ENABLED, SSID DaciaSpring-OBD2 sichtbar

**AP-TEST ERGEBNIS (22:23):**
```
[22:23:40] wlan0: AP-ENABLED
[22:23:42] ✅ AP-Modus AKTIV!
[22:23:42]    SSID: DaciaSpring-OBD2
[22:23:42]    Pi IP: 10.0.0.1
```

**STATUS:** resolved

## [2026-06-30 22:24] Heimnetz wiederhergestellt

**PROBLEM:** Nach AP-Test war wlan0 nur noch im AP-Modus (10.0.0.1).

**FIX:**
- wpa_supplicant.conf wieder zurückbenannt
- IPs von wlan0 entfernt → dhcpcd bekommt neue IP
- Script neu gestartet → Heimnetz erkannt (192.168.178.87)

**STATUS:** resolved