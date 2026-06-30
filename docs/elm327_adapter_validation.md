# ELM327 Adapter-Validierung für Dacia Spring

## Problemstellung

Viele billige chinesische ELM327-Adapter können keine bzw. unvollständige CAN-Bus-Daten vom Dacia Spring (bzw. Renault Megane E-State Plattform) lesen. Das vGate iCar Pro hingegen funktioniert zuverlässig.

## Der Schlüssel: PIC18F25K80 Chip

CanZE Plus (und verwandte Apps wie CanZE4iOS) connecten mit ELM327 OBD-Geräten mit **PIC18F25K80 Chip** (Version 1.5), z.B.:
- KONWEI KW902
- vGate iCar Pro
- ELM327 Mini (Original)

### Warum der PIC18F25K80 wichtig ist

Der PIC18F25K80 ist ein 28-Pin Microcontroller von Microchip mit integriertem **CAN 2.0 Controller**-Modul:

| Eigenschaft | Wert |
|-------------|------|
| CAN-Version | 2.0A/B (bis 1 Mbps) |
| CAN-Buffer | 2 TX/RX Buffer |
| Flash | 256 KB |
| RAM | 2048 Bytes |
| Erweiterte CAN-IDs | JA (bis 29-bit / Extended) |
| J1939 Support | JA |

### Der Unterschied zu billigen Clones

Viele billige Adapter verwenden:
1. **GCW05/GCW08 Chips** - KEIN echter ELM327, keine CAN-Implementierung
2. **PIC18F25K80 "Lite" Firmware** - Blockiert Extended CAN IDs
3. **FPGA-basierte Emulation** - Keine echte CAN-Hardware

vGate iCar Pro verwendet den **PIC18F47K42** (erweiterte Version) mit vollständiger CAN-Implementierung.

---

## Adapter-Validierungstests

### Test 1: ELM327 Identifikation

```
Befehl:    ATZ
Erwartet:  ELM327 v1.5 oder ELM327 v2.1

Befehl:    ATI
Erwartet:  PIC18F25K80 oder ähnlich
```

### Test 2: CAN-Protokoll-Erkennung

```
Befehl:    ATSP0
Bedeutung: Auto-Probing aktivieren

Befehl:    ATDPN
Erwartet:  6 (ISO 15765-4 500K) oder 7 (ISO 15765-4 250K)
```

### Test 3: Standard OBD2 PID

```
Befehl:    0100
Bedeutung: Supported PIDs bitmask request

Erwartete Antwort:
41 00 XX XX XX XX XX XX
  └─ Response Indicator └─ PID 0 (Supported PIDs 21-40)
```

### Test 4: Extended CAN Diagnostic

```
Befehl:    ATSH 7E0
Bedeutung: Setze CAN-ID auf 7E0 (Diagnostic Request)

Befehl:    ATSH 7E8
Bedeutung: Setze CAN-ID auf 7E8 (Diagnostic Response)

Befehl:    03
Bedeutung: Mode 03 - Freeze Frame Data

Erwartete Antwort:
7E8 06 43 01 XX ...
  └─ Response ID └─ Mode 03 Response
```

### Test 5: Raw CAN Frame Capture

```
Befehl:    ATCR
Bedeutung: Clear/Read CAN Rahmen

Erwartet:  CAN-Frames mit 29-bit Extended IDs (z.B. 18DA00F1)
```

---

## Dacia Spring spezifische CAN-Bus IDs

### Wichtige CAN-IDs für Dacia Spring (elektrisch):

| CAN-ID | Richtung | Beschreibung |
|--------|----------|--------------|
| 0x0B0 | Vehicle → Bus | KOM Motor-Status |
| 0x2B8 | Vehicle → Bus | Batteriemanagement (LBC) |
| 0x18DA00F1 | UDS | Dynamic Address 0xF1 (Response) |
| 0x18DAF100 | UDS | Dynamic Address 0xF0 (Request) |
| 0x7E0/0x7E8 | Diagnostic | Extended Diagnostic (32-bit) |
| 0x7DF | OBD2 | Standard OBD2 Broadcast |
| 0x7E0 | OBD2 | Standard OBD2 Request (9-bit) |

### Wichtige OBD2 PIDs für Dacia Spring:

| PID | Beschreibung | Format |
|-----|--------------|--------|
| 0100 | Supported PIDs | Bitmask |
| 010C | Engine RPM | A*256/B (elektrisch = 0) |
| 010D | Vehicle Speed | A km/h |
| 0105 | Coolant Temperature | A-40 °C |
| 0131 | Battery SOC | A*100/255 % |

---

## Empfohlene Adapter-Whitelist

### ✅ Getestet & Funktionierend:
- vGate iCar Pro (PIC18F47K42)
- OBDLink EX / UX
- KONWEI KW902
- ELM327 Mini (Original, PIC18F25K80)

### ⚠️ Bedingt Funktionierend:
- Billige ELM327 v1.5 (PIC18F25K80) - muss Extended CAN unterstützen
- ELM327 v2.1 - hängt von der Firmware ab

### ❌ Nicht Funktionierend:
- GCW05 / GCW08 Clone
- Bluetooth OBD2 "ELM" Adapter ohne echten Chip
- USB "OBD2" Adapter ohne CAN-Controller

---

## Validierungs-Script (Python-Pseudocode)

```python
import serial

class ELM327Validator:
    def __init__(self, port, baudrate=38400):
        self.ser = serial.Serial(port, baudrate, timeout=2)
    
    def send_command(self, cmd):
        """Sende AT-Befehl und empfange Antwort"""
        self.ser.write((cmd + '\r\n').encode())
        response = self.ser.read(self.ser.in_waiting).decode()
        return response.strip()
    
    def validate_adapter(self):
        """Führe alle Validierungstests durch"""
        results = {}
        
        # Test 1: ELM327 Identifikation
        results['ATZ'] = self.send_command('ATZ')
        results['ATI'] = self.send_command('ATI')
        
        # Test 2: CAN-Protokoll
        results['ATSP0'] = self.send_command('ATSP0')
        results['ATDPN'] = self.send_command('ATDPN')
        
        # Test 3: Standard OBD2 PID
        results['0100'] = self.send_command('0100')
        
        # Test 4: Extended CAN
        self.send_command('ATSH 7E0')
        results['03'] = self.send_command('03')
        
        return results
    
    def is_valid_for_dacia_spring(self, results):
        """Prüfe ob Adapter für Dacia Spring geeignet"""
        # Muss echte ELM327-Identifikation haben
        if 'ELM327' not in str(results.get('ATZ', '')):
            return False, "Kein echter ELM327 Adapter"
        
        # Muss Extended CAN unterstützen
        if '7E' not in str(results.get('03', '')):
            return False, "Kein Extended CAN Support"
        
        return True, "Adapter ist kompatibel"
```

---

## Nächste Schritte

1. **Adapter-Validation-Script für Raspberry Pi erstellen**
2. **Dacia Spring CAN-Bus-IDs dokumentieren** (volle DB-Csv)
3. **CAN-Daten-Validierungspipeline bauen**
4. **Plausibilitäts-Checks implementieren**

---

*Dieses Dokument wird fortlaufend aktualisiert basierend auf neuen Erkenntnissen.*