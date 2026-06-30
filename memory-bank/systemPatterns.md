# Systemarchitektur: OBD2 EV Adapter

## Gesamtarchitektur (AKTUALISIERT - BLE-basiert)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Dacia Spring EV                          │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  CAN-Bus    │    │  Motor/      │    │  Brems-/       │   │
│  │  System     │    │  Antriebs-   │    │  Fahrwerk-     │   │
│  │  (500kbps)  │    │  System      │    │  System        │   │
│  └──────┬──────┘    └──────┬───────┘    └───────┬────────┘   │
│         │                  │                     │            │
│         └──────────────────┴─────────────────────┘            │
│                            │                                   │
└────────────────────────────┼───────────────────────────────────┘
                             │ OBD2 Port (Pin 4,5,16)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Vgate iCar Pro BLE                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ELM327 Chip (OBD2 ↔ BLE Bridge)                         │    │
│  │                                                          │    │
│  │  BLE Socket               OBD2 Protocol                  │    │
│  │  (Android/Pi)    ◀▶       AT-Befehle / PIDs              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │ BLE (Bluetooth Low Energy 4.0)     │
└────────────────────────────┼───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Raspberry Pi Zero 2 W                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                          │    │
│  │  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │    │
│  │  │ BLE OBD2     │──▶│ RPM-Simulat. │──▶│ ELM327      │ │    │
│  │  │ Client       │   │              │   │ Emulator    │ │    │
│  │  │ (Vgate      │   └──────────────┘   │ (WLAN/BT)   │ │    │
│  │  │  Anbindung)  │                      └──────┬──────┘ │    │
│  │                        ▲                       │        │    │
│  │                        └───────────────────────┘        │    │
│  │                                                          │    │
│  │  ┌──────────────┐   ┌───────────────────────────────┐   │    │
│  │  │ Fahrzeug-    │   │  Bluetooth/WLAN Server        │   │    │
│  │  │ daten-       │   │  (ELM327 Emulation für        │   │    │
│  │  │ preprocessing│   │  Sound-Apps)                  │   │    │
│  │  └──────────────┘   └───────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            │                                     │
│  Strom: USB (micro)        │  WLAN oder Bluetooth SPP           │
└────────────────────────────┼───────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Android Sound-App                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Potenza Drive / RevHeadz / Similar                      │    │
│  │                                                          │    │
│  │  OBD2-Client ◀▶ BT/WLAN-SPP ◀▶ Virtuelle Sound-Synth.  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Zustandsmaschine: Fahrzeug-Status

```
                    ┌──────────┐
                    │  OFF     │
                    │ (Ignition)│
                    └────┬─────┘
                         │ Fahrzeug aus
                         │ OBD2 Ready = Nein
                         │ RPM = 0
                    ┌────┴─────┐
          Ready=True│          │Ready=False
                    │  READY   │
                    │ (Engine  │
                    │  Running)│
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
        ┌─────┴───┐ ┌────┴────┐ ┌───┴──────┐
        │  IDLE   │ │ACCEL  │ │DECEL   │
        │ (0-5km/h)│ │(Gas↑)  │ │(Brems↓) │
        │ RPM:800 │ │RPM↑↑   │ │RPM↓↓    │
        └────┬────┘ └────┬────┘ └───┬────┘
             │           │          │
             │    ┌──────┴───┐      │
             │    │ SHIFT    │      │
             │    │ Point    │      │
             │    │ RPM>5500 │      │
             │    └────┬─────┘      │
             │         │            │
             │    ┌────┴─────┐      │
             │    │  GEAR UP │◀─────┘
             │    │ RPM→3500 │
             │    └──────────┘
             │
        ┌────┴────────────────────────┐
        │  DRIVE (5-100+ km/h)        │
        │  Dynamische RPM-Simulation  │
        └─────────────────────────────┘
```

## Schlüssel-Komponenten (AKTUALISIERT)

### 1. Vgate iCar Pro BLE OBD2 Client
- **Aufgabe:** BLE-Verbindung zum Vgate iCar Pro aufbauen, OBD2-PIDs abfragen
- **Schnittstelle:** BLE Socket (RFCOMM-Emulation über GATT)
- **Ausgangsdaten:**
  - `vehicle_speed` (km/h) - PID 0x0D vom Vgate
  - `vehicle_ready` (bool) - PID 0x0A (RPM) oder Status-Ping
  - `throttle_position` (0-100%) - PID 0x11 (Pedal Position)
  - **NICHT VERFÜGBAR:** Motor-RPM (EV hat keinen), Power, Rekuperation
  - **EINSCHRÄNKUNG:** Vgate iCar Pro kann nur standard OBD2-PIDs lesen

### 2. RPM-Simulator (Core Algorithm)
- **Eingänge:** speed, throttle, power, acceleration, ready
- **Ausgänge:** virtual_rpm (0-8000), engine_load (0-100%)
- **Logik:** Siehe `memory-bank/rpm_algorithm_spec.md`

### 3. ELM327-Emulator
- **Aufgabe:** OBD2-Protokoll implementieren
- **Features:**
  - AT-Befehle verarbeiten
  - PID-Anfragen beantworten (01nnnn)
  - Ready-Status melden
  - Fehlercodes bei ungültigen PIDs

### 4. Bluetooth SPP Server
- **Aufgabe:** RFCOMM-Verbindung zu Android verwalten
- **Features:**
  - Pairing unterstützen
  - Datenpufferung
  - Latency-Optimierung

## Datenfluss-Pipeline

```
CAN-Frame (2-8 Bytes)
    │
    ▼
Parser (extract speed, throttle, etc.)
    │
    ▼
State Machine (update ready, drive_state)
    │
    ▼
RPM Algorithm (speed + throttle + power → rpm)
    │
    ▼
PID Response Builder (010C → ASCII response)
    │
    ▼
Bluetooth SPP (send to Android)
```

## Kritische Implementierungspfade

### Pfad 1: RPM-Echtzeitsimulation
1. CAN-Frame mit Speed/Throttle empfangen
2. Werte validieren und glätten
3. RPM-Algorithmus berechnen
4. OBD2-Response formatieren (`41 0C XX XX`)
5. Via Bluetooth senden

### Pfad 2: PID-Anfrage-Verarbeitung
1. Android sendet `010C` (RPM anfordern)
2. Parser erkennt PID 0x0C
3. Prüfen: Fahrzeug Ready?
   - Nein: Senden `NO DATA`
   - Ja: Berechnete RPM verwenden
4. RPM in Bytes umwandeln (Formula: `A*256+B = 4*rpm`)
5. Response senden: `41 0C XX XX`

### Pfad 3: ELM327 Handshake
1. Android verbindet via Bluetooth SPP
2. Adapter sendet Willkommensnachricht
3. Android sendet AT-Befehle (`ATZ`, `ATE0`, `ATH0`, `ATSP0`)
4. Adapter bestätigt mit `OK`
5. Android sendet `0100` (Supported PIDs)
6. Adapter antwortet mit Bitfeld (PID 0C und 0D gesetzt)
7. Android sendet `010C`, `010D`
8. Datenfluss beginnt

## SSH Zugang (AKTUALISIERT 2026-06-26)

- **vollständige Dokumentation:** `memory-bank/sshAccess.md`
- **Host:** `192.168.178.87`, **User:** `lsd`, **Passwort:** `maxlose288`
- **Zweck:** Fernwartung, Dateitransfer, Service-Management, Log-Analyse

## Design Patterns

- **State Machine:** Fahrzeugzustände verwalten
- **Observer Pattern:** CAN-Datenänderungen lösen RPM-Berechnung aus
- **Adapter Pattern:** EV-Daten → OBD2-Format Konvertierung
- **Buffer Pool:** Bluetooth-Datenpufferung für geringe Latency