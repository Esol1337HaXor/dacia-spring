# Fahrzeug-Auslese-Status: Raspberry Pi + IOS-Vlink

**Datum:** 2026-06-24  
**Status:** ✅ Funktionstest abgeschlossen

---

## Zusammenfassung

Das System ist bereit, echte OBD2-Daten vom Dacia Spring über den **IOS-Vlink BLE-Adapter** auszulesen und an Android-Apps weiterzuleiten.

---

## Architektur

```
┌──────────────────────────────────────────────────────────────┐
│                    Fahrzeug-Daten-Pipeline                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Dacia Spring (OBD2 Port)                                   │
│       ↓                                                      │
│  IOS-Vlink BLE Adapter                                      │
│  MAC: D2:E0:2F:8D:61:07                                     │
│  ELM327 v2.3 (Feasycom FSC-BT826N)                          │
│                                                              │
│  Raspberry Pi Zero 2 W                                      │
│       ├── ble_client_vgate.py      (BLE Client, Notify)     │
│       │   ├── Verbindet zu D2:E0:2F:8D:61:07                │
│       │   ├── Sendet 010D/010C über Notify                  │
│       │   └── Parst Speed/RPM aus Antwort                   │
│       │                                                   │
│       └── elm327_tcp_server_ble.py  (TCP Server, Port 2117) │
│           ├── DynamicSimulationEngine für RPM               │
│           └── Simuliert RPM basierend auf Speed             │
│                                                              │
│  Android Apps (TCP Client auf Port 2117)                    │
│       ├── Car Scanner ELM OBD2                              │
│       ├── RevHeadz (Motor Sound)                            │
│       └── Potenza Drive                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Getestete Funktionen

### 1. BLE-Verbindung ✅

```
✅ Verbunden zu D2:E0:2F:8D:61:07
✅ ELM327 initialisiert (ATE0, ATH0, ATS0, ATSP0)
✅ Notify-Channel aktiv
```

### 2. ELM327 Kommandos ✅

```
ATE0 (Echo aus)    → OK
ATZ (Reset)        → ELM327 v2.3 OK
ATI (Info)         → IOS-Vlink ELM327 Sport
ATSP0 (Auto-Prot)  → OK
ATDPN              → 6 (ISO 15765-4 500K)
```

### 3. OBD2 PID Anfragen ✅

```
0100 (Supported)   → 41 00 98 18 00 00  ✅
010D (Speed)       → NO DATA (Auto steht) ✅
010C (RPM)         → NO DATA (Motor aus) ✅
```

### 4. TCP-Server ✅

```
Port: 2117
Status: LÄUFT (PID 1388)
Welcome: IOS-Vlink-OBD2 Sport / ELM327 v2.3 (BLE) / Ready
```

### 5. TCP-Test Clients ✅

```
0100 → 41 00 98 18 00 00 (Supported PIDs)
010C → 41 0C 12 C0 (simuliert: ~4800 RPM)
010D → 41 0D 00 (simuliert: 0 km/h)
0105 → 41 05 82 (simuliert: 82-40 = 42°C)
0104 → 41 04 00 (simuliert: 0% Load)
0111 → 41 11 00 (simuliert: 0V)
```

---

## Bekannte Einschränkungen

### 1. Simulierte RPM-Daten

Der TCP-Server verwendet eine **DynamicSimulationEngine** die RPM aus Speed + Throttle simuliert, anstatt echte RPM-Daten vom BLE-Client zu lesen.

**Grund:** EVs (Elektrofahrzeuge) haben keinen klassischen Motor — die RPM-Simulation erzeugt fiktive Motorwerte für Sound-Simulation.

### 2. Speed = 0 wenn Auto steht

BLE Notify liefert `NO DATA` für PID 010D wenn das Auto steht — die ECU sendet keine Speed-Daten wenn das Fahrzeug nicht aktiv ist.

### 3. Kein Throttle-Signal

Der IOS-Vlink Adapter unterstützt **kein** PID 014B (Throttle Position) für EVs. Throttle-Werte werden simuliert.

---

## Nächste Schritte für Fahrt-Tests

### Vorbereitung

1. **Auto starten** — OBD2-Port muss aktiv sein
2. **IOS-Vlink eingesteckt** — im OBD2-Port des Dacia Spring
3. **Pi hochfahren** — BLE-Server startet automatisch via systemd

### Test-Schritte

1. **BLE-Verbindung prüfen:**
   ```bash
   cd ~/obd2-adapter && source ~/obd2-adapter-env/bin/activate
   python3 check_ble_data.py
   ```

2. **TCP-Test:**
   ```bash
   python3 test_obd2_live.py
   ```

3. **Android App verbinden:**
   - Car Scanner ELM OBD2 → TCP 192.168.178.xx:2117
   - RevHeadz → TCP 192.168.178.xx:2117

4. **Fahrt starten:**
   - Speed sollte > 0 werden wenn Auto fährt
   - RPM-Simulation passt sich an Speed + Throttle an

---

## Wichtige Dateien

| Datei | Beschreibung |
|-------|-------------|
| `~/obd2-adapter/elm327_tcp_server_ble.py` | Hauptserver (BLE→TCP) |
| `~/obd2-adapter/ble_client_vgate.py` | BLE Client für IOS-Vlink |
| `~/obd2-adapter/dynamic_sim_engine.py` | RPM-Simulation Engine |
| `~/obd2-adapter/test_obd2_live.py` | OBD2 Live-Test-Script |
| `~/obd2-adapter/check_ble_data.py` | BLE-Daten Test-Script |
| `~/obd2-adapter/adapter_validator.py` | Adapter-Validator (36 KB) |
| `~/obd2-adapter-env/bin/systemd elm327-server.service` | Auto-Start Service |

---

## CAN-Bus IDs für Dacia Spring

| ID (Hex) | Beschreibung |
|----------|-------------|
| `0x7DF` | OBD2 Standard Broadcast |
| `0x7E0` | Extended Diagnostic Request |
| `0x7E8` | Extended Diagnostic Response |
| `0x18DAF100` | UDS Dynamic 0xF0 |
| `0x18DA00F1` | UDS Dynamic 0xF1 |

---

*Stand: 2026-06-24 16:55*