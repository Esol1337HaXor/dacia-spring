# OBD2 BLE Verbindung - Technische Dokumentation

**Erstellt:** 2026-06-24
**Letzte Aktualisierung:** 2026-06-24
**Status:** Verbindung funktioniert ✅

---

## Gefundene Hardware

| Feature | Wert |
|---------|------|
| **Gerät** | IOS-Vlink OBD2 Adapter |
| **Hersteller** | Feasycom (FSC-BT826N) |
| **ELM327 Version** | v2.3 |
| **Software** | v5.4.2 |
| **MAC Adresse** | `D2:E0:2F:8D:61:07` |
| **Hardware Revision** | 1.2 |
| **Serial Number** | 13E02F8D6107 |

---

## BLE UUIDs (Gefunden 2026-06-24)

### WICHTIG: Der IOS-Vlink verwendet andere UUIDs als der Standard ELM327!

Standard ELM327 BLE UUIDs (funktionieren NICHT mit diesem Gerät):
- Service: `0000ffe1-0000-1000-8000-00805f9b34fb`
- Characteristic: `0000ffe1-0000-1000-8000-00805f9b34fb`

**Korrekte IOS-Vlink UUIDs:**
- **Service:** `e7810a71-73ae-499d-8c15-faa9aef0c3f2`
- **Characteristic:** `bef8d6c9-9c21-4c9e-b632-bd58c1009f9f`
  - Properties: `read`, `write-without-response`, `write`, `notify`, `indicate`

### Alle gefundenen BLE Services

```
1. 0000180a-0000-1000-8000-00805f9b34fb (GATT Standard Service)
   - 00002a28: Software Revision String → "5.4.2,20190819"
   - 00002a29: Manufacturer Name String → "Feasycom"
   - 00002a25: Serial Number String → "13E02F8D6107"
   - 00002a24: Model Number String → "FSC-BT826N"
   - 00002a27: Hardware Revision String → "1.2"

2. e7810a71-73ae-499d-8c15-faa9aef0c3f2 (OBD2/ELM327 Service)
   - bef8d6c9-9c21-4c9e-b632-bd58c1009f9f ← HIER KOMMUNIZIEREN
     Properties: read, write-without-response, write, notify, indicate

3. 000018f0-0000-1000-8000-00805f9b34fb (Custom Service)
   - 00002af1: Electric Current Statistics (write-only)
   - 00002af0: Electric Current Specification (notify only)

4. 00001800-0000-1000-8000-00805f9b34fb (Device Information)
   - 00002a00: Device Name → "IOS-Vlink"
   - 00002a01: Appearance

5. 00001801-0000-1000-8000-00805f9b34fb (Generic Discoverable)
   - 00002a05: Service Changed
```

---

## Kommunikations-Protokoll

### WICHTIGSTE ERKENNTNIS: Antwort kommt ÜBER NOTIFY!

Der IOS-Vlink sendet ELM327-Antworten **NICHT** über `read_gatt_char()`, sondern über **BLE Notify/Indicate**.

### Korrekte Kommunikations-Reihenfolge:

```python
# 1. Mit Gerät verbinden
async with BleakClient("D2:E0:2F:8D:61:07") as client:
    
    # 2. NotifyHandler einrichten
    def notify_handler(sender, data):
        text = data.decode("utf-8")
        # text enthält die ELM327 Antwort!
        
    await client.start_notify(
        "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f",
        notify_handler
    )
    
    # 3. Kommando SENDEN (write)
    await client.write_gatt_char(
        "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f",
        b"ATZ\r"
    )
    
    # 4. Antwort kommt ÜBER NOTIFY
    # Beispiel-Antwort: "ELM327 v2.3\r\r>"
```

### Getestete AT-Befehle

| Befehl | Antwort | Status |
|--------|---------|--------|
| `ATZ` | `ELM327 v2.3\r\r>` | ✅ Funktioniert |
| `ATI` | (nicht getestet) | ⏳ |
| `ATE0` | OK | ⏳ |
| `ATH0` | OK | ⏳ |
| `ATS0` | OK | ⏳ |
| `ATSP0` | OK | ⏳ |

### Getestete OBD2 PIDs

| Befehl | Bedeutung | Status |
|--------|-----------|--------|
| `0100` | Supported PIDs | ⏳ Testen |
| `010D` | Speed (km/h) | ⏳ Testen |
| `010C` | RPM | ⏳ Testen |
| `0105` | Coolant Temp | ⏳ Testen |
| `0104` | Engine Load | ⏳ Testen |

---

## Python-Implementierung

### Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `pi/ble_client_vgate.py` | **HAUPTKLASSE** - BLE Client mit Notify-Support |
| `pi/rpm_simulation_engine.py` | RPM Engine (E-Auto, basierend auf Speed) |
| `pi/obd2_data_pipeline.py` | Daten-Pipeline BLE → RPM → TCP |
| `pi/elm327_tcp_server_ble.py` | Integrierter TCP Server mit BLE |
| `pi/scan_vlink_services.py` | Service Scanner (Debug) |
| `pi/test_vlink_final.py` | Finaler Test-Skript |

### VgateBLEClient Klasse

```python
from ble_client_vgate import VgateBLEClient

# Initialisierung
client = VgateBLEClient("D2:E0:2F:8D:61:07", debug=True)

# Starten
await client.start()

# Daten lesen
speed = await client.get_speed()
rpm = await client.get_rpm()
data = await client.get_obd_data()

# Stoppen
await client.stop()
```

### Verwendung von Notify

```python
# Der Client richtet einen Notify-Handler ein:
def notify_handler(sender, data):
    text = data.decode("utf-8", errors="ignore")
    # Zum Puffer hinzufügen
    notify_buffer += text

# Command senden
await client.write_gatt_char(
    "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f",
    b"010D\r"
)

# Antwort über Notify empfangen und parsen
```

---

## E-Auto Besonderheiten (Dacia Spring)

### Was funktioniert:
- ✅ Speed (PID 010D) — echt vom Fahrzeug
- ✅ OBD2 Protokoll — ELM327 v2.3 antwortet korrekt

### Was NICHT funktioniert (EV-Einschränkungen):
- ❌ RPM (PID 010C) — kein Verbrennungsmotor → immer 0
- ❌ Engine Load (PID 0104) — keine relevante Daten
- ❌ Coolant Temp (PID 0105) — keine Kühlflüssigkeit

### Unsere Lösung:
- Speed wird echt vom Vlink gelesen
- RPM wird **simuliert** basierend auf Speed und Fahrzustand
  - Stand = 850 RPM (Idle)
  - Beschleunigen = höhere RPM
  - Bremsen/Ausrollen = niedrigere RPM

---

## Bekannte Probleme & Lösungen

### Problem 1: read_gatt_char gibt leere Antwort
**Ursache:** Gerät sendet Antworten über Notify, nicht über Read
**Lösung:** `start_notify()` verwenden + Buffer im Callback füllen

### Problem 2: BLE Connect Timeout
**Ursache:** Gerät ist zu weit weg oder nicht eingesteckt
**Lösung:** Pi nah am OBD2-Port positionieren (< 5cm)

### Problem 3: Falsche UUIDs
**Ursache:** Standard ELM327 UUIDs funktionieren nicht
**Lösung:** Korrekte UUIDs verwenden (siehe oben)

---

## WiFi TCP Server (Integration)

Der integrierte Server `elm327_tcp_server_ble.py`:
- Verbindet sich zu IOS-Vlink über BLE Notify
- Startet TCP Server auf Port 2117
- Gibt ELM327-Antworten an TCP-Clients weiter
- Simuliert RPM basierend auf BLE-Speed

### Starten:
```bash
cd ~/obd2-adapter
source ~/obd2-adapter-env/bin/activate
python3 elm327_tcp_server_ble.py --mac D2:E0:2F:8D:61:07
```

### Android App Verbindung:
- TCP zu: `192.168.178.87:2117`
- Unterstützte Apps: Car Scanner, RevHeadz (mit WiFi TCP Support)

---

## Test-Ergebnisse (2026-06-24)

### BLE Verbindung:
```
✅ Connected: True
✅ Mit OBD2 Adapter verbunden!
🔧 ELM327 initialisiert (ATE0, ATH0, ATS0, ATSP0)
```

### Notify-Response (ATZ):
```
📥 Notify: bytearray(b'ATZ\r')
📥 Notify: bytearray(b'\r\rELM327 v2.3\r\r>')
```

### Service Scanner Ausgabe:
```
✅ Verbunden: True
Service: e7810a71-73ae-499d-8c15-faa9aef0c3f2
  - bef8d6c9-9c21-4c9e-b632-bd58c1009f9f [read, write, notify]
```

---

## Entscheidungen (2026-06-24)

1. **BLE Notify statt Read** — IOS-Vlink sendet Antworten nur über Notify
2. **MAC Adresse hardcoded** — D2:E0:2F:8D:61:07 (statischer Eintrag)
3. **RPM Simulation** — keine echten EV-RPM verfügbar, daher Speed-basiert
4. **WiFi TCP statt Bluetooth** — zuverlässiger als BLE SPP auf Pi

---

## Nächste Schritte (Offen)

- [ ] Fahrt-Test: Echte Speed-Daten mit fahrendem Fahrzeug testen
- [ ] Alle OBD2 PIDs testen (0100, 0104, 0105, 0111)
- [ ] Android App Integration (Car Scanner, RevHeadz)
- [ ] Auto-Start beim Pi Boot
- [ ] EV-spezifische PIDs suchen (Motor-Drehzahl, Battery, Power)

---

*Dieses Dokument wird bei neuen Erkenntnissen aktualisiert.*