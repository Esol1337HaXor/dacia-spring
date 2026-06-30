# CAN-Bus Kommunikation: CanZE + ELM327 Adapter Analyse

**Erstellt:** 2026-06-24  
**Status:** Abgeschlossen ✅  
**Autor:** Cline (AI Assistant) + User

---

## Zusammenfassung

Diese Dokumentation beschreibt die Kommunikation zwischen **CanZE** (der Android-App/Sound-Simulation) und dem **Dacia Spring** über **ELM327-basierte OBD2-Adapter**. Der Fokus liegt auf der technischen Analyse der Kommunikationswege, Chip-Spezifika und Adapter-Validierung.

---

## 1. Kommunikationsarchitektur

### 1.1 Datenfluss

```
┌──────────────────────────────────────────────────────────────┐
│                    Kommunikationsschichten                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Android App (Car Scanner / RevHeadz)                        │
│       ↓ TCP/IP oder BLE                                      │
│  ELM327-Adapter (vGate iCar Pro / IOS-Vlink)                 │
│       ↓ AT-Befehle + OBD2 PIDs                               │
│  CAN-Bus (ISO 15765-4, 500 Kbps)                            │
│       ↓ OBD2 Protocol                                        │
│  Fahrzeug-ECU (Motor, Batterie, Fahrpedal, etc.)             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Protokoll-Stack

| Schicht | Protokoll | Beschreibung |
|---------|-----------|--------------|
| Application | ELM327 Command Protocol | AT-Befehle + OBD2 PIDs |
| Transport | TCP/IP (Port 2117) oder BLE GATT | WiFi oder Bluetooth Low Energy |
| Network | ISO 15765-4 (CAN 11/500) | OBD2 Standard CAN |
| Physical | OBD2 Stecker (16-Pin) | Physikalische Verbindung |

---

## 2. ELM327 Chip Analyse

### 2.1 Unterstützte Chips

| Chip | Hersteller | Features | CAN Support |
|------|-----------|----------|-------------|
| **PIC18F25K80** | Microchip | Classic ELM327 | CAN 2.0 A/B (500K) |
| **PIC18F47K42** | Microchip | Erweitert + Extended IDs | CAN 2.0 A/B (1 Mbps) |

### 2.2 PIC18F25K80 Spezifikationen

- **Mikrocontroller:** 8-Bit PIC mit 28-Pin Package
- **CAN-Controller:** Integrated CAN 2.0 Module
- **Baudraten:** Bis 1 Mbps (CAN FD Ready)
- **Memory:** 128 KB Flash, 4 KB RAM
- **OBD2 Support:** Full OBD2, SAE J1850, ISO 9141, KWP2000
- **UDS Support:** ISO 14229 (Extended CAN IDs 29-bit)

### 2.3 PIC18F47K42 Spezifikationen

- **Erweiterte Features:** Plus Extended CAN Address Support
- **Baudraten:** Bis 1 Mbps mit Dynamic Address (J1939)
- **UUDS Support:** Full UDS over CAN (ISO 14229-1)
- **J1939:** Dynamic Address Assignment

---

## 3. CAN-Bus IDs für Dacia Spring

### 3.1 Standard OBD2 IDs

| ID (Hex) | Richtung | Beschreibung |
|----------|----------|--------------|
| `0x7DF` | Broadcast | OBD2 Standard Broadcast |
| `0x7E0` | Request | Extended Diagnostic Request |
| `0x7E8` | Response | Extended Diagnostic Response |

### 3.2 Erweiterte CAN IDs (29-bit)

| ID (Hex) | Richtung | Beschreibung |
|----------|----------|--------------|
| `0x18DAF100` | Request | UDS Dynamic 0xF0 Request |
| `0x18DA00F1` | Response | UDS Dynamic 0xF1 Response |
| `0x18DA` | General | J1939 Extended Address Space |

### 3.3 Fahrzeug-spezifische IDs

| ID (Hex) | Component | Beschreibung |
|----------|-----------|--------------|
| `0x0B0` | KOM/Motor | Motor-Status |
| `0x2B8` | LBC | Batteriemanagement |

---

## 4. BLE-Kommunikation (IOS-Vlink / vGate iCar Pro)

### 4.1 BLE-GATT-Profile

Der IOS-Vlink Adapter verwendet folgende GATT-Services:

| Service UUID | Characteristic UUID | Properties | Beschreibung |
|-------------|---------------------|------------|--------------|
| `e7810a71-73ae-499d-8c15-faa9aef0c3f2` | `bef8d6c9-9c21-4c9e-b632-bd58c1009f9f` | read, write, notify, indicate | Haupt-ELM327 Kanal |
| `0000180a-0000-1000-8000-00805f9b34fb` | `00002a28` | read | Software Revision |
| `0000180a-0000-1000-8000-00805f9b34fb` | `00002a29` | read | Manufacturer Name |
| `0000180a-0000-1000-8000-00805f9b34fb` | `00002a25` | read | Serial Number |
| `0000180a-0000-1000-8000-00805f9b34fb` | `00002a24` | read | Model Number |
| `0000180a-0000-1000-8000-00805f9b34fb` | `00002a27` | read | Hardware Revision |

### 4.2 Gerät-Informationen (IOS-Vlink)

| Eigenschaft | Wert |
|------------|------|
| **Gerät** | IOS-Vlink OBD2 Adapter |
| **Hersteller** | Feasycom (FSC-BT826N) |
| **ELM327 Version** | v2.3 |
| **Software** | v5.4.2 |
| **MAC Adresse** | D2:E0:2F:8D:61:07 |
| **Hardware Revision** | 1.2 |
| **Serial Number** | 13E02F8D6107 |

### 4.3 BLE-Kommunikationsprotokoll

**WICHTIG:** ELM327-Antworten kommen **NICHT** über `read_gatt_char()`, sondern über **BLE Notify/Indicate**.

```python
# Korrekte BLE-Kommunikation
async with BleakClient("D2:E0:2F:8D:61:07") as client:
    # 1. Notify-Handler einrichten
    def notify_handler(sender, data):
        text = data.decode("utf-8")  # ELM327 Antwort!
        
    await client.start_notify(
        "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f",
        notify_handler
    )
    
    # 2. Kommando SENDEN (write)
    await client.write_gatt_char(
        "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f",
        b"010D\r"  # Vehicle Speed PID
    )
    
    # 3. Antwort kommt ÜBER NOTIFY
    # Beispiel: "41 0D 14\r\r>"
```

---

## 5. ELM327 AT-Befehle

### 5.1 Wichtige AT-Befehle

| Befehl | Beschreibung | Antwort |
|--------|-------------|---------|
| `ATZ` | Adapter Reset | `ELM327 v2.3\r\nOK\r\n> ` |
| `ATI` | Adapter Info | `IOS-Vlink ELM327 Sport\r\n> ` |
| `ATE0` | Echo aus | `OK\r\n> ` |
| `ATE1` | Echo an | `OK\r\n> ` |
| `ATH0` | Header aus | `OK\r\n> ` |
| `ATH1` | Header an | `OK\r\n> ` |
| `ATS0` | Spaces aus | `OK\r\n> ` |
| `ATS1` | Spaces an | `OK\r\n> ` |
| `ATSP0` | Auto-Protocol | `OK\r\n> ` |
| `ATDPN` | Current Protocol Number | `6` = ISO 15765-4 500K |

### 5.2 CAN-Protokoll-Nummern

| Nummer | Protokoll | Beschreibung |
|--------|-----------|--------------|
| 1 | SAE J1850 PWM | Ford/GM |
| 2 | SAE J1850 VPW | GM |
| 3 | ISO 9141-2 | Audi/VW (älter) |
| 4 | ISO 14230-4 KWP (5 baud init) | BMW (älter) |
| 5 | ISO 14230-4 KWP fast | BMW |
| **6** | **ISO 15765-4 (CAN 500K)** | **Renault/Dacia Standard** |
| 7 | ISO 15765-4 (CAN 250K) | Andere Fahrzeuge |
| 8 | SAE J1939 (CAN 250K) | LKW |
| 9 | SAE J1939 (CAN 500K) | LKW |

---

## 6. OBD2 PID Tests

### 6.1 Getestete PIDs

| PID | Befehl | Bedeutung | Erwartete Antwort |
|-----|--------|-----------|-------------------|
| 0x00 | `0100` | Supported PIDs | `41 00 98 18 00 00` |
| 0x04 | `0104` | Engine Load | `41 04 XX` |
| 0x05 | `0105` | Coolant Temp | `41 05 XX` |
| 0x0C | `010C` | Engine RPM | `41 0C XX XX` |
| 0x0D | `010D` | Vehicle Speed | `41 0D XX` |

### 6.2 OBD2 Response-Format

```
Befehl: 0100\r
Antwort: 41 00 98 18 00 00\r\n> 

41 = Response für PID 01
00 = Supported PIDs Bitmask (Bits 00-31)
98 = Bit 3,5,7 gesetzt (Supported PIDs 20-3F)
```

### 6.3 RPM-Berechnung

```
Antwort: 41 0C XX XX
XX = High Byte, XX = Low Byte

RPM = (256 * A + B) / 4

Beispiel: 41 0C 0D 48
RPM = (256 * 13 + 72) / 4 = 850 RPM
```

### 6.4 Speed-Berechnung

```
Antwort: 41 0D XX
XX = Speed in km/h

Beispiel: 41 0D 14
Speed = 0x14 = 20 km/h
```

---

## 7. Adapter-Validierung

### 7.1 Validator-Script

**Datei:** `pi/adapter_validator.py`  
**Beschreibung:** Überprüft ob ein angeschlossener ELM327-Adapter die erforderlichen Features für die Kommunikation mit dem Dacia Spring unterstützt.

**Verbindungsmethoden:**
- Serial (Bluetooth/USB TTL)
- TCP/IP (WiFi Adapter wie vGate iCar Pro)
- BLE (Bluetooth Low Energy)

### 7.2 Test-Serien

| Serie | Test | Beschreibung |
|-------|------|--------------|
| 1 | ATZ + ATI | Adapter Identifikation |
| 2 | ATSP0 + ATDPN | CAN-Protokoll-Erkennung |
| 3 | OBD2 PIDs | Standard OBD2 PID-Tests |
| 4 | Extended CAN | UDS Diagnostic Tests (7E0/7E8) |
| 5 | J1939 Extended | Dynamic Address Support |
| 6 | Raw CAN Capture | CAN-Bus Sniffing Support |

### 7.3 Validator-Ergebnis (Echo-Server Test)

```
ATZ - Adapter Reset: PASS (ELM327 v2.3 erkannt)
ATI - Chip Identification: WARN (kein PIC18F explizit)
ATSP0 + ATDPN - CAN Protocol: PASS (6 = ISO 15765-4 500K)
OBD2 PID 0100: PASS (41 00 98 18 00 00)
OBD2 PID 010C: PASS (simuliert)
OBD2 PID 010D: PASS (simuliert)
Extended CAN Mode 03: WARN (ECU nicht erreichbar - normales Verhalten ohne Fahrzeug)
Extended CAN Mode 04: WARN
Extended CAN Mode 09: WARN
J1939 Extended Address: WARN
Raw CAN Frame Capture: WARN
```

### 7.4 Bekannte gute Adapter

| Adapter | Chip | Status |
|---------|------|--------|
| vGate iCar Pro | PIC18F47K42 BLE | ✅ Empfohlen |
| OBDLink EX | PIC18F25K80 | ✅ Empfohlen |
| OBDLink UX | PIC18F25K80 | ✅ Empfohlen |
| KONWEI KW902 | PIC18F25K80 | ✅ Empfohlen |
| GCW05/GCW08 Clone | unbekannt | ❌ Nicht kompatibel |

---

## 8. Pi-System-Architektur

### 8.1 Datenfluss vom Adapter zur Android-App

```
┌────────────────────────────────────────────────────────────┐
│                    Pi System Architecture                    │
├────────────────────────────────────────────────────────────┤
│                                                              │
│  vGate iCar Pro (BLE)                                       │
│       ↓ BLE 4.0 (GATT Notify)                               │
│  Raspberry Pi Zero 2 W                                      │
│       ├── ble_client_vgate.py    (BLE Client)               │
│       │   ├── VgateBLEClient class                           │
│       │   └── Notify Handler für Speed/PID                  │
│       │                                                   │
│       ├── rpm_simulation_engine.py  (RPM Engine)            │
│       │   ├── Speed → RPM Umrechnung                        │
│       │   └── Gear Simulation (0-6)                         │
│       │                                                   │
│       ├── obd2_data_pipeline.py     (Data Pipeline)         │
│       │   ├── BLE Speed + Throttle                         │
│       │   └── → Simulated RPM + Speed                       │
│       │                                                   │
│       └── elm327_tcp_server_ble.py  (TCP Server)            │
│           ├── Port 2117 (ELM327-Emulation)                  │
│           └── → TCP Clients (Android Apps)                  │
│                                                              │
│  Android Apps (over WiFi)                                   │
│       ├── Car Scanner ELM OBD2                              │
│       ├── RevHeadz (Motor Sound)                            │
│       └── Potenza Drive                                     │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

### 8.2 Wichtige Dateien

| Datei | Beschreibung |
|-------|-------------|
| `ble_client_vgate.py` | BLE Client für vGate iCar Pro |
| `rpm_simulation_engine.py` | RPM-Simulation basierend auf Speed |
| `obd2_data_pipeline.py` | Daten-Pipeline BLE → RPM → TCP |
| `elm327_tcp_server_ble.py` | TCP Server mit ELM327-Emulation |
| `dynamic_sim_engine.py` | Erweiterte RPM-Simulation |
| `scan_vlink_services.py` | BLE Service Scanner (Debug) |
| `test_vlink_final.py` | Finaler Test-Skript |

---

## 9. Bekannte Probleme & Lösungen

### 9.1 BLE-Verbindung instabil

**Problem:** BLE-Timeouts oder verlorene Pakete  
**Lösung:** Externe BLE-Antenne am Pi, Adapter nah am OBD2-Port platzieren

### 9.2 TCP-Response-Erkennung

**Problem:** ELM327-Prompt `>` wird nicht korrekt entfernt → leere Responses  
**Lösung:** `response.split('>', 1)[0]` statt `[-1]` (Debug 2026-06-24 behoben)

### 9.3 Adapter-Kompatibilität

**Problem:** Cloned-Adapter erkennen nicht alle CAN-Protokolle  
**Lösung:** Adapter-Validator verwenden (`adapter_validator.py`)

---

## 10. Nächste Schritte

- [ ] Fahrt-Test: Echte Speed-Daten mit fahrendem Fahrzeug testen
- [ ] Alle OBD2 PIDs testen (0100, 0104, 0105, 0111)
- [ ] Android App Integration (Car Scanner, RevHeadz)
- [ ] Auto-Start beim Pi Boot
- [ ] EV-spezifische PIDs suchen (Motor-Drehzahl, Battery, Power)

---

## 11. Entscheidungen-Protokoll

### 2026-06-24: BLE Notify statt Read

**PROBLEM:** ELM327-Antworten kommen nicht über `read_gatt_char()` an  
**ENTSCHIEDUNG:** BLE Notify/Indicate verwenden  
**GRUND:** IOS-Vlink Adapter senden Antworten nur über Notify  
**STATUS:** ✅ Behoben

### 2026-06-24: TCP Prompt-Strip Bug

**PROBLEM:** Alle TCP-Responses waren leer  
**ENTSCHIEDUNG:** `response.split('>', 1)[0]` statt `[-1]`  
**GRUND:** Prompt `>` steht AM ENDE der Antwort, alles DAVOR ist Inhalt  
**STATUS:** ✅ Behoben

### 2026-06-24: TCP-Timeout-Einstellung

**PROBLEM:** Socket-Timeout war nach Willkommens-Lesen nicht zurückgesetzt  
**ENTSCHIEDUNG:** `self.connection.settimeout(self.timeout)` nach connect  
**GRUND:** 0.3s Timeout für Willkommens-Lesen muss auf 5.0s zurückgesetzt werden  
**STATUS:** ✅ Behoben

---

*Diese Dokumentation wird bei neuen Erkenntnissen aktualisiert.*