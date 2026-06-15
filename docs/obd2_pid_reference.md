# OBD2 PID Referenz - Implementierungsplan

## PID 0x00: Supported PIDs 01-20

**Antwort-Format:** 1-4 Bytes Bitfeld
**Beschreibung:** Zeigt welche PIDs unterstützt werden

**Unsere Antwort (Beispiel):**
```
41 00 BC01 0000
```
Bit-Interpretation:
- Bit 15 (PID 16): 0 = Nicht unterstützt
- Bit 14 (PID 17): 0 = Nicht unterstützt
- Bit 13 (PID 18): 0 = Nicht unterstützt
- Bit 12 (PID 19): 0 = Nicht unterstützt
- Bit 11 (PID 20): 0 = Nicht unterstützt
- Bit 10 (PID 14): 0 = Nicht unterstützt
- Bit 9  (PID 13): 0 = Nicht unterstützt
- Bit 8  (PID 12): 1 = Unterstützt (RPM)
- Bit 7  (PID 11): 0 = Nicht unterstützt
- Bit 6  (PID 10): 0 = Nicht unterstützt
- Bit 5  (PID 09): 0 = Nicht unterstützt
- Bit 4  (PID 08): 0 = Nicht unterstützt
- Bit 3  (PID 07): 0 = Nicht unterstützt
- Bit 2  (PID 06): 0 = Nicht unterstützt
- Bit 1  (PID 05): 1 = Unterstützt (Coolant Temp)
- Bit 0  (PID 04): 1 = Unterstützt (Engine Load)
- Bit 15 (PID 0D): 1 = Unterstützt (Speed)

## PID 0x0C: Engine RPM

**Anfrage:** `010C`
**Antwort:** `41 0C XX XX`
**Formel:** `RPM = (A × 256 + B) / 4`
**Bereich:** 0 - 8191 RPM
**Genauigkeit:** 0.25 RPM

### Beispiele:
| RPM | Byte A | Byte B | Antwort |
|-----|--------|--------|---------|
| 0 | 0x00 | 0x00 | 41 0C 00 00 |
| 800 | 0x00 | 0xC8 | 41 0C 00 C8 |
| 1000 | 0x00 | 0xFA | 41 0C 00 FA |
| 3000 | 0x02 | 0xD5 | 41 0C 02 D5 |
| 6000 | 0x05 | 0xAA | 41 0C 05 AA |

### Implementierung:
```
# Pseudocode für RPM-Berechnung
function rpmToBytes(rpm):
    value = rpm * 4
    byte_a = value >> 8
    byte_b = value & 0xFF
    return "41 0C " + hex(byte_a) + " " + hex(byte_b)
```

## PID 0x0D: Vehicle Speed

**Anfrage:** `010D`
**Antwort:** `41 0D AA`
**Formel:** `Speed = A` km/h
**Bereich:** 0 - 255 km/h
**Genauigkeit:** 1 km/h

### Beispiele:
| Speed | Byte A | Antwort |
|-------|--------|---------|
| 0 km/h | 0x00 | 41 0D 00 |
| 30 km/h | 0x1E | 41 0D 1E |
| 50 km/h | 0x32 | 41 0D 32 |
| 100 km/h | 0x64 | 41 0D 64 |
| 200 km/h | 0xC8 | 41 0D C8 |

### Implementierung:
```
# Pseudocode für Speed
function speedToBytes(speed_kmh):
    byte_a = min(speed_kmh, 255)  # Clamp auf 255
    return "41 0D " + hex(byte_a)
```

## PID 0x04: Calculated Engine Load

**Anfrage:** `0104`
**Antwort:** `41 04 AA`
**Formel:** `Load = (A / 255) × 100%`
**Bereich:** 0 - 100%
**Genauigkeit:** ~0.39%

### Implementierung:
```
function loadToBytes(load_percent):
    byte_a = int(load_percent × 255 / 100)
    return "41 04 " + hex(byte_a)
```

## PID 0x05: Engine Coolant Temperature

**Anfrage:** `0105`
**Antwort:** `41 05 AA`
**Formel:** `Temp = A - 40°C`
**Bereich:** -40°C bis 215°C
**Genauigkeit:** 1°C

### Implementierung:
```
function tempToBytes(temp_celsius):
    byte_a = temp_celsius + 40
    return "41 05 " + hex(byte_a)
```

**Hinweis für EV:** Simuliere konstant 90°C (typische Motortemperatur)

## Nützliche Referenzwerte

### OBD2 Protokolle
| Protokoll | Name | Baudrate |
|-----------|------|----------|
| Auto | Auto Select | - |
| 1 | ISO 9141-2 | 10.4 kbps |
| 2 | ISO 14230-4 (KWP2000 Slow) | 10.4 kbps |
| 3 | ISO 14230-4 (KWP2000 Fast) | 10.4 kbps |
| 4 | ISO 15765-4 (CAN 11/500) | 500 kbps |
| 6 | ISO 15765-4 (CAN 29/500) | 500 kbps |
| 7 | ISO 15765-4 (CAN 11/250) | 250 kbps |
| 8 | ISO 15765-4 (CAN 29/250) | 250 kbps |
| 9 | SAE J1939 (CAN 29/250) | 250 kbps |
| A | SAE J1939 (CAN 29/500) | 500 kbps |
| B | User Defined (CAN 11/500) | 500 kbps |
| C | User Defined (CAN 11/250) | 250 kbps |
| D | User Defined (CAN 29/500) | 500 kbps |
| E | User Defined (CAN 29/250) | 250 kbps |

### ELM327 Response Codes
| Code | Bedeutung |
|------|-----------|
| `OK` | Befehl erfolgreich |
| `NO DATA` | Keine Antwort vom Fahrzeug |
| `ERROR` | Allgemeiner Fehler |
| `CAN ERROR` | CAN-Kommunikationsfehler |
| `TIMEOUT` | Zeitüberschreitung |
| `UNABLE TO CONNECT` | Keine Fahrzeugverbindung |
| `BUFFER FULL` | Puffer überlaufen |