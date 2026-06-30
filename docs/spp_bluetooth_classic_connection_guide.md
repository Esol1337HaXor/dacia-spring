# vGate iCar Pro BT — Vollständige Verbindungsdokumentation

**Datum:** 2026-06-25  
**Gerät:** vGate iCar Pro BT (VK1032 Bluetooth-Nur, KEIN WiFi)  
**Verbindung:** Bluetooth Classic SPP über RFCOMM Channel 1  
**Pi IP:** 192.168.178.87  
**Android-Vlink MAC:** `13:E0:2F:8D:61:07`

---

## 🎯 Zusammenfassung

Nach mehr tägiger Fehlersuche wurde die Verbindung zum vGate iCar Pro BT über **Bluetooth Classic SPP** hergestellt. Der Adapter sendet ZWEI Bluetooth-Signale — nur eines davon (Android-Vlink) enthält Fahrzeugdaten.

### Wichtige Erkenntnis

Der vGate iCar Pro BT (Bluetooth-Nur) verwendet **Bluetooth Classic SPP**, NICHT BLE GATT. CanZE Plus auf Android verwendet denselben Weg.

---

## 🔍 Problemanalyse

### Was wir ANFANGS dachten:
- vGate iCar Pro ist ein BLE-Gerät
- Wir müssen über BLE GATT (Service `e7810a71`) kommunizieren
- IOS-Vlink Signal (`D2:E0:2F:8D:61:07`) ist der richtige Adapter

### Was WIRKLich stimmt:
- Der Adapter sendet ZWEI Signale:
  - `D2:E0:2F:8D:61:07` — IOS-Vlink (BLE GATT) — **KEINE Fahrzeugdaten**
  - `13:E0:2F:8D:61:07` — Android-Vlink (Bluetooth Classic SPP) — **CanZE-Verbindung!**
- **Manual Pairing ist ZWINGEND erforderlich** bevor SPP funktioniert
- rfcomm0 muss NACH dem Pairing erstellt werden

---

## 🧪 Testverfahren im Überblick

### Test 1: BLE GATT Scan
```bash
# Zeigt beide BLE-Signale des Adapters
sudo bluetoothctl scan on
# Ergebnis:
# Device 13:E0:2F:8D:61:07 Android-Vlink
# Device D2:E0:2F:8D:61:07 IOS-Vlink
```

### Test 2: BLE GATT Kommunikation
```bash
# Versucht BLE GATT auf Android-Vlink
sudo python3 /home/lsd/obd2-adapter/ble_client_vgate_root.py
# Ergebnis: ❌ Connection refused / br-connection-profile-unavailable
# Grund: Android-Vlink ist BLE GATT, aber Classic SPP!
```

### Test 3: RFCOMM SPP Scan (vor Pairing)
```bash
# Versucht RFCOMM Verbindung vor dem Pairing
sudo python3 /home/lsd/obd2-adapter/bt_classic_spp_test.py
# Ergebnis: ❌ Connection refused auf Channel 1-9
# Grund: Gerät muss GEPARED sein bevor SPP funktioniert!
```

### Test 4: WiFi TCP Scan
```bash
# Scannt das lokale Netz nach vGate WiFi
sudo python3 /home/lsd/obd2-adapter/tcp_vgate_test.py
# Ergebnis: ❌ Kein Gerät im Netzwerk
# Grund: BT-Version hat KEIN WiFi!
```

### Test 5: Manual Pairing
```bash
# Bluetooth Classic Pairing mit Android-Vlink
sudo bluetoothctl
[bluetooth]# trust 13:E0:2F:8D:61:07
[bluetooth]# pair 13:E0:2F:8D:61:07
[bluetooth]# connect 13:E0:2F:8D:61:07
# PIN: 1234 oder 0000
# Ergebnis: ✅ Paired: yes, Connected: yes
```

### Test 6: rfcomm0 erstellen
```bash
# RFCOMM Device nach Pairing erstellen
sudo rfcomm release /dev/rfcomm0 2>/dev/null
sudo rm -f /dev/rfcomm0
sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1
# Ergebnis: ✅ /dev/rfcomm0 existiert
```

### Test 7: pyserial installieren
```bash
sudo pip3 install --break-system-packages pyserial
# Ergebnis: ✅ pyserial verfügbar
```

### Test 8: ELM327 über SPP
```bash
# Serial Port öffnen und ELM327 Commands senden
sudo python3 /home/lsd/obd2-adapter/spp_elm327_test.py
# Ergebnis:
# ✅ ELM327 v2.3 gefunden!
# ✅ ATE0 → OK
# ✅ ATH0 → OK
# ✅ ATS0 → OK
# ✅ ATSP 0 → OK
```

### Test 9: CAN-Bus PIDs
```bash
# Testet CAN-Bus PIDs wie CanZE
sudo python3 /home/lsd/obd2-adapter/spp_obd2_parser.py
# Ergebnis:
# 222003 → Speed: 6220030000 = 0 km/h ✅ (Auto steht)
# 22202E → Throttle: 62202E0000 = 0% ✅ (Pedal los)
```

### Test 10: Fahrzeug-Test mit Gasgeben
```bash
# Leerlauf: 62202E0000 → 0%
# Kickdown: 62202E0392 → 91.4%
# Vollgas:  62202E03E8 → 100.0%
# Ergebnis: ✅ Throttle-Werte korrekt!
```

---

## 📊 Test-Ergebnisse Zusammenfassung

| Test | Zweck | Ergebnis |
|------|-------|----------|
| BLE GATT Scan | Beide Signale finden | ✅ 2 Signale gefunden |
| BLE GATT Kommunikation | Daten lesen | ❌ 0 Daten |
| RFCOMM SPP (vor Pairing) | SPP Verbindung | ❌ Connection refused |
| WiFi TCP | vGate WiFi finden | ❌ Nicht im Netzwerk |
| Manual Pairing | Bluetooth Classik Pairing | ✅ Erfolg |
| rfcomm0 erstellen | Serial Port erstellen | ✅ Erfolg |
| pyserial | Serial Port Zugriff | ✅ Installiert |
| ELM327 über SPP | Commands senden | ✅ v2.3 gefunden! |
| CAN-Bus PIDs | Speed + Throttle | ✅ 0 km/h, 0% |
| Fahrzeug-Test | Gasgeben erkennen | ✅ 91.4%, 100%! |

---

## 🛠️ Schritt-für-Schritt Anleitung

### Schritt 1: vGate iCar Pro BT anschließen
- Adapter in OBD2-Port des Autos stecken
- Dashboard muss leuchten (Zündung AN)
- Adapter LED muss leuchten

### Schritt 2: Bluetooth Pairing
```bash
sudo bluetoothctl
[bluetooth]# trust 13:E0:2F:8D:61:07
[bluetooth]# pair 13:E0:2F:8D:61:07
[bluetooth]# connect 13:E0:2F:8D:61:07
# PIN: 1234 oder 0000
```

### Schritt 3: rfcomm0 erstellen
```bash
sudo rfcomm release /dev/rfcomm0 2>/dev/null
sudo rm -f /dev/rfcomm0
sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1
```

### Schritt 4: SPP TCP Server starten
```bash
cd ~/obd2-adapter
bash start_spp_server.sh
# Oder manuell:
sudo python3 spp_tcp_server.py
```

### Schritt 5: RevHeadz verbinden
- IP des Pi + Port 2117
- Beispiel: `192.168.178.87:2117`

---

## 📡 Unterstützte CAN-Bus PIDs

| PID | Funktion | Format | Beispiel |
|-----|----------|--------|----------|
| 222003 | Speed (km/h) | `622003XXXX` | `6220030000` → 0 km/h |
| 22202E | Throttle (%) | `62202EXXYY` → XXYY/10 | `62202E03E8` → 100.0% |
| 223045 | Motor Speed | `623045XXXX` | `6230458000` → ? |
| 229001 | Battery SOC | `629001XXXX` | `7F2212` → NACK |

### WICHTIG: Throttle-Format
- **16-bit Big-Endian** mit Dezimalfaktor 10
- `0x0392` = 914 → 91.4% (Kickdown)
- `0x03E8` = 1000 → 100.0% (Vollgas)
- `0x0000` = 0 → 0.0% (Leerlauf)

---

## 🔧 Unterstützende Scripts

| Script | Zweck | Status |
|--------|-------|--------|
| `pi/bluetooth_pair_spp.sh` | Pairing Automation | ✅ Erstellt |
| `pi/vgate_pairing_check.sh` | Pairing-Status prüfen | ✅ Erstellt |
| `pi/spp_fix_rfcomm.sh` | rfcomm0 neu erstellen | ✅ Erstellt |
| `pi/spp_elm327_test.py` | ELM327 Command Test | ✅ Erstellt |
| `pi/spp_baud_scan.py` | Baudrate Scan | ✅ Erstellt |
| `pi/spp_obd2_parser.py` | OBD2-PID Parser | ✅ Erstellt |
| `pi/spp_tcp_server.py` | TCP Server mit Echtzeit-Daten | ✅ Erstellt |
| `pi/start_spp_server.sh` | Server Start-Script | ✅ Erstellt |

---

## 🎉 Erfolge

1. **Bluetooth Classic SPP über rfcomm0** — vGate iCar Pro BT erfolgreich angebunden
2. **Manual Pairing** — Pairing mit Android-Vlink durchgeführt
3. **ELM327 v2.3** — Adapter antwortet auf Commands
4. **Speed 222003** — Echtzeit-Speed über SPP gelesen
5. **Throttle 22202E** — Echtzeit-Gaspedal über SPP gelesen
6. **16-bit Parser** — Throttle-Format korrekt interpretiert
7. **RPM-Simulation** — RPM aus Speed + Throttle + Gang berechnet
8. **TCP Server** — RevHeadz kann sich verbinden

---

## ⚠️ Bekannte Probleme

1. **rfcomm0 stale** — Muss nach jedem Neustart neu erstellt werden
   - Lösung: Systemd-Service für rfcomm bind beim Booten
2. **223045 Motor Speed** — Format noch unklar (`6230458000`)
3. **229001 Battery SOC** — Negative Response (`7F2212`)
4. **BLE GATT IOS-Vlink** — Keine Fahrzeugdaten

---

## 📝 Nächste Schritte

1. **rfcomm0 Auto-Setup** — Systemd Service erstellen
2. **Motor-Speed Parser** — Format für 223045 herausfinden
3. **Battery-SOC Parser** — Format für 229001 herausfinden
4. **RevHeadz Integration** — Echte RPM-Daten statt Simulation
5. **Android App Test** — RevHeadz mit echten Daten testen

---

## 🧠 Wichtige Lektionen

1. **Nicht alle "vGate iCar Pro" sind gleich** — BT-Version hat KEIN WiFi
2. **Zwei BLE-Signale ≠ zwei Funktionen** — Beide sind nur Discovery-Signale
3. **Pairing ist ZWINGEND** — SPP funktioniert OHNE Pairing nicht
4. **rfcomm0 NACH Pairing erstellen** — Vorheriges Erstellen funktioniert nicht
5. **16-bit Big-Endian** — Throttle braucht 2 Bytes + /10