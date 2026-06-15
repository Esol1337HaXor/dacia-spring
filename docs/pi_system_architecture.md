# Pi Zero 2W System Architektur - OBD2 ELM327 Emulation

## Überblick

Dieses Dokument beschreibt die auf dem Raspberry Pi Zero 2W laufenden Dienste, deren Funktionen und wie der ELM327 TCP Server funktioniert um RevHeadz (und andere OBD2-Apps) mit simulierten OBD2-Daten zu versorgen.

---

## System-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│                  Raspberry Pi Zero 2 W                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           ELM327 TCP Server (Hauptdienst)             │  │
│  │  pi/elm327_tcp_server_standalone.py                   │  │
│  │  Port: 2117                                           │  │
│  │  PID: 1548 (nohup + disown)                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↑                                  │
│                           │ TCP/IP                          │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Android App (RevHeadz)                   │  │
│  │  WiFi TCP → 192.168.178.87:2117                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Weitere Dienste (aktuell inaktiv/nicht verwendet):         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  bluetooth_spp_server.py                              │  │
│  │  Bluetooth RFCOMM Emulation (Channel 1)               │  │
│  │  Status: Nicht im Einsatz (WiFi TCP bevorzugt)        │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  elm327_ble_emulator.py                               │  │
│  │  BLE GATT Server (iCar Pro Style)                     │  │
│  │  Status: Nicht im Einsatz (bleak braucht root)        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Laufende Dienste

### 1. ELM327 TCP Server (HAUPTDIENST) ✅ AKTIV

**Datei:** `pi/elm327_tcp_server_standalone.py`

**Beschreibung:**
Der ELM327 TCP Server emuliert einen ELM327 OBD2-Adapter über TCP/IP. Er lauscht auf Port 2117 und beantwortet ELM327-Commandos wie ein echter OBD2-Adapter.

**Start-Befehl:**
```bash
cd /home/lsd/obd2-adapter
nohup python3 elm327_tcp_server_standalone.py > server.log 2>&1 &
disown
```

**Prozess-Status:**
```bash
pgrep -a python3 | grep elm327
# Ausgabe: 1548 python3 elm327_tcp_server_standalone.py
```

**Netzwerk:**
- **Port:** 2117 (Standard ELM327 TCP Port)
- **IP:** 192.168.178.87 (WiFi IP des Pi)
- **Protocol:** TCP/IP über WiFi

**Funktionsweise:**
```
1. Server startet und lauscht auf Port 2117
2. Client (RevHeadz) verbindet sich per TCP
3. Server sendet Welcome Message:
   - "PiZeroCar-OBD2\r\nELM327 v1.5a (WiFi)\r\nReady\r\n> "
4. Client sendet ELM327 Commands:
   - AT Z (Reset)
   - AT SP 0 (Protocol Auto)
   - 01 00 (Supported PIDs)
   - 01 0C (RPM lesen)
5. Server verarbeitet Commands:
   - Normalisiert: "AT Z" → "ATZ", "01 0C" → "010C"
   - Sucht matchende Command-Logik
   - Sendet Antwort + "> " Prompt zurück
6. Cycle wiederholt sich für alle Commands
```

**Unterstützte Commands:**

| Kategorie | Commands | Beschreibung |
|-----------|----------|-------------|
| AT Commands | AT Z, ATI, AT E0, AT E1, AT H0, AT H1, AT S0, AT S1, AT SP0, AT A | ELM327 Controller Commands |
| OBD2 PIDs | 0100, 0104, 0105, 010C, 010D, 010E, 0101, 0111, 0114, 0120 | OBD2 PID Requests |
| Nicht unterstützt | AT AL, AT L0, AT ST XX | Werden mit "NO DATA" beantwortet |

**RPM Simulation:**
```python
# Basis-RPM: 850 (Motor idle)
# Jitter: ±20 RPM (natürliche Schwankung)
# Formel: RPM * 4 = (A << 8) | B

rpm = 850 + random.randint(-20, 20)  # 830-870
value = rpm * 4  # 3320-3480
a = (value >> 8) & 0xFF  # High Byte
b = value & 0xFF          # Low Byte
response = f"41 0C {a:02X} {b:02X}"
```

**Supported PIDs (01 00 Antwort):**
```
41 00 98 18 00 00

Byte1 (0x98 = 1001 1000): PIDs 01-08
  - Bit 7: PID 01 (Status) ✓
  - Bit 4: PID 04 (Engine Load) ✓
  - Bit 3: PID 05 (Coolant Temp) ✓

Byte2 (0x18 = 0001 1000): PIDs 09-16
  - Bit 3: PID 0C (Engine RPM) ✓
  - Bit 4: PID 0D (Vehicle Speed) ✓
```

---

### 2. Bluetooth SPP Server (INAKTIV) ⚠️

**Datei:** `pi/bt_spp_server.py`

**Beschreibung:**
Emuliert einen Bluetooth SPP (Serial Port Profile) Server der einen ELM327 über RFCOMM Channel 1 bereitstellt. Wurde getestet, läuft aber nicht stabil.

**Status:** Nicht im Einsatz - WiFi TCP wird bevorzugt.

**Warum nicht verwendet:**
- Bluetooth Pairing Probleme mit einigen Android Devices
- RFCOMM Verbindungen wurden vom Pi abgelehnt (BlueZ Filter)
- Kürereich Reichweite als WiFi

**Start-Befehl (inaktiv):**
```bash
cd /home/lsd/obd2-adapter
sudo python3 bt_spp_server.py
```

---

### 3. BLE Emulator (INAKTIV) ⚠️

**Datei:** `pi/elm327_ble_emulator.py`

**Beschreibung:**
Emuliert einen ELM327 über BLE GATT Service (UUID 0000ffe1-0000-1000-8000-00805f9b34fb) im Stil eines Vgate iCar Pro.

**Status:** Nicht im Einsatz - braucht root Privilegien und BLE Advertising Support.

**Warum nicht verwendet:**
- `bleak.BleakServer` benötigt root Privilegien
- Pi Zero 2W BLE Controller unterstützt keinen Server-Mode gut
- Komplexer als notwendig

**Unterstützte UUIDs:**
- **Service:** 0000ffe1-0000-1000-8000-00805f9b34fb
- **Characteristic:** 0000ffe1-0000-1000-8000-00805f9b34fb

---

## Server Architektur im Detail

### ELM327Engine Klasse

Die `ELM327Engine` Klasse ist das Herzstück des TCP Servers. Sie verarbeitet alle ELM327 Commands.

```python
class ELM327Engine:
    """ELM327 command processor for OBD2 emulation."""
    
    def __init__(self):
        self.echo = True           # Command Echo aktiv
        self.idle_rpm = 850        # Basis-Drehzahl

    def process(self, command):
        """Verarbeitet einen ELM327 Command."""
        line = command.strip()
        
        # NORMALISIERUNG (Schlüssel für RevHeadz Kompatibilität!)
        normalized = line.replace(" ", "").upper()
        # "AT Z" → "ATZ"
        # "01 0C" → "010C"
        # "at z" → "ATZ"
        
        # ECHO (wenn aktiv)
        if self.echo:
            response = line + "\r"
        
        # COMMAND VERARBEITUNG
        if normalized == "ATZ":
            response += "ELM327 v1.5a\r\nOK\r\n> "
        elif normalized == "010C":
            rpm = self.idle_rpm + random.randint(-20, 20)
            response += f"41 0C {rpm*4>>8:02X} {rpm*4&0xFF:02X}\r\n> "
        # ... weitere Commands
```

### TCPHandler Klasse

Die `TCPHandler` Klasse verwaltet jede einzelne Client-Verbindung.

```python
class TCPHandler:
    def __init__(self, client_socket, addr):
        self.socket = client_socket
        self.addr = addr
        self.engine = ELM327Engine()

    def handle(self):
        # 1. Welcome Message senden
        welcome = "PiZeroCar-OBD2\r\nELM327 v1.5a (WiFi)\r\nReady\r\n> "
        self.socket.sendall(welcome.encode())
        
        # 2. Command-Response Loop
        buffer = ""
        while True:
            data = self.socket.recv(4096)
            if not data:
                break
            
            # Buffer decode und Commands aufteilen
            buffer += data.decode('utf-8', errors='ignore')
            
            # Auf \r oder \n aufteilen
            while '\r' in buffer:
                line, buffer = buffer.split('\r', 1)
                line = line.strip()
                if line:
                    response = self.engine.process(line)
                    self.socket.sendall(response.encode())
```

### Server Start Prozess

```python
def main():
    # 1. Logging setup
    logging.basicConfig(level=logging.INFO, ...)
    
    # 2. IP Adresse ermitteln
    result = subprocess.run(["hostname", "-I"], ...)
    ip = result.stdout.strip().split()[0]
    
    # 3. TCP Socket erstellen
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", TCP_PORT))  # Port 2117
    server.listen(5)  # Max 5 wartende Verbindungen
    
    # 4. Verbindungsschleife
    while True:
        client_sock, addr = server.accept()
        # Neue Verbindung → Thread erstellen
        t = threading.Thread(target=TCPHandler(client_sock, addr).handle)
        t.start()
```

---

## Command Flow Diagramm

```
RevHeadz App                TCP Server                ELM327Engine
    |                            |                          |
    |-- TCP Connect (2117) ----->|                          |
    |                            |                          |
    |<-- Welcome Message --------|                          |
    |   "PiZeroCar-OBD2\r\n"    |                          |
    |   "ELM327 v1.5a\r\n"      |                          |
    |   "Ready\r\n> "           |                          |
    |                            |                          |
    |-- AT Z ------------------>|                          |
    |                            |-- process("AT Z") ------>|
    |                            |   normalized = "ATZ"     |
    |                            |   response = "ATZ\r\n"   |
    |                            |   response += "ELM327... |
    |                            |   response += "OK\r\n> " |
    |<-- AT Z\r\nELM327... ------|                          |
    |    OK\r\n>                 |                          |
    |                            |                          |
    |-- AT SP 0 --------------->|                          |
    |                            |-- process("AT SP 0") ---->|
    |                            |   normalized = "ATSP0"   |
    |                            |   response = "AT SP 0\r"|
    |                            |   response += "OK\r\n> "|
    |<-- AT SP 0\r\nOK\r\n> -----|                          |
    |                            |                          |
    |-- 01 00 ----------------->|                          |
    |                            |-- process("01 00") ------>|
    |                            |   normalized = "0100"    |
    |                            |   response = "01 00\r"   |
    |                            |   response += "41 00... |
    |<-- 01 00\r\n41 00... ------|                          |
    |    >                       |                          |
    |                            |                          |
    |-- 01 0C ----------------->|                          |
    |                            |-- process("01 0C") ------>|
    |                            |   normalized = "010C"    |
    |                            |   rpm = 850 + jitter     |
    |                            |   response = "01 0C\r"   |
    |                            |   response += "41 0C..." |
    |<-- 01 0C\r\n41 0C XX XX ---|                          |
    |    \r\n>                   |                          |
    |                            |                          |
```

---

## Network Configuration

### WiFi Setup
```bash
# Pi WiFi IP
hostname -I
# Ausgabe: 192.168.178.87

# WiFi Interface
ip addr show wlan0
```

### Port Prüfung
```bash
# Prüfen ob Port 2117 offen ist
ss -tlnp | grep 2117
# oder
netstat -tlnp | grep 2117

# Sollte zeigen:
# LISTEN 0  128  0.0.0.0:2117  0.0.0.0:*  users:(("python3",pid=1548,fd=3))
```

### Firewall (falls aktiv)
```bash
# Standard Pi Zero hat keine Firewall aktiv
# Falls notwendig:
sudo ufw allow 2117/tcp
sudo ufw enable
```

---

## Logging und Debugging

### Server Log
```bash
# Log Datei anzeigen
cat /home/lsd/obd2-adapter/server.log

# Live Log folgen
tail -f /home/lsd/obd2-adapter/server.log
```

### Typische Log Ausgabe
```
2026-06-16 01:33:34,872 [INFO] ==================================================
2026-06-16 01:33:34,873 [INFO] ELM327 WiFi TCP Server (STANDALONE)
2026-06-16 01:33:34,873 [INFO] ==================================================
2026-06-16 01:33:34,873 [INFO] Port: 2117
2026-06-16 01:33:34,895 [INFO] WiFi IP: 192.168.178.87
2026-06-16 01:33:34,895 [INFO] ==================================================
2026-06-16 01:33:34,895 [INFO] WAITING FOR CONNECTIONS...
2026-06-16 01:33:34,896 [INFO] Connect to: 192.168.178.87:2117
2026-06-16 01:33:34,896 [INFO] ==================================================
2026-06-16 01:35:00,123 [INFO] Connected from ('192.168.178.100', 12345)
2026-06-16 01:35:15,456 [INFO] Disconnected ('192.168.178.100', 12345)
```

### RevHeadz Debug auf Android
In RevHeadz kann das Debug-Logging aktiviert werden:
- Einstellungen → Debug Mode
- Zeigt alle SEND/RECV Commands in der App-Anzeige

---

## Service Management

### Server neustarten
```bash
# Alten Server stoppen
pkill -f elm327_tcp_server

# Neuen Server starten
cd /home/lsd/obd2-adapter
nohup python3 elm327_tcp_server_standalone.py > server.log 2>&1 &
disown
```

### Server Status prüfen
```bash
# Prozess prüfen
pgrep -a python3 | grep elm327

# Port prüfen
ss -tlnp | grep 2117

# Log prüfen
tail -20 server.log
```

### Auto-Start bei Boot (optional)
```bash
# /etc/rc.local bearbeiten
sudo nano /etc/rc.local

# Vor "exit 0" hinzufügen:
cd /home/lsd/obd2-adapter
nohup python3 elm327_tcp_server_standalone.py > server.log 2>&1 &

# Oder systemd Service erstellen:
sudo nano /etc/systemd/system/elm327-server.service

[Unit]
Description=ELM327 TCP Server for OBD2 Emulation
After=network.target

[Service]
Type=simple
User=lsd
WorkingDirectory=/home/lsd/obd2-adapter
ExecStart=/usr/bin/python3 /home/lsd/obd2-adapter/elm327_tcp_server_standalone.py
Restart=always

[Install]
WantedBy=multi-user.target

# Service aktivieren
sudo systemctl daemon-reload
sudo systemctl enable elm327-server
sudo systemctl start elm327-server
```

---

## Troubleshooting

### Problem: RevHeadz kann sich nicht verbinden

**Ursache:** Server läuft nicht oder falsche IP/Port

**Lösung:**
```bash
# 1. Prüfen ob Server läuft
pgrep -a python3 | grep elm327

# 2. Prüfen ob Port offen ist
ss -tlnp | grep 2117

# 3. Server neu starten
pkill -f elm327
cd /home/lsd/obd2-adapter
nohup python3 elm327_tcp_server_standalone.py > server.log 2>&1 &
disown
```

### Problem: "Timeout waiting for response"

**Ursache:** Server antwortet nicht oder Prompt fehlt

**Lösung:**
- Server Log prüfen: `cat server.log`
- Sicherstellen dass alle Responses mit `> ` enden
- Command Normalisierung funktioniert korrekt

### Problem: RPM wird nicht angezeigt

**Ursache:** PID 0C nicht in Supported Pids oder falsche Berechnung

**Lösung:**
```python
# 01 00 Antwort muss Byte2 = 0x18 haben
response += "41 00 98 18 00 00\r\n> "
#            ↑    ↑
#           01,04,05  0C(RPM),0D(Speed)

# RPM Berechnung: value = rpm * 4
rpm = 850
value = 850 * 4 = 3400 = 0x0D40
response = f"41 0C {0x0D:02X} {0x40:02X}"
# Ergebnis: "41 0C 0D 40"
```

### Problem: SSH hängt sich auf

**Ursache:** SSH Connection Timeout oder zu viele Sessions

**Lösung:**
```bash
# Auf dem Pi: Aktive SSH Sessions prüfen
who
w

# Alte Sessions beenden
pkill -u lsd -t pts/0  # pts/0 durch passende Nummer ersetzen
```

---

## Sicherheitsaspekte

### Aktuelle Sicherheitslage

⚠️ **Der Pi Zero 2W ist NICHT für den Einsatz in öffentlichen/netzwerk-umkonfigurierten Netzwerken geeignet!**

**Risiken:**
- Passwort-basierte SSH Authentifizierung
- Keine Firewall konfiguriert
- TCP Port 2117 ist im lokalen Netzwerk offen
- Keine VPN oder Zugangskontrolle

**Empfohlene Verbesserungen:**
1. SSH Key Authentifizierung einrichten (bereits getan ✅)
2. UFW Firewall konfigurieren
3. Fail2Ban installieren
4. Regelmäßige Updates durchführen

---

## Dateistruktur auf dem Pi

```
/home/lsd/obd2-adapter/
├── elm327_tcp_server_standalone.py  ← Hauptserver (AKTIV)
├── elm327_tcp_server.py              ← Original Server (inaktiv)
├── elm327_ble_emulator.py            ← BLE Emulator (inaktiv)
├── bt_spp_server.py                  ← Bluetooth SPP (inaktiv)
├── server.log                        ← Server Log
├── start_bt.sh                       ← Bluetooth Start Script
├── check_bt.sh                       ← Bluetooth Status
├── debug_bt.sh                       ← Bluetooth Debug
├── fix_pairing.sh                    ← Pairing Fix Script
├── restart_bt.sh                     ← Bluetooth Neustart
├── setup_bt.sh                       ← Bluetooth Setup
├── fix_agent.sh                      ← Agent Fix Script
├── test_elm327_protocol.py           ← ELM327 Test Script
├── test_tcp_connection.py            ← TCP Test Script
└── README.md                         ← Dokumentation
```

---

## Zusammenfassung

### Aktuelle Dienst-Status
| Dienst | Status | Port/Channel | Beschreibung |
|--------|--------|--------------|-------------|
| elm327_tcp_server_standalone.py | ✅ AKTIV | TCP 2117 | ELM327 OBD2 Emulation über WiFi |
| bt_spp_server.py | ⚠️ Inaktiv | RFCOMM 1 | Bluetooth SPP (nicht stabil) |
| elm327_ble_emulator.py | ⚠️ Inaktiv | BLE GATT | BLE Emulator (braucht root) |

### Wichtige Fakten
- **Pi IP:** 192.168.178.87
- **TCP Port:** 2117
- **RPM Basis:** 850 (idle, ±20 Jitter)
- **Supported PIDs:** 01, 04, 05, 0C (RPM), 0D (Speed)
- **Command Format:** Alle Commands werden normalisiert (Spaces entfernt, uppercase)
- **Prompt Format:** Alle Antworten enden mit `> `

### RevHeadz Verbindung
```
Android ← WiFi TCP ← Pi Zero 2W ← ELM327 Server
(192.168.178.X)    (2117)    (192.168.178.87)
```

**Funktioniert:**
- ✅ AT Commands (Z, E0, S0, H0, SP0, etc.)
- ✅ 01 00 (Supported PIDs)
- ✅ 01 0C (RPM)
- ✅ 01 0D (Speed)
- ✅ Command Normalisierung
- ✅ Command Prompt nach jeder Antwort