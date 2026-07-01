# Vlink Adapter — BLE Pairing + Bluetooth Classic SPP

Der **Vlink Adapter** (erhältlich als iOS- und Android-Version) ist ein OBD2-Adapter, der **Bluetooth Low Energy (BLE)** für das Pairing nutzt und danach auf **Bluetooth Classic Serial Port Profile (SPP)** für die eigentlichen OBD2-Daten umschaltet.

**Wichtig:** Es gibt nur diesen einen Adapter — die iOS- und Android-Versionen verwenden dieselbe Hardware. Der Unterschied liegt lediglich in der App-Steuerung.

---

## 🔌 Betriebsarten

### BLE GATT (Pairing & Discovery)

Zuerst verbindet sich der Pi (oder ein Smartphone) per BLE mit dem Adapter:

| Eigenschaft | Wert |
|-------------|------|
| **Service UUID** | `e7810a71-73ae-499d-8c15-faa9aef0c3f2` |
| **Char UUID** | `bef8d6c9-9c21-4c9e-b632-bd58c1009f9f` |
| **Reichweite** | Bis zu 10 Meter (line of sight) |
| **Verwendung** | Discovery, Pairing, Initialisierung |

```python
# BLE Pairing Beispiel mit bleak
import asyncio
from bleak import BleakClient

SERVICE_UUID = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
CHAR_UUID = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"
ADDRESS = "D2:E0:2F:8D:61:07"  # Vlink MAC-Adresse

async def pair_with_vlink():
    async with BleakClient(ADDRESS) as client:
        await client.connect()
        # ATZ — Adapter resetten
        await client.write_gatt_char(CHAR_UUID, b"ATZ\r".encode())
        response = await client.read_gatt_char(CHAR_UUID)
        print(response.decode())
```

### Bluetooth Classic SPP (Datenübertragung)

Nach erfolgreichem BLE-Pairing wechselt der Adapter auf **Bluetooth Classic SPP**:

| Eigenschaft | Wert |
|-------------|------|
| **Protokoll** | RFCOMM Channel 1 (Serial Port Profile) |
| **Baudrate** | 115200 (automatisch) |
| **Device** | `/dev/rfcomm0` (auf Raspberry Pi) |
| **Verwendung** | Echte OBD2-Daten, AT-Befehle |

```bash
# RFCOMM Device erstellen
sudo rfcomm bind /dev/rfcomm0 D2:E0:2F:8D:61:07 1

# Test mit minicom
sudo screen /dev/rfcomm0 115200
# ATZ
# 010D  (Vehicle Speed)
```

---

## 🚗 OBD2-PIDs beim Dacia Spring

### Standard-PIDs (über ELM327)

| PID | Befehl | Bedeutung | Verfügbarkeit |
|-----|--------|-----------|---------------|
| 0x0D | `010D` | Vehicle Speed | ✅ Echt vom CAN-Bus |
| 0x0C | `010C` | Engine RPM | ⚠️ Simuliert (kein Verbrenner) |
| 0x0A | `010A` | Engine Load | ⚠️ EV-spezifisch |
| 0x05 | `0105` | Coolant Temp | ⚠️ EV-spezifisch |
| 0x11 | `0111` | Throttle Position | ✅ Echt vom CAN-Bus |

### CAN-Bus PIDs (direkt vom Fahrzeug)

| CAN-ID | Funktion | Format |
|--------|----------|--------|
| `222003` | Speed (km/h) | 16-bit Big-Endian |
| `22202E` | Throttle (%) | 16-bit Big-Endian /10 |

**Hinweis:** Da der Dacia Spring ein Elektrofahrzeug ist, sind RPM und viele Verbrenner-PIDs nicht direkt verfügbar. Der Pi berechnet RPM basierend auf Speed + Throttle.

---

## 📡 Architektur: Pi als Bluetooth Bridge

```
Auto OBD2 Port
      │
      ▼
┌──────────────────────┐
│   Vlink Adapter      │
│  BLE GATT (Pairing)  │
│  BT Classic SPP (DAT)│
│  MAC: D2:E0:2F:8D:61:07 │
└──────────┬───────────┘
           │ Bluetooth Classic SPP
           │ RFCOMM Channel 1
           ▼
┌─────────────────────────────────┐
│  Raspberry Pi Zero 2 W          │
│                                 │
│  /dev/rfcomm0 → SPP Reader      │
│  CAN-PIDs: 222003 (Speed)       │
│            22202E (Throttle)    │
│                                 │
│  spp_tcp_server.py              │
│  → Bridgebt CAN zu TCP          │
│  → RPM Engine (Speed+Throttle)  │
│                                 │
│  Port: 2117 / TCP               │
└──────────┬──────────────────────┘
           │ WiFi TCP
           │ Port 2117
           ▼
┌─────────────────────────────────┐
│  Android Phone / Tablet         │
│  RevHeadz / Car Scanner         │
│  - RPM Anzeige                  │
│  - Speed (echt vom CAN-Bus)     │
│  - Throttle (echt vom CAN-Bus)  │
│  - Motorsound-Synthese          │
└─────────────────────────────────┘
```

---

## 🔧 Einrichtung am Raspberry Pi

### 1. BLE-Pairing (einmalig)

```bash
bluetoothctl
[bluetooth]# scan on
[bluetooth]# pair D2:E0:2F:8D:61:07
[bluetooth]# trust D2:E0:2F:8D:61:07
[bluetooth]# connect D2:E0:2F:8D:61:07
```

### 2. RFCOMM Device erstellen

```bash
sudo rfcomm bind /dev/rfcomm0 D2:E0:2F:8D:61:07 1
```

### 3. SPP Server starten

```bash
cd /home/lsd/obd2-adapter
python3 spp_tcp_server.py &
```

### 4. Server-Status prüfen

```bash
ss -tlnp | grep 2117
# Sollte zeigen: LISTEN 0 100 0.0.0.0:2117
```

---

## 📱 Android App verbinden

### RevHeadz

1. Verbindungstyp: **WiFi OBD2 Adapter**
2. IP: Pi-Adresse (`hostname -I`)
3. Port: `2117`
4. Verbinden

### Car Scanner ELM OBD2

1. Verbindung: **WiFi / TCP**
2. Device: Manuelles Device
3. IP: Pi-Adresse
4. Port: `2117`
5. Protokoll: ELM327

---

## ⚠️ Bekannte Probleme

### 1. Bluetooth Classic wechselt nicht nach BLE-Pairing

**Symptom:** Adapter pairingt per BLE, sendet aber keine Daten über SPP.

**Lösung:**
```bash
# Adapter neu starten
sudo rfcomm release /dev/rfcomm0
sudo rfcomm bind /dev/rfcomm0 D2:E0:2F:8D:61:07 1
sudo systemctl restart spp-elm327-server
```

### 2. BLE-Verbindung instabil

**Symptom:** Discovery findet Adapter nicht.

**Lösung:**
- Pi nah am Adapter platzieren (< 5 cm)
- Bluetooth neu starten: `sudo systemctl restart bluetooth`

### 3. Mehrere Vlink Adapter in der Nähe

**Symptom:** Verbindet mit falschem Adapter.

**Lösung:**
- MAC-Adresse fixieren (siehe oben)
- BLE-Service-UUID filtern

---

## 📚 Weitere Informationen

| Dokument | Inhalt |
|----------|--------|
| [ELM327 Befehle](docs/elm327_commands.md) | Komplette AT-Befehlsreferenz |
| [OBD2 PIDs](docs/obd2_pid_reference.md) | Alle PIDs und Formeln |
| [CAN Bus Referenz](docs/can_bus_reference.md) | CAN-Frame-Formate, Dacia Spring |
| [Systemarchitektur](docs/pi_system_architecture.md) | Alle Dienste, Command-Flows, Debugging |

---

**Autor:** Esol1337HaXor
**Letzte Aktualisierung:** 2026-07-01