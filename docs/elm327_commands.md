# ELM327 AT-Befehlsreferenz

## Übersicht

Der ELM327 ist ein kleiner Chip, der als Schnittstelle zwischen OBD2-fähigen Fahrzeugen und Diagnosegeräten (Handy, Tablet, PC) dient. Unsere Emulation muss sich vollständig wie ein ELM327 verhalten.

## Initialisierung des Handshakes

### 1. Bluetooth-Verbindung herstellen
- Android-App verbindet sich via RFCOMM/Bluetooth SPP
- ELM327 sendet WILLKOMMEN (optional, kann konfiguriert werden)
- Standard Willkommensmeldung:
```
Starting PIC32...
ELM327 v1.5
```

### 2. AT-Befehle vom Client empfangen
Der Client sendet typischerweise:
```
ATZ
ATE0
ATH0
ATS0
E
ATDPN
ATSP0
```

---

## AT-Befehle im Detail

### ATZ - Reset des Geräts

**Anfrage:** `ATZ`
**Antwort:** `OK` (gefolgt von Willkommensnachricht bei neuem Reset)
**Beschreibung:** Setzt das Gerät auf Werkseinstellungen zurück

**Implementierung:**
```python
def handle_atz():
    # Reset allen State
    bluetooth_echo = True
    bluetooth_header = True
    bluetooth_spaces = True
    protocol = 0  # Auto
    # ... alle anderen Defaults
    
    send_response("OK")
    # Optional: Willkommensnachricht beim ersten Reset
    # send_welcome_message()
```

### ATI - Hersteller/Version Info

**Anfrage:** `ATI`
**Antwort:** `ELM327 v1.5` (oder ähnlicher String)
**Beschreibung:** Gibt Hersteller und Firmware-Version zurück

**Implementierung:**
```python
def handle_ati():
    send_response("ELM327 v1.5")
    send_response("OBD2 EV Adapter")
```

### ATE[0|1] - Echo ein/aus

**Anfrage:** `ATE0` (Echo aus) oder `ATE1` (Echo an)
**Antwort:** `OK`
**Beschreibung:** Steuert ob gesendete Befehle vom Gerät echoed werden

**Implementierung:**
```python
def handle_ate(param):
    global bluetooth_echo
    if param == "0":
        bluetooth_echo = False
    elif param == "1":
        bluetooth_echo = True
    send_response("OK")
```

### ATH[0|1] - Header ein/aus

**Anfrage:** `ATH0` (Header aus) oder `ATH1` (Header an)
**Antwort:** `OK`
**Beschreibung:** Steuert ob Protokoll-Header gesendet werden

**Mit Header:**
```
ATZ
Starting PIC32...
ELM327 v1.5
OK

0100
01 41 00 BC 01 00 00 00 00 00 00
OK

010C
1150
OK
```

**Ohne Header (ATH0):**
```
ATZ
OK
0100
41 00 BC 01 00 00 00 00 00 00 00
OK
010C
1150
OK
```

**Implementierung:**
```python
def handle_ath(param):
    global bluetooth_header
    if param == "0":
        bluetooth_header = False
    elif param == "1":
        bluetooth_header = True
    send_response("OK")
```

### ATS[0|1] - Space ein/aus

**Anfrage:** `ATS0` (Space aus) oder `ATS1` (Space an)
**Antwort:** `OK`
**Beschreibung:** Steuert ob Spaces zwischen Bytes gesendet werden

**Mit Space (ATS1):**
```
41 0C 0F A0
```

**Ohne Space (ATS0):**
```
410C0FA0
```

**Implementierung:**
```python
def handle_ats(param):
    global bluetooth_spaces
    if param == "0":
        bluetooth_spaces = False
    elif param == "1":
        bluetooth_spaces = True
    send_response("OK")
```

### ATSP[0-FF] - Protokoll setzen

**Anfrage:** `ATSP0` (Auto Select) oder `ATSPx` (festes Protokoll)
**Antwort:** `OK` oder `CAN ERROR` wenn Protokoll nicht verfügbar
**Beschreibung:** Wählt das OBD2-Protokoll

**Wichtige Protokoll-Nummern:**
| Wert | Protokoll |
|------|----------|
| 0 | Auto Select |
| 1 | ISO 9141-2 |
| 4 | ISO 15765-4 (CAN 11/500) |
| 5 | ISO 15765-4 (CAN 29/500) |
| 6 | ISO 15765-4 (CAN 11/250) |
| 8 | ISO 15765-4 (CAN 29/250) |

**Implementierung:**
```python
def handle_atsp(param):
    global current_protocol
    protocol = int(param, 16)
    
    if protocol == 0:
        current_protocol = 4  # Default: CAN 11/500 für moderne Fahrzeuge
    elif protocol in [1, 4, 5, 6, 8]:
        current_protocol = protocol
    else:
        send_response("ERROR")
        return
    
    send_response("OK")
```

### ATDPN - Aktuelles Protokoll anzeigen

**Anfrage:** `ATDPN`
**Antwort:** `PROTOCOL: 4` (oder aktueller Wert)
**Beschreibung:** Zeigt das aktuell eingestellte Protokoll

**Implementierung:**
```python
def handle_atdpn():
    send_response(f"PROTOCOL: {current_protocol}")
```

### E - Ausgabepuffer löschen

**Anfrage:** `E`
**Antwort:** `OK`
**Beschreibung:** Löscht den Ausgabepuffer

**Implementierung:**
```python
def handle_e():
    clear_output_buffer()
    send_response("OK")
```

### ATBR - Baudrate setzen

**Anfrage:** `ATBRx`
**Antwort:** `OK`
**Beschreibung:** Setzt die Baudrate der seriellen Verbindung

---

## PID-Anfragen (OBD2 Data Requests)

### Format der Anfrage
```
01nnXX  # n = Funktion (01 = Echtzeit-Daten), nnXX = PID
02nnXX  # Instant
03nnXX  # Freeze Frame
04nnXX  # Saved DTC
05nnXX  # Test Results
06nnXX  # Monitor Results
07nnXX  # Pending DTC
08nnXX  # Control
09nnXX  # Vehicle Information
0Annnn  # Extended Data
```

### Wichtige PIDs für Sound-Apps

#### 0100 - Supported PIDs 01-20
#### 010C - Engine RPM
#### 010D - Vehicle Speed
#### 0104 - Engine Load
#### 0105 - Coolant Temperature
#### 010E - Fuel Temperature
#### 010F - Intake Air Temperature
#### 0110 - Timing Advance

### Antwort-Format

**Erfolgreiche Antwort:** `41 nnXX [Datenbytes]`
**Keine Daten:** `NO DATA`
**Fehler:** `ERROR`

---

## Implementierungs-Beispiel (Python)

```python
class ELM327Emulator:
    def __init__(self):
        self.echo_enabled = True
        self.header_enabled = True
        self.spaces_enabled = True
        self.protocol = 4  # CAN 11/500
        self.vehicle_ready = False
        self.virtual_rpm = 0
        self.vehicle_speed = 0
        
    def process_command(self, cmd):
        """Verarbeite einen eingehenden Befehl"""
        cmd = cmd.strip().upper()
        
        # AT-Befehle
        if cmd.startswith("AT"):
            return self.handle_at_command(cmd)
        elif cmd.startswith("01"):
            return self.handle_obd2_request(cmd)
        else:
            return "ERROR"
    
    def handle_at_command(self, cmd):
        """Verarbeite AT-Befehle"""
        if cmd == "ATZ":
            self.reset_state()
            return "OK"
        elif cmd == "ATI":
            return "ELM327 v1.5\nOBD2 EV Adapter"
        elif cmd == "ATE0":
            self.echo_enabled = False
            return "OK"
        elif cmd == "ATH0":
            self.header_enabled = False
            return "OK"
        elif cmd == "ATS0":
            self.spaces_enabled = False
            return "OK"
        elif cmd == "ATSP0":
            self.protocol = 4
            return "OK"
        elif cmd == "ATDPN":
            return f"PROTOCOL: {self.protocol}"
        else:
            return "OK"  # Fallback
    
    def handle_obd2_request(self, cmd):
        """Verarbeite OBD2-PID-Anfragen"""
        pid_hex = cmd[2:]  # z.B. "0C" für 010C
        
        if pid_hex == "00":
            return self.build_supported_pids_response()
        elif pid_hex == "0C":
            return self.build_rpm_response()
        elif pid_hex == "0D":
            return self.build_speed_response()
        else:
            return "NO DATA"
    
    def build_rpm_response(self):
        """Baelde die RPM-Antwort"""
        if not self.vehicle_ready:
            return "NO DATA"
        
        # RPM in Bytes konvertieren
        value = int(self.virtual_rpm * 4)
        a = (value >> 8) & 0xFF
        b = value & 0xFF
        
        if self.spaces_enabled:
            return f"41 0C {a:02X} {b:02X}"
        else:
            return f"410C{a:02X}{b:02X}"
    
    def build_speed_response(self):
        """Baelde die Speed-Antwort"""
        speed_byte = min(self.vehicle_speed, 255)
        
        if self.spaces_enabled:
            return f"41 0D {speed_byte:02X}"
        else:
            return f"410D{speed_byte:02X}"
    
    def build_supported_pids_response(self):
        """Baelde die Supported PIDs Antwort"""
        # Bitfeld: PID 4, 5, 12, 13 sind unterstützt
        # Bits: PID 4, 5, 12, 13 gesetzt = 0x000001C6
        # But PID 12 (0C) and 13 (0D) are in the second word
        # Support: PID 4, 5, 12, 13
        return "41 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
```

---

## Typischer Handshake-Ablauf

```
Client → Server: (Bluetooth-Verbindung)
Server → Client: Starting PIC32...
Server → Client: ELM327 v1.5
Client → Server: ATZ
Server → Client: OK
Client → Server: ATI
Server → Client: ELM327 v1.5
Client → Server: ATE0
Server → Client: OK
Client → Server: ATH0
Server → Client: OK
Client → Server: ATS0
Server → Client: OK
Client → Server: ATSP0
Server → Client: OK
Client → Server: 0100
Server → Client: 410000000000000000000000
Client → Server: 010C
Server → Client: 0F A0         (4000 RPM)
Client → Server: 010D
Server → Client: 00 32           (50 km/h)
```

---

## Fehlerbehandlung

| Fehler | Antwort | Situation |
|--------|---------|----------|
| Ungültiger AT-Befehl | `ERROR` | unbekannter Befehl |
| PID nicht verfügbar | `NO DATA` | Fahrzeug nicht Ready |
| CAN-Fehler | `CAN ERROR` | CAN-Kommunikation gestört |
| Timeout | `TIMEOUT` | Keine Antwort vom Fahrzeug |
| Buffer voll | `BUFFER FULL` | Zu viele Anfragen |

---

## Hinweis zur Implementierung

Für ESP32 mit MicroPython oder ESP-IDF muss besonders auf folgende Punkte geachtet werden:

1. **Echtzeit-Fähigkeit:** CAN-Daten müssen <50ms verarbeitet werden
2. **Bluetooth-Puffer:** SPP-Puffer nicht überlaufen lassen
3. **Protokoll-Status:** ATSP0 muss CAN 11/500 (Protokoll 4) auswählen
4. **Kein Header/Space:** ATH0 + ATS0 für minimale Antwortgröße