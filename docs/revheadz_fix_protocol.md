# RevHeadz Verbindung - Debug Protokoll & Fix Dokumentation

## Problemstellung

RevHeadz (Android Motorsound-Simulation App) konnte sich nicht mit dem Pi Zero 2W ELM327 TCP Server verbinden. Die App zeigte:

```
3.06 No command prompt received, sending initial command
3.06 SEND: AT Z
3.09 RECV: NO DATA
18.07 Timeout waiting for response
18.07 Disconnecting
```

## Ursachen-Analyse

### Ursache 1: Command Normalisierung
**Problem:** RevHeadz sendet Commands **mit Leerzeichen** (`AT Z`, `AT SP 0`, `01 0C`), aber der Server hat nur die Varianten **ohne Leerzeichen** (`ATZ`, `ATSP0`, `010C`) erkannt.

**Code vor dem Fix:**
```python
if line == "ATZ":  # Matcht nur "ATZ", nicht "AT Z"
    response += "ELM327 v1.5a\r\n..."
```

**Code nach dem Fix:**
```python
normalized = line.replace(" ", "").upper()  # "AT Z" → "ATZ"
if normalized == "ATZ":
    response += "ELM327 v1.5a\r\nOK\r\n"
```

### Ursache 2: Fehlender Command Prompt `> `
**Problem:** RevHeadz erwartet nach jeder ELM327 Antwort einen **Command Prompt** `> `. Ohne diesen Prompt wartet die App auf Antwort und timed out nach 15 Sekunden.

**Elm327 Standard:** ELM327 Chips senden `> ` als Command Prompt nach jeder Antwort.

**Code vor dem Fix:**
```python
response += "OK\r\n"  # Kein Prompt
```

**Code nach dem Fix:**
```python
response += "OK\r\n> "  # Prompt am Ende
```

### Ursache 3: Falsche Supported PIDs
**Problem:** `01 00` (Supported PIDs) Antwort enthielt nicht die Bits für PID 0C (RPM) und PID 0D (Speed). RevHeadz prüft diese und bricht ab:

```
RPM or speed not supported, unable to perform simulation.
```

**Code vor dem Fix:**
```python
response += "41 00 E0 00 00 01\r\n"
# Byte2 = 0x00 → Kein PID 0C oder 0D
```

**Code nach dem Fix:**
```python
response += "41 00 98 18 00 00\r\n"
# Byte1 = 0x98 → PID 01, 04, 05
# Byte2 = 0x18 → PID 0C (RPM), PID 0D (Speed)
```

---

## Vollständiges Fix-Protokoll

### Phase 1: Connection & Initialisierung

```
0.00  RevHeadz (Android) Version: 1.38, Build: 69
0.00  Connecting to Wifi OBD-II adapter...
0.74  Connected ← WiFi TCP Verbindung hergestellt ✅

0.75  RECV: PiZeroCar-OBD2        ← Gerätename ✅
0.75  RECV: ELM327 v1.5a (WiFi)   ← Chip Erkennung ✅
0.75  RECV: Ready                 ← Status ✅
0.75  RECV: >                     ← Command Prompt ✅
```

### Phase 2: AT Command Sequenz

```
0.76  SEND: AT Z                  ← Reset
0.77  RECV: AT Z                  ← Echo (echo_enabled=True) ✅
0.77  RECV: ELM327 v1.5a          ← Chip Version ✅
0.77  RECV: OK                    ← Reset erfolgreich ✅
0.77  RECV: >                     ← Prompt nach ATZ ✅

0.77  SEND: AT SP 0              ← Protocol Auto
0.77  RECV: OK                    ← Protocol auf Auto ✅
0.77  RECV: >                     ← Prompt ✅

0.78  SEND: AT AL                ← Auto List (nicht unterstützt)
0.79  RECV: NO DATA               ← Command nicht implementiert ⚠️
0.79  RECV: >                     ← Prompt trotzdem ✅

0.80  SEND: AT E0                ← Echo ausschalten
0.80  RECV: OK                    ← Echo ausgeschaltet ✅
0.80  RECV: >                     ← Prompt ✅

0.81  SEND: AT L0                ← Lines ausschalten (nicht unterstützt)
0.81  RECV: NO DATA               ← Command nicht implementiert ⚠️
0.81  RECV: >                     ← Prompt trotzdem ✅

0.81  SEND: AT S0                ← Spaces ausschalten
0.82  RECV: OK                    ← Spaces ausgeschaltet ✅
0.82  RECV: >                     ← Prompt ✅

0.82  SEND: AT H0                ← Header ausschalten
0.83  RECV: OK                    ← Header ausgeschaltet ✅
0.83  RECV: >                     ← Prompt ✅

0.83  SEND: AT ST 80             ← Send Timeout (nicht unterstützt)
0.84  RECV: NO DATA               ← Command nicht implementiert ⚠️
0.84  RECV: >                     ← Prompt trotzdem ✅
```

### Phase 3: RPM Support Erkennen

```
0.84  SEND: 01 00                ← Supported PIDs
0.84  RECV: 41 00 98 18 00 00   ← PIDs: 01,04,05,0C,0D ✅
                                       Byte1=0x98 (01,04,05)
                                       Byte2=0x18 (0C=RPM✓, 0D=Speed✓)

0.85  SEND: 01 0C                ← RPM lesen
0.85  RECV: 41 0C 0D 7C          ← RPM = (13*256+124)/4 = 863 ✅
                                       0x0D7C = 3452
                                       3452/4 = 863 RPM (idle ± jitter)

0.86-0.90  SEND: 01 0C (mehrfach) ← RPM Samples
0.87-0.90  RECV: 41 0C XX XX     ← RPM ≈ 850 ✅

0.90  1 RPM responses            ← RevHeadz erkennt RPM ✅
```

### Phase 4: Speed Support Erkennen

```
0.94  SEND: 01 0D                ← Speed lesen
0.95  RECV: 41 0D 00             ← Speed = 0 km/h (stehend) ✅
0.95  1 Speed responses          ← RevHeadz erkennt Speed ✅

0.96-1.00  SEND: 01 0D (mehrfach)
0.97-1.00  RECV: 41 0D 00        ← Speed = 0 km/h ✅

1.02  Initialization complete    ← RevHeadz erfolgreich initialisiert! ✅🎉
```

### Phase 5: Betrieb

```
1.73  SEND: AT ST 3a             ← RevHeadz sendet weitere Commands
```

---

## Implementierte Commands

### ✅ Unterstützte AT Commands
| Command | Beschreibung | Response |
|---------|-------------|----------|
| `AT Z` | Reset | `ELM327 v1.5a\r\nOK\r\n> ` |
| `AT I` | Identify | `PiZeroCar-OBD2\r\n> ` |
| `AT E0` | Echo off | `OK\r\n> ` |
| `AT E1` | Echo on | `OK\r\n> ` |
| `AT H0` | Header off | `OK\r\n> ` |
| `AT H1` | Header on | `OK\r\n> ` |
| `AT S0` | Spaces off | `OK\r\n> ` |
| `AT S1` | Spaces on | `OK\r\n> ` |
| `AT SP 0` | Protocol Auto | `OK\r\n> ` |
| `AT A` | Addressing off | `OK\r\n> ` |

### ⚠️ Nicht implementierte (optional) AT Commands
| Command | Response | Kritisch? |
|---------|----------|-----------|
| `AT AL` | `NO DATA\r\n> ` | Nein |
| `AT L0` | `NO DATA\r\n> ` | Nein |
| `AT ST XX` | `NO DATA\r\n> ` | Nein |

### ✅ Unterstützte OBD2 PIDs
| PID | Beschreibung | Response Format |
|-----|-------------|-----------------|
| `01 00` | Supported PIDs | `41 00 98 18 00 00` |
| `01 04` | Engine Load | `41 04 XX` |
| `01 05` | Coolant Temp | `41 05 XX` |
| `01 0C` | Engine RPM | `41 0C XX XX` |
| `01 0D` | Vehicle Speed | `41 0D XX` |

---

## Technische Details

### RPM Berechnung
```python
# Formel: RPM = (A * 256 + B) / 4
# Beispiel: 850 RPM → 850 * 4 = 3400 → 0x0D40

rpm = 850
value = rpm * 4  # 3400
a = (value >> 8) & 0xFF  # 0x0D = 13
b = value & 0xFF          # 0x40 = 64
response = f"41 0C {a:02X} {b:02X}\r\n> "
# Ergebnis: "41 0C 0D 40\r\n> "
```

### Supported PIDs Bitmask
```
Byte1 (PIDs 01-08): 0x98 = 1001 1000
  - Bit 7: PID 01 ✅
  - Bit 4: PID 04 ✅
  - Bit 3: PID 05 ✅

Byte2 (PIDs 09-16): 0x18 = 0001 1000
  - Bit 3: PID 0C (RPM) ✅
  - Bit 4: PID 0D (Speed) ✅
```

### Command Normalisierung
```python
# Alle Whitespaces werden entfernt und zu uppercase konvertiert
"AT Z"     → "ATZ"
"AT SP 0"  → "ATSP0"
"01 0C"    → "010C"
"at z"     → "ATZ"
```

---

## Deploy-Anleitung

### Files auf Pi kopieren
```bash
# Auf dem PC (PowerShell):
scp pi/elm327_tcp_server_standalone.py lsd@192.168.178.87:/home/lsd/obd2-adapter/
```

### Server starten
```bash
# Auf dem Pi:
cd /home/lsd/obd2-adapter
nohup python3 elm327_tcp_server_standalone.py > server.log 2>&1 &
disown
```

### Server Status prüfen
```bash
pgrep -a python3 | grep elm327
# Sollte zeigen: XXXX python3 elm327_tcp_server_standalone.py
```

### RevHeadz Verbindung
- **Typ:** WiFi OBD2 Adapter
- **IP:** `192.168.178.87`
- **Port:** `2117`

---

## Git Commit
```bash
git add pi/elm327_tcp_server_standalone.py
git commit -m "fix: RevHeadz Kompatibilität - Command Normalisierung + Prompt + PIDs"
git push origin main
```

---

## Future Improvements

### Priorität Hoch
- [ ] RPM auf Throttle-Antwort reagieren lassen
- [ ] Speed Simulation (wenn CAN-Daten verfügbar)

### Priorität Mittel
- [ ] `AT ST XX` (Send Timeout) implementieren
- [ ] `AT AL` (Auto List) mit Default-Werten
- [ ] `AT L0` (Lines off) implementieren

### Priorität Niedrig
- [ ] `AT SP XX` (specific protocol) mit CAN 11/500
- [ ] Additional OBD2 PIDs (Coolant Temp, Load, etc.)
- [ ] Multi-client support (mehrere Apps gleichzeitig)

---

## Fazit

**RevHeadz Verbindung erfolgreich!** ✅

Alle kritischen Commands funktionieren:
- ✅ Command Normalisierung (`AT Z` → `ATZ`)
- ✅ Command Prompt `> ` nach jeder Antwort
- ✅ RPM PID 0C mit 850 RPM Idle
- ✅ Speed PID 0D mit 0 km/h
- ✅ Supported PIDs korrekt (Byte2 = 0x18)

Der Server läuft persistent auf dem Pi Zero 2W und steht für RevHeadz zur Verfügung.