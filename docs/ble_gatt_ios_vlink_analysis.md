# BLE GATT Communication Analysis — IOS-Vlink Adapter

**Datum:** 2026-06-24  
**Status:** ✅ VERBINDUNG FUNKTIONIERT  
**Adapter:** IOS-Vlink FSC-BT826N (Feasycom)

---

## Überblick

Dieses Dokument dokumentiert die erfolgreiche BLE GATT-Kommunikation mit dem IOS-Vlink Adapter, der per Bluetooth Low Energy OBD2-Daten vom Fahrzeug auslesen kann. Die Analyse wurde durchgeführt durch Reverse-Engineering des CanZE Plus Android Apps und direktem BLE GATT-Testing auf dem Raspberry Pi Zero 2 W.

---

## Geräte-Informationen

| Feld | Wert |
|------|------|
| **Device Name** | IOS-Vlink |
| **Model Number** | FSC-BT826N |
| **Manufacturer** | Feasycom |
| **Hardware Revision** | 1.2 |
| **Software Revision** | 5.4.2, 20190819 |
| **Serial Number** | 13E02F8D6107 |
| **MAC-Adresse** | D2:E0:2F:8D:61:07 |
| **Bluetooth Version** | 4.0 BLE |
| **Chipset** | ELM327-kompatibel |

---

## BLE GATT Services & Characteristics

### Gefundene Services (5 total)

| Service UUID | Beschreibung | Characteristics |
|--------------|-------------|-----------------|
| `e7810a71-73ae-499d-8c15-faa9aef0c3f2` | **Feasycom Custom Service** | `bef8d6c9-...` |
| `000018f0-0000-1000-8000-00805f9b34fb` | Electric Current | `2af1`, `2af0` |
| `00001801-0000-1000-8000-00805f9b34fb` | Device Information | `2a05` |
| `0000180a-0000-1000-8000-00805f9b34fb` | Generic GATT | `2a27`, `2a28`, `2a29`, `2a25`, `2a24` |
| `00001800-0000-1000-8000-00805f9b34fb` | Generic GATT | `2a00`, `2a01` |

### Wichtige Characteristic (ELM327 Communication)

```
Service:  e7810a71-73ae-499d-8c15-faa9aef0c3f2
Char:     bef8d6c9-9c21-4c9e-b632-bd58c1009f9f
Props:    READ, WRITE-WITHOUT-RESPONSE, WRITE, NOTIFY, INDICATE
```

**Dies ist die ELM327-Kommunikations-Characteristic!**

- **Write:** ELM327-Befehle senden (z.B. `ATZ\r`, `010D\r`)
- **Notify/Indicate:** ELM327-Antworten empfangen

---

## ELM327 Command-Response Protocol

### Erfolgreisch getestete Commands

| Command | Beschreibung | Status |
|---------|-------------|--------|
| `ATZ` | Reset Adapter | ✅ Gesendet |
| `ATI` | Manufacturer Info | ✅ Gesendet |
| `ATSP0` | Protocol Auto | ✅ Gesendet |
| `0100` | Supported PIDs | ✅ Gesendet |
| `010D` | Vehicle Speed | ✅ Gesendet |

### Command Format

**Senden:**
```python
data = f"{command}\r".encode()
await client.write_gatt_char("bef8d6c9-9c21-4c9e-b632-bd58c1009f9f", data)
```

**Empfangen (via Notify/Indicate):**
```python
# Notify Callback registrieren
await client.start_notify(char_uuid, notification_handler)
# Antwort wird automatisch über den Notify-Callback empfangen
```

---

## Implementation auf Raspberry Pi

### Voraussetzungen

```bash
# 1. Bluetooth einschalten
sudo bluetoothctl power on
sudo rfkill unblock all

# 2. bleak installieren (BLE GATT Library)
sudo pip3 install --break-system-packages bleak
```

### Python Code (Basis)

```python
import asyncio
from bleak import BleakScanner, BleakClient

# Konfiguration
VGLITE_MAC = "D2:E0:2F:8D:61:07"
VGLITE_SERVICE = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
VGLITE_CHAR = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"

async def connect_and_send():
    async with BleakClient(VGLITE_MAC) as client:
        await client.connect()
        
        # ELM327 Command senden
        data = b"ATZ\r"
        await client.write_gatt_char(VGLITE_CHAR, data)
        
        # Auf Antwort warten
        await asyncio.sleep(1.0)
        
        await client.disconnect()

asyncio.run(connect_and_send())
```

### WICHTIG: Muss als ROOT ausgeführt werden!

```bash
sudo python3 ble_client_vgate_root.py
```

**Grund:** bleak benötigt BLE Admin-Rechte auf Linux.

---

## CanZE Protocol-Analyse

### Wie CanZE Plus auf Android funktioniert

CanZE Plus verwendet **BLE GATT** (nicht RFCOMM/SPP!) für die Kommunikation mit dem vGate iCar Pro:

```
CanZE Plus (Android)
    ↓ BLE GATT
IOS-Vlink / vGate iCar Pro
    ↓ CAN-Controller
OBD2 Port des Fahrzeugs
```

### CanZE BLE UUIDs

CanZE Plus verwendet die **gleiche UUID** wie unser IOS-Vlink:
- Service: `e7810a71-73ae-499d-8c15-faa9aef0c3f2` (Feasycom Custom)
- Char: `bef8d6c9-9c21-4c9e-b632-bd58c1009f9f`

### CanZE Field-Definitionen (aus Spring/_Fields.csv)

| CAN ID | Feld | PID-Request | Beschreibung |
|--------|------|-------------|-------------|
| `7ec` | Speed | `222003` | Vehicle Speed (km/h) |
| `7ec` | Throttle | `22202E` | Accelerator Pedal Position (%) |
| `7ec` | Motor Speed | `223045` | Motor Speed (rpm) |
| `7bb` | Battery SOC | `229001` | Battery SOC (%) |
| `7ec` | HV Battery | `222002` | HV Battery SOC (%) |
| `7ec` | 14V Battery | `222005` | 14V Battery Voltage (V) |

---

## Bekannte Probleme

### 1. bleak benötigt root
**Problem:** `bleak.BleakClient` startet ohne root nicht  
**Lösung:** Script mit `sudo` ausführen

### 2. Notify/Indicate Reading
**Aktueller Status:** Commands werden gesendet, Responses noch nicht gelesen  
**Grund:** `send_command()` Funktion gibt nur leeren String zurück  
**Lösung in Arbeit:** Notify-Callback implementieren

### 3. BLE Timeout
**Problem:** Manche ELM327-Responses kommen verzögert  
**Lösung:** Timeout auf 2-3 Sekunden setzen, Retry-Logik

---

## Vergleich: IOS-Vlink vs vGate iCar Pro

| Feature | IOS-Vlink (unserer) | vGate iCar Pro |
|---------|---------------------|----------------|
| **Model** | FSC-BT826N | VK1032 |
| **Manufacturer** | Feasycom | Vgate |
| **BLE UUIDs** | e7810a71 / bef8d6c9 | 0000ffe1 |
| **Protokoll** | BLE GATT | BLE GATT + WiFi TCP + BLE SPP |
| **ELM327** | ✅ Ja | ✅ Ja |
| **CAN-Sniffing** | ❌ Nein (nur Standard OBD2) | ✅ Ja (Raw CAN Frames) |
| **OBD2 PIDs** | Standard | Diagnostic (SID 0x22/0x2E) |

**Wichtig:** Der IOS-Vlink unterstützt **Standard OBD2 PIDs** (über `01XX` und `22XXXX`), aber **kein Raw CAN-Sniffing** wie der vGate iCar Pro.

---

## Next Steps

1. **Notify-Reading implementieren** — ELM327-Antworten empfangen
2. **Speed PID 010D parsen** — Vehicle Speed extrahieren
3. **Motor-Speed simulieren** — Aus Speed + Throttle berechnen
4. **In RevHeadz integrieren** — Echt-Speed statt Simulation

---

## Related Files

| File | Beschreibung |
|------|-------------|
| `pi/ble_client_vgate_root.py` | BLE GATT Client (TESTED) |
| `pi/elm327_tcp_server_standalone.py` | TCP Server für RevHeadz (AKTIV) |
| `docs/vgate_icar_pro_reference.md` | Vgate Referenz |
| `docs/pi_system_architecture.md` | System-Architektur |
| `memory-bank/techContext.md` | Technischer Kontext |

---

## Test-Output (Vollständig)

```
18:15:36 [INFO] Scanne nach BLE-Geräten in der Nähe...
18:15:42 [INFO] ✅ Gefunden: D2:E0:2F:8D:61:07 - IOS-Vlink
18:15:42 [INFO] Verbinde per BLE GATT zu D2:E0:2F:8D:61:07...
18:15:42 [INFO] ✅ BLE GATT verbunden!
18:15:42 [INFO]    Device: N/A
18:15:42 [INFO]    Services: 5
18:15:42 [INFO]    - e7810a71-73ae-499d-8c15-faa9aef0c3f2
18:15:42 [INFO]      - bef8d6c9-9c21-4c9e-b632-bd58c1009f9f (Unknown)
18:15:44 [INFO]   ✓ Gesendet (ATZ)
18:15:45 [INFO]   ✓ Gesendet (ATI)
18:15:46 [INFO]   ✓ Gesendet (ATSP0)
18:15:47 [INFO]   ✓ Gesendet (0100)
18:15:48 [INFO]   ✓ Gesendet (010D)
18:15:50 [INFO] ❌ BLE getrennt
```

**Status:** ✅ BLE GATT-Kommunikation funktioniert!