# ELM327 Adapter Validator für Dacia Spring

## Übersicht

Dieses Tool validiert ELM327-basierte OBD2-Adapter auf Kompatibilität mit dem **Dacia Spring** (elektrisch). Es prüft ob der Adapter die erforderlichen Features für die CAN-Bus-Kommunikation unterstützt.

## Warum dieser Validator?

Viele billige chinesische ELM327-Adapter können keine bzw. unvollständige CAN-Bus-Daten vom Dacia Spring lesen. Der Validator identifiziert inkompatible Adapter bevor sie im Einsatz sind.

### Bekannte Probleme mit inkompatiblen Adaptern:
- GCW05/GCW08 "Clone"-Adapter (keine echte CAN-Implementierung)
- PIC18F25K80 mit "Lite" Firmware (blockiert Extended CAN IDs)
- FPGA-basierte ELM327-Emulation ohne echte CAN-Hardware

### Getestete funktionierende Adapter:
- ✅ vGate iCar Pro (PIC18F47K42)
- ✅ OBDLink EX / UX
- ✅ KONWEI KW902
- ✅ ELM327 Mini (Original, PIC18F25K80)

## Installation

### Abhängigkeiten

```bash
# Python 3.8+ erforderlich
python3 --version

# Serial-Kommunikation Bibliothek
pip3 install pyserial

# Für TCP/IP (WiFi Adapter) ist keine zusätzliche Installation nötig
```

### Deployment auf Raspberry Pi

```bash
# Script auf den Pi kopieren
scp pi/adapter_validator.py lsd@192.168.178.87:~/obd2-adapter/

# Oder mit Git
cd ~/obd2-adapter
git pull
```

## Verwendung

### TCP/IP (WiFi Adapter - vGate iCar Pro)

```bash
# Standard-Test auf vGate iCar Pro
python3 adapter_validator.py -t tcp -d 192.168.1.123:23

# Mit JSON-Ausgabe
python3 adapter_validator.py -t tcp -d 192.168.1.123:23 -o json

# Bericht speichern
python3 adapter_validator.py -t tcp -d 192.168.1.123:23 --save-report report.json
```

### Serial (Bluetooth/USB TTL)

```bash
# Bluetooth über RFCOMM
python3 adapter_validator.py -t serial -d /dev/rfcomm0 -b 38400

# USB TTL Adapter
python3 adapter_validator.py -t serial -d /dev/ttyUSB0 -b 115200
```

### BLE (Bluetooth Low Energy)

```bash
# BLE Adapter über RFCOMM-Emulation
python3 adapter_validator.py -t ble -d /dev/tty.BLE-ELM-SP
```

## Befehlszeilenoptionen

| Option | Beschreibung | Standard |
|--------|--------------|----------|
| `-t, --type` | Verbindungstyp: serial, tcp, ble | tcp |
| `-d, --device` | Gerät oder Host:Port | 192.168.1.123:23 |
| `-b, --baudrate` | Baudrate (seriell) | 38400 |
| `-o, --output` | Ausgabeformat: text, json, both | text |
| `-v, --verbose` | Detaillierte Log-Ausgabe | aus |
| `--save-report` | Bericht in Datei speichern | - |

## Tests des Validators

Der Validator führt 6 Serien von Tests durch:

### Serie 1: Adapter Identifikation
- **ATZ** - Reset und ELM327-Version prüfen
- **ATI** - Chip-Typ identifizieren (PIC18F25K80, PIC18F47K42)

### Serie 2: CAN-Protokoll
- **ATSP0 + ATDPN** - Auto-Protokoll-Erkennung testen
- Erwartetes Protokoll: 6 (ISO 15765-4 CAN 500K)

### Serie 3: OBD2 PID Tests
- **0100** - Supported PIDs (Bitmaske)
- **010C** - Engine RPM (bei EV = 0, aber Antwort-Struktur muss stimmen)
- **010D** - Vehicle Speed
- **0105** - Coolant Temperature

### Serie 4: Extended CAN Diagnostic
- **ATSH 7E0/7E8** - Extended CAN IDs setzen
- **Mode 03** - Freeze Frame Data
- **Mode 04** - Tester Present
- **Mode 09** - Vehicle Info

### Serie 5: J1939 Extended Address
- **ATSA F1** - Dynamic Address setzen
- **10 00** - UDS DiagnosticSessionControl

### Serie 6: Raw CAN Frame Capture
- **ATCR** - Raw CAN Frames erfassen
- Prüft ob CAN-Bus Sniffing funktioniert

## Ausgabe-Beispiel

```
============================================================
ELM327 ADAPTER VALIDIERUNGSBERICHT
============================================================

Adapter-Informationen:
  Hersteller:   vGate
  Firmware:     2.1
  Chip-Typ:     PIC18F25K80/PIC18F47K42
  Protokoll:    ISO 15765-4 (CAN 500K)
  CAN-Geschw.:  500K

Testergebnisse:
------------------------------------------------------------
  ✅ ATZ - Adapter Reset
     → ELM327 v2.1 erkannt
  ✅ ATI - Chip Identification
     → PIC18F25K80 oder PIC18F47K42 Chip bestätigt
  ✅ ATSP0 + ATDPN - CAN Protocol Detection
     → ISO 15765-4 CAN 500K (Standard für Renault/Dacia)
  ✅ OBD2 PID 0100
     → OBD2 Response korrekt für PID 0100
  ⚠️  Extended CAN Mode 03 - Freeze Frame Data
     → Keine Extended CAN Response für Mode 03 (ECU nicht erreichbar)

------------------------------------------------------------
Score: 90.0%
Kompatibel: JA ✅
============================================================
```

## JSON-Ausgabe

```json
{
  "adapter_info": {
    "vendor": "vGate",
    "firmware_version": "2.1",
    "chip_type": "PIC18F25K80/PIC18F47K42",
    "protocol": "ISO 15765-4 (CAN 500K)",
    "can_speed": "500K"
  },
  "overall_score": 90.0,
  "is_compatible": true,
  "warnings": [],
  "errors": [],
  "tests": [
    {
      "name": "ATZ - Adapter Reset",
      "command": "ATZ",
      "expected": "ELM327 v[0-9.]+",
      "status": "pass",
      "response": "ELM327 v2.1",
      "details": "ELM327 v2.1 erkannt"
    }
  ]
}
```

## Automatisierte Tests im Boot-Prozess

Der Validator kann als systemd Service ausgeführt werden:

```ini
# /etc/systemd/system/elm327-validator.service
[Unit]
Description=ELM327 Adapter Validator
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/obd2-adapter/adapter_validator.py \
    -t tcp \
    -d 192.168.1.123:23 \
    --save-report /var/log/elm327-validator/report.json
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Fehlerbehebung

### "Verbindung fehlgeschlagen"
- IP-Adresse und Port prüfen
- Adapter über Web-Oberfläche neu starten (vGate iCar Pro: http://192.168.1.123)
- Firewall-Regeln prüfen

### "Kein echter ELM327 Adapter erkannt"
- Adapter ist ein GCW05/GCW08 Clone - nicht kompatibel
- Firmware des Adapters aktualisieren

### "Keine Extended CAN Response"
- ECU des Fahrzeugs nicht erreichbar (Zündung aus?)
- Adapter unterstützt keine Extended CAN IDs - inkompatibel

## Wartung

### Neue CAN-IDs hinzufügen
Bearbeiten Sie `pi/adapter_validator.py` und fügen Sie neue IDs zu `DACIA_SPRING_CAN_IDS` hinzu.

### Neue OBD2 PIDs testen
Fügen Sie PIDs zu `TEST_OBD2_PIDS` hinzu.

## Lizenz

GPL-3.0 - Dacia Spring Projekt