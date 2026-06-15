# CAN-Bus Referenz - Dacia Spring / Renault ZE Plattform

## Übersicht

Der Dacia Spring verwendet einen CAN-Bus (Controller Area Network) nach ISO 15765-4 (CAN 11-bit, 500 kbps).
Das gleiche CAN-Bus-Plattform wird von Renault für mehrere Elektrofahrzeuge verwendet (Zoe, Kangoo E, Fluence Z.E.).

## Referenzprojekte

### CanZE (Open Source)
- **Repo:** https://github.com/chrismade/CanZE
- **Beschreibung:** Android-App zum Auslesen von Renault ZE Fahrzeugdaten
- **Lizenz:** GPL v3
- **Nutzung:** Dient als Referenz für CAN-Frame-Struktur und Dateninterpretation
- **Code-Basis:** Java, Bluetooth SPP für OBD2-Adapter-Kommunikation

### CanZE Plus (Commercial)
- **Website:** https://www.canze.ro
- **Status:** Keine öffentliche Code-Basis
- **Funktion:** Erweiterte CAN-Daten-Anzeige für Renault ZE Fahrzeuge

## Wichtige Erkenntnisse aus CanZE Analyse

### Bluetooth Kommunikation (ConnectedBluetoothThread.java)
```java
// Buffer-Größe: 1024 Bytes
public static final int BUFFER_SIZE = 1024;

// Datenfluss: Bluetooth → InputStream → byte[] → int[] → Processing Stack
// Die raw byte-Daten werden direkt vom Bluetooth-Stream gelesen
// und an die Verarbeitungs-Stack weitergereicht
```

### Architektur-Muster
- Bluetooth-Thread liest kontinuierlich Daten vom InputStream
- Byte-Array wird in Integer-Array konvertiert
- Processing-Stack interpretiert CAN-Frames
- Daten werden für Display/Aufzeichnung aufbereitet

## Bekannte CAN-Frame-Struktur (Renault ZE Plattform)

### Frame-Form
```
ID (3 Bits/11 Bit) | RTR | DLC | Data Bytes (0-8)
```

### Wichtige CAN-IDs (detaillierte Recherche erforderlich)
Hinweis: Die spezifischen CAN-IDs für den Dacia Spring müssen durch Analyse mit CanZE Plus oder einem CAN-Logger ermittelt werden.

#### Mögliche Speed-Daten (Referenz Renault Zoe)
- CAN-ID für Geschwindigkeit: Oft im Bereich 0x100-0x300
- Datenfeld enthält typischerweise byte-basierte Geschwindigkeit

#### Mögliche Ready/Ignition-Status
- CAN-ID für Fahrzeugstatus: Oft im Bereich 0x300-0x500
- Bit-Position im Datenfeld zeigt Ready/Not Ready Status

#### Mögliche Throttle/Pedal-Position
- CAN-ID für Fahrpedal: Oft im Bereich 0x100-0x400
- Prozentwert im Datenfeld

#### Mögliche Power/Rekuperation
- CAN-ID für Antriebsdaten: Oft im Bereich 0x200-0x500
- Leistung in kW oder als Rohwert

## CAN-Daten-Erkundungs-Plan

### Phase 1: Passive Analyse
1. CanZE Plus auf Android-Gerät installieren
2. OBD2-Adapter an Fahrzeug anschließen
3. CAN-Frames mit CanZE Plus oder CAN-Logger aufnehmen
4. Frames für Speed, Ready, Throttle, Power identifizieren

### Phase 2: Frame-Interpretation
1. Rohdaten mit CanZE Plus-Dokumentation vergleichen
2. Byte-Offset und Skalierungsfaktoren ermitteln
3. Formeln für Datenkonvertierung dokumentieren

### Phase 3: Adapter-Implementierung
1. CAN-Interface auf ESP32/RPi einrichten
2. Frame-Parsing-Logik implementieren
3. Daten-Validierung mit CanZE Plus vergleichen

## OBD2-Port Pinbelegung

| Pin | Funktion | Beschreibung |
|-----|----------|-------------|
| 1 | - | User Defined |
| 2 | - | User Defined |
| 4 | GND | Fahrzeugmasse |
| 5 | GND | Fahrzeugmasse (Shield) |
| 6 | CAN-High | ISO 15765-4 CAN (11-bit, 500kbps) |
| 7 | ISO DDS | ISO 9141-2 Layer |
| 8 | - | User Defined |
| 9 | - | User Defined |
| 10 | - | User Defined |
| 11 | ISO DDS | ISO 9141-2 Layer |
| 14 | CAN-Low | ISO 15765-4 CAN (11-bit, 500kbps) |
| 15 | ISO DDS | ISO 9141-2 Layer |
| 16 | BATT | Batterie-Spannung (12V) |

## Hardware-Empfehlungen für CAN-Interface

### ESP32 Option
- **ESP32 DevKit V1** mit.native CAN-Controller
- **MCP2515** CAN-Controller (SPI, falls kein nativer CAN)
- **TJA1050** CAN-Transceiver (5 Mbps, 12-28V)
- **SN65HVD230** CAN-Transceiver (1 Mbps)

### Raspberry Pi Option
- **Pi Zero 2 W** mit SocketCAN
- **CAN-HAT** (z.B. Pican 2)
- **MCP2515** CAN-Controller auf HAT

## Tools für CAN-Analyse

### Desktop
- **CANalyzer** (Vector) - Kommerziell
- **CANoe** (Vector) - Kommerziell
- **candump** (SocketCAN) - Open Source
- **Wireshark** - Open Source
- **CANbus-KiT** - Open Source

### Mobile
- **CanZE Plus** - Android, Renault ZE
- **Car Scanner ELM OBD2** - Android/iOS
- **OBD9141** - Android

## Wichtige Hinweise

### rechtlicher Hinweis
Die Analyse des CAN-Busses dient nur zu Forschungs- und Entwicklungszwecken.
Das Eindringen in Fahrzeugnetze kann rechtliche Konsequenzen haben.
Nur Fahrzeuge analysieren, die Ihnen gehören oder für die Sie eine schriftliche
Genehmigung des Eigentümers haben.

### technischer Hinweis
Der Dacia Spring verwendet vermutlich die gleiche CAN-Architektur wie
Renault Zoe/Kangoo E. Die CanZE-Codebasis kann als Referenz dienen,
aber die CAN-IDs und Datenformate müssen für den Spring spezifisch
verifiziert werden.