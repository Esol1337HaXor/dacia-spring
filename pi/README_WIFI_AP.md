# WiFi AP Modus — Dacia Spring OBD2 Adapter

## Überblick

Dieses Dokument beschreibt die WiFi AP (Access Point) Funktionalität des Pi Zero 2W. Der Pi kann zwischen zwei Modi wechseln:

| Modus | Verwendung | Pi IP | Beschreibung |
|-------|-----------|-------|-------------|
| **Client-Modus** | Zu Hause | 192.168.178.87 | Pi verbindet sich mit Heimnetz-WiFi |
| **AP-Modus** | Im Auto | 10.0.0.1 | Pi wird zum Hotspot |

---

## Warum dieser Modus?

### Problem:
Der Pi ist aktuell über WiFi mit dem Heimnetz verbunden (192.168.178.87). Wenn du im Auto bist, gibt es kein Heimnetz — die Verbindung bricht ab!

### Lösung:
Der Pi kann als **eigener Hotspot** fungieren. Im Auto startet er automatisch den AP-Modus, und dein Handy verbindet sich direkt mit dem Pi!

---

## Auto-Boot Verhalten

### Beim Pi-Start:

```
Pi bootet
  ↓
Startet als WiFi Client (wpa_supplicant)
  ↓
Wartet 15s auf Heimnetz-Verbindung
  ↓
┌──────────────┬───────────────┐
│ Heimnetz DA  │ Heimnetz NEIN │
│ (192.168.    │ (kein Router  │
│  178.x)     │  erreichbar)  │
↓              ↓
Bleibt       Switch zu
Client-Modus AP-Modus
(192.168.    (10.0.0.1)
 178.87)
```

**Das bedeutet:**
- **Zu Hause:** Pi verbindet sich automatisch mit Heimnetz → SSH von überall möglich
- **Im Auto:** Kein Heimnetz → Pi wird automatisch zum Hotspot

---

## Manuelles Umschalten

### Umschalt-Script:
```bash
# Standort: /home/lsd/obd2-adapter/wifi_mode_switch.sh
```

### Befehle:

```bash
# AP-Modus (Auto) — Pi wird zum Hotspot
sudo /home/lsd/obd2-adapter/wifi_mode_switch.sh car

# Client-Modus (Heimnetz) — Pi verbindet sich mit Zuhause
sudo /home/lsd/obd2-adapter/wifi_mode_switch.sh home

# Auto-Detect — Startet als Client, switch zu AP wenn kein Heimnetz
sudo /home/lsd/obd2-adapter/wifi_mode_switch.sh auto

# Status prüfen
sudo /home/lsd/obd2-adapter/wifi_mode_switch.sh status
```

---

## Hotspot-Parameter

| Parameter | Wert |
|-----------|------|
| **SSID** | `DaciaSpring-OBD2` |
| **Password** | `obd2spring2026` |
| **Pi IP (AP)** | `10.0.0.1` |
| **Channel** | 6 (2.4 GHz) |
| **DHCP Range** | 10.0.0.100 - 10.0.0.200 |
| **Max Clients** | 10 |
| **Verschlüsselung** | WPA2-PSK |

---

## Verbindungsherstellung

### Handy mit Pi verbinden (AP-Modus):

1. **WiFi-Einstellungen am Handy öffnen**
2. **Netzwerk wählen:** `DaciaSpring-OBD2`
3. **Password eingeben:** `obd2spring2026`
4. **Verbinden**

### Danach:

| Zugriff | URL/Adresse |
|---------|-------------|
| **SSH** | `ssh lsd@10.0.0.1` |
| **RevHeadz** | `10.0.0.1:2117` (Typ: WiFi OBD2) |
| **Pi Dateisystem** | `/home/lsd/obd2-adapter/` |

---

## Installation

### hostapd + dnsmasq installieren:

```bash
# 1. Setup-Script auf Pi kopieren
scp setup_wifi_ap.sh lsd@192.168.178.87:/home/lsd/obd2-adapter/

# 2. SSH zum Pi
ssh lsd@192.168.178.87

# 3. Setup ausführen (braucht sudo!)
cd /home/lsd/obd2-adapter
sudo bash setup_wifi_ap.sh

# 4. Pi neustarten
sudo reboot
```

### Nach der Installation:

```bash
# Service aktivieren
sudo systemctl enable wifi-auto-boot

# Status prüfen
sudo systemctl status wifi-auto-boot

# Logs ansehen
sudo journalctl -u wifi-auto-boot -n 50
```

---

## Dateien-Übersicht

| Datei | Zweck |
|-------|-------|
| `pi/wifi_mode_switch.sh` | Umschalt-Script (car/home/auto/status) |
| `pi/setup_wifi_ap.sh` | Installiert hostapd + dnsmasq |
| `pi/wifi-auto-boot.service` | Systemd Service für Auto-Boot |
| `docs/README_WIFI_AP.md` | Dieses Dokument |

---

## Konfigurations-Dateien

### hostapd Config:
```
/etc/hostapd/hostapd.conf
```
- SSID, Password, Channel konfiguriert
- WPA2 Verschlüsselung aktiv

### dnsmasq Config:
```
/etc/dnsmasq.conf
```
- DHCP Range: 10.0.0.100-200
- DNS: Pi selbst (10.0.0.1)

### wpa_supplicant Config:
```
/etc/wpa_supplicant/wpa_supplicant.conf
```
- Heimnetz SSID + Password
- Wird für Client-Modus verwendet

---

## Troubleshooting

### Problem: AP startet nicht

```bash
# hostapd Logs prüfen
sudo journalctl -u hostapd -n 50

# Config testen
sudo hostapd -d /etc/hostapd/hostapd.conf

# Manuell starten
sudo hostapd -B /etc/hostapd/hostapd.conf
```

### Problem: Handy verbindet sich nicht

```bash
# SSID prüfen
sudo iw dev wlan0 scan | grep DaciaSpring

# Channel prüfen
sudo iwinfo wlan0 channel

# Password prüfen
sudo grep wpa_passphrase /etc/hostapd/hostapd.conf
```

### Problem: Kein Internet im AP-Modus

**Das ist normal!** Im AP-Modus hat der Pi KEIN Internet (außer Heimnetz ist da).
Das ist kein Fehler — RevHeadz braucht kein Internet!

### Problem: Pi ist nach Neustart unerreichbar

```bash
# Auto-Detect erzwingen
sudo wifi_mode_switch.sh car  # ← Wenn du im Auto bist
# ODER
sudo wifi_mode_switch.sh home # ← Wenn du zu Hause bist
```

---

## WiFi-Reichweite optimieren (optional)

### Externe WiFi-Antenne:
- Pi Zero 2W hat einen **U.FL Anschluss** für externe Antenne
- Reichweite: 10m (intern) → 50m+ (extern)
- Kosten: ~5-10€

### Empfohlene Antenne:
- **2.4 GHz WiFi Antenne mit U.FL Stecker**
- Oder: **Magnetische External Antenne**

---

## Sicherheits-Hinweise

### WPA2 Password:
- Standard: `obd2spring2026`
- **Empfohlen:** Eigener Password in `/etc/hostapd/hostapd.conf` ändern!

### Max Clients:
- Standard: 10 (reicht für Auto-Nutzung)
- Kann reduziert werden auf z.B. 2 in `/etc/hostapd/hostapd.conf`

### Firewall:
- Im AP-Modus ist der Pi nur vom verbundenen Handy erreichbar
- Port 2117 (RevHeadz) und Port 22 (SSH) sind offen
- Kein Internet-Forwarding aktiv (sicher!)

---

## Zusammenfassung

### Vorteile vom AP-Modus:
✅ **ÜBERALL verfügbar** — Nicht an Heimnetz gebunden
✅ **Stabile IP** — Immer 10.0.0.1 im AP-Modus
✅ **Auto-Boot** — Pi erkennt automatisch Heimnetz vs. Auto
✅ **Sicher** — Nur autorisierte Geräte (Password-Schutz)
✅ **Kein Internet nötig** — RevHeadz funktioniert lokal

### Nachteile:
⚠️ **Kein Internet auf Pi** (wenn nur AP-Modus)
⚠️ **WiFi-Reichweite** (Pi Zero 2W intern ~10m)
⚠️ **Umschalten nötig** (kann aber automatisch!)

---

## Nächste Schritte

1. **Setup ausführen:** `sudo bash setup_wifi_ap.sh`
2. **Pi neustarten:** `sudo reboot`
3. **Auto-Boot testen:** Pi Strom weg → an → Status prüfen
4. **Manuell testen:** `wifi_mode_switch.sh car` → Handy verbinden
5. **RevHeadz testen:** `10.0.0.1:2117`

**Dann ist der Pi bereit für den Einsatz ÜBERALL — nicht nur zu Hause!** 🚗💨