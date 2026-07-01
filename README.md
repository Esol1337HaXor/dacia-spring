# Dacia Spring OBD2 Adapter

![Status](https://img.shields.io/badge/Status-Working-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%20Zero%202W-blue)
![License](https://img.shields.io/badge/License-MIT-blue)

Ein System, das einen **Raspberry Pi Zero 2 W** als **ELM327 OBD2-Adapter** ausgeben lässt, um Android-Motorsound-Apps wie **RevHeadz** im **Dacia Spring** (und anderen E-Fahrzeugen) zu betreiben.

Stecker rein — Auto starten — App verbinden — Sound ab. Mehr gibt's nicht zu tun.

---

## 🎯 Kurzfassung

| Frage | Antwort |
|-------|---------|
| **Was macht das System?** | Emuliert einen ELM327 OBD2-Adapter für Motorsound-Apps in E-Autos |
| **Welche Apps funktionieren?** | RevHeadz, Car Scanner, Potenza Drive und alle ELM327-kompatiblen Apps |
| **Wie verbindet man es?** | WiFi TCP — IP und Port werden automatisch konfiguriert |
| **Woher kommen die Daten?** | Zwei Modi: Simulation oder echte CAN-Daten vom vGate iCar Pro BT |
| **Braucht man Pairing?** | Nur bei Modus B mit vGate Adapter (einmalig) |
| **Was funktioniert NICHT?** | WiFi Access Point (nur Client-Modus, kein Hotspot) |

---

## 📡 Zwei Modi, gleiche Ergebnis

### Modus A: Simulation (keine Hardware nötig)

Der Pi generiert realistische RPM-Werte selbst. Funktioniert sofort nach der Installation — kein zusätzlicher Adapter erforderlich.

- **RPM:** 850 Leerlauf, ±20 Jitter (natürliches Schwanken)
- **Alle PIDs verfügbar:** Status, Engine Load, Coolant Temp, RPM, Speed
- **Plug-and-Play:** systemd Service startet automatisch beim Booten

### Modus B: Echte Fahrzeugdaten (vGate iCar Pro BT erforderlich)

Der Pi liest echte CAN-Bus-Daten vom Auto über einen vGate iCar Pro BT Adapter und bereitet sie für die App auf.

- **Speed:** Echt vom CAN-Bus (PID 222003)
- **Throttle:** Echt vom Gaspedal (PID 22202E, 0–100 %)
- **RPM:** Basierend auf Speed + Throttle berechnet (realistische Beschleunigung/Bremsen)
- **Funktioniert mit Gasgeben:** 0 % Leerlauf → 91 % Kickdown → 100 % Vollgas

**Welchen Modus sollte ich wählen?**
Modus A ist einfacher einzurichten. Modus B klingt realistischer, weil er echte Fahrzeugdaten verwendet — aber Modus A klingt ebenfalls gut, weil die RPM-Simulation natürlich jittert. Beide funktionieren gleichermaßen mit RevHeadz.

---

## 🔌 So funktioniert es

```
Modus A (Simulation):
  Pi → simulierte RPM → WiFi TCP → RevHeadz → Motorsound

Modus B (Echte Daten):
  Auto OBD2 Port → vGate iCar Pro BT → CAN-Bus Daten →
  Pi berechnet RPM daraus → WiFi TCP → RevHeadz → Motorsound
```

In beiden Moden verbindet sich die Android-App gleich: WiFi TCP auf Port 2117.

---

## 🚀 Installation

### 1. Pi vorbereiten

- Raspberry Pi Zero 2 W mit Raspberry Pi OS Trixie
- WiFi mit dem gleichen Netzwerk wie das Android-Gerät

### 2. Repository klonen

```bash
git clone https://github.com/Esol1337HaXor/dacia-spring.git
cd dacia-spring/pi
```

### 3. Server installieren

#### Für Modus A (Simulation):

```bash
sudo cp elm327-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now elm327-server
```

Fertig. Der Server startet automatisch mit dem Pi.

#### Für Modus B (Echte Daten mit vGate iCar Pro BT):

```bash
# Adapter einstecken, Pairing einmalig:
sudo bluetoothctl
[bluetooth]# trust 13:E0:2F:8D:61:07
[bluetooth]# pair 13:E0:2F:8D:61:07

# RFCOMM Device erstellen:
sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1

# Service installieren:
sudo cp spp-elm327-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spp-elm327-server
```

**Hinweis:** Nach jedem Neustart muss `rfcomm bind` wiederholt werden — dafür gibt es ein Setup-Script: `setup_spp_service.sh`.

---

## 📱 App verbinden

### RevHeadz

1. Verbindungstyp: **WiFi OBD2 Adapter**
2. IP: Pi-Adresse ermitteln (`hostname -I` auf dem Pi, typisch `192.168.178.87`)
3. Port: `2117`
4. Verbinden klicken — fertig

### Car Scanner ELM OBD2

1. Verbindung: **WiFi / TCP**
2. Device: Manuelles Device
3. IP: Pi-Adresse
4. Port: `2117`
5. Protokoll: ELM327

### Pi-Adresse ermitteln

```bash
hostname -I
# Typische Ausgabe: 192.168.178.87
```

---

## ✅ Funktionsstatus

| Komponente | Status |
|------------|--------|
| ELM327 Emulation über WiFi TCP | ✅ Funktioniert |
| RevHeadz Verbindung | ✅ Funktioniert |
| Command Normalisierung | ✅ Funktioniert |
| RPM (Simulation oder echt) | ✅ Funktioniert |
| Speed ( Simulation oder echt) | ✅ Funktioniert |
| Throttle (Modus B) | ✅ Funktioniert |
| AlleSupported PIDs | ✅ Funktioniert |
| AT Commands (ATZ, ATE0, ATH0, etc.) | ✅ Funktioniert |
| systemd Auto-Start | ✅ Funktioniert |
| Bluetooth SPP zu vGate Adapter | ✅ Funktioniert |
| BLE GATT zu vGate WiFi Adapter | ✅ Funktioniert |
| BLE GATT zu IOS-VLink Adapter | ✅ Funktioniert |
| WiFi Access Point (Hotspot) | ❌ Nicht implementiert — Pi funktioniert nur als WiFi-Client |

**Zusammengefasst:** Das System funktioniert in beiden Modi vollumfänglich. Einziger Punkt, der nicht exists: der Pi kann keinen eigenen WiFi-Hotspot aufsetzen. Für den typischen Einsatz (Pi im gleichen Heimnetz wie Handy, oder im Auto mit Mobilhotspot) ist das kein Problem.

---

## 🔧 Server verwalten

```bash
# Status prüfen
sudo systemctl status elm327-server      # Modus A
sudo systemctl status spp-elm327-server  # Modus B

# Neustarten
sudo systemctl restart elm327-server

# Logs
sudo journalctl -u elm327-server -f
tail -f /home/lsd/obd2-adapter/server.log
```

### RPM-Werte anpassen

In `elm327_tcp_server_standalone.py`:

```python
idle_rpm = 850    # Leerlauf ändern
jitter_range = 20 # Mehr/weniger Jitter
```

---

## 🛠️ Probleme lösen

### App verbindet sich nicht

```bash
# Läuft der Server?
pgrep -a python3 | grep elm327

# Ist Port offen?
ss -tlnp | grep 2117

# Gleiches WiFi?
hostname -I  # Pi-Adresse mit der des Handys vergleichen
```

### "Timeout waiting for response"

Alle Antworten enden mit dem ELM327-Prompt `> `. Falls dies fehlt, ist die Server-Version veraltet — bitte die neueste Version clonen.

### vGate Adapter verbindet sich nicht

```bash
# Pairing-Status prüfen
sudo bluetoothctl info 13:E0:2F:8D:61:07

# RFCOMM neu erstellen
sudo rfcomm release /dev/rfcomm0 2>/dev/null
sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1
```

---

## 📁 Dateien

```
pi/
├── elm327_tcp_server_standalone.py  # Modus A: Simulation
├── spp_tcp_server.py                 # Modus B: Echte CAN-Daten
├── elm327-server.service             # systemd Service (Modus A)
├── spp-elm327-server.service         # systemd Service (Modus B)
├── rpm_simulation_engine.py          # RPM-Berechnung
└── setup_spp_service.sh              # RFCOMM Auto-Setup (Modus B)
```

---

## 📚 Tiefe Dokumentation

| Dokument | Inhalt |
|----------|--------|
| [Systemarchitektur](docs/pi_system_architecture.md) | Alle Dienste, Command-Flows, Debugging |
| [Bluetooth SPP Guide](docs/spp_bluetooth_classic_connection_guide.md) | vGate iCar Pro BT Einrichtung |
| [Master Plan](docs/master_plan.md) | Langfristige Planung |
| [ELM327 Befehle](docs/elm327_commands.md) | Komplette Befehlsreferenz |
| [OBD2 PIDs](docs/obd2_pid_reference.md) | Alle PIDs und Formeln |
| [BLE GATT Analyse](docs/ble_gatt_ios_vlink_analysis.md) | BLE Adapter Dokumentation |

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