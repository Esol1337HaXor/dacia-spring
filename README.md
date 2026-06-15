# OBD2 EV Adapter - Sound-Layer für Dacia Spring

![Status](https://img.shields.io/badge/Status-Concept-red)
![License](https://img.shields.io/badge/License-MIT-blue)

## 🎯 Projektübersicht

Dieses Projekt implementiert einen Hardware/Software-Adapter, der sich als kompatibler **ELM327 OBD2-Dongle** gegenüber Android Sound-Apps ausgeben, aber in Echtzeit echte Fahrzeugdaten eines **Dacia Spring Elektroauto** verwendet.

Fehlende Verbrennerdaten (insbesondere Motordrehzahl/RPM) werden künstlich aus EV-Daten wie Geschwindigkeit, Fahrpedalstellung und Leistung erzeugt.

### Was erreicht werden soll

- Bestehende Android-Sound-Apps (Potenza Drive, RevHeadz etc.) im Dacia Spring nutzen
- Realistische Motorsounds durch simulierte RPM-Werte
- Echte Fahrzeuggeschwindigkeit für authentisches Erlebnis
- Plug-and-Play über OBD2-Port und Bluetooth

## 🏗️ Architektur

```
Dacia Spring (CAN-Bus)
    ↓ CAN-Bus (OBD2 Pin 6, 14)
OBD2 Adapter (ESP32 / Pi Zero 2W)
    ↓ CAN → Datenakquisition
RPM Simulator (Echtzeit-Synthese)
    ↓ Virtuelle RPM + Echte Speed
ELM327 Emulator (OBD2-Protokoll)
    ↓ Bluetooth SPP
Android Sound-App
```

## 📁 Projektstruktur

```
dacia-spring-obd2/
├── memory-bank/              # Cline Memory Bank Dokumentation
│   ├── projectbrief.md       # Projektziele und Scope
│   ├── productContext.md     # Produktkontext und User Experience
│   ├── techContext.md        # Technologien und Abhängigkeiten
│   ├── systemPatterns.md     # Systemarchitektur und Design Patterns
│   ├── activeContext.md      # Aktuelle Arbeit und Entscheidungen
│   └── progress.md           # Fortschritt und Phasen
├── firmware/                 # Firmware-Quellcode (künftig)
│   ├── pi/                  # Raspberry Pi Implementierung (**HAUPTPLATTFORM**)
│   └── esp32/               # ESP32 Implementierung (Alternative)
├── python-tools/            # Python Hilfsprogramme (künftig)
├── docs/                    # Zusatzdokumentation
│   ├── obd2_pid_reference.md
│   ├── elm327_commands.md
│   └── can_bus_reference.md
├── hardware/                # Hardware-Design (künftig)
└── tests/                   # Tests (künftig)
```

## 🚀 Schnellstart

> **Hinweis:** Dieses Projekt befindet sich derzeit in der Konzeptphase.

### Voraussetzungen
- Dacia Spring Elektroauto
- ESP32 DevKit V1 oder Raspberry Pi Zero 2 W
- Android-Smartphone mit Bluetooth
- Sound-App (Potenza Drive, RevHeadz o.Ä.)

### Hardware-Bestellliste (Empfohlen: Raspberry Pi Zero 2 W)
| Komponente | ca. Kosten |
|------------|------------|
| Raspberry Pi Zero 2 W | €15 |
| Pican 2 CAN-HAT | €25 |
| OBD2-Stecker (16-pin) | €2 |
| Gehäuse (3D-gedruckt) | €3 |
| Micro-USB Netzteil | €5 |
| **Gesamt** | **~€50** |

### Alternative: ESP32 (Günstiger, aber komplexer)
| Komponente | ca. Kosten |
|------------|------------|
| ESP32 DevKit V1 | €5 |
| MCP2515 CAN-Modul | €3 |
| TJA1050 CAN-Transceiver | €2 |
| **Gesamt** | **~€10** |

## 📡 OBD2 PID Mapping

| PID | Name | Quelle | Typ |
|-----|------|--------|-----|
| 0x0C | Engine RPM | **Simuliert** | Virtuell |
| 0x0D | Vehicle Speed | **Echt CAN** | True |
| 0x04 | Engine Load | Simuliert | Optional |
| 0x05 | Coolant Temp | Simuliert | Optional |

## 📶 ELM327 AT-Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `ATZ` | Gerät zurücksetzen |
| `ATI` | Herstellerinfo |
| `ATE0` | Echo ausschalten |
| `ATH0` | Header ausschalten |
| `ATS0` | Space ausschalten |
| `ATSP0` | Protokoll automatisch |

## 📚 Dokumentation

Alle technischen Details finden sich in der **Memory Bank**:
- [Projektbrief](memory-bank/projectbrief.md) - Ziele und Scope
- [Produktkontext](memory-bank/productContext.md) - Warum dieses Projekt
- [Technischer Kontext](memory-bank/techContext.md) - Technologien und Tools
- [Systemarchitektur](memory-bank/systemPatterns.md) - Design und Patterns
- [Aktuelle Arbeit](memory-bank/activeContext.md) - Stand und Entscheidungen
- [Fortschritt](memory-bank/progress.md) - Status und Phasen

### Technische Referenz
- [OBD2 PID Referenz](docs/obd2_pid_reference.md) - PID-Formeln und Implementierung
- [ELM327 AT-Befehle](docs/elm327_commands.md) - Protokoll-Spezifikation
- [CAN-Bus Referenz](docs/can_bus_reference.md) - Dacia Spring / Renault ZE Plattform
- [RPM Algorithmus](memory-bank/rpm_algorithm_spec.md) - RPM-Simulations-Spezifikation

## 🔧 Entwicklungsstatus

**Phase 1: Konzept & Recherche** (80% abgeschlossen)

- [x] Projektpitch analysiert
- [x] Memory Bank erstellt
- [ ] CAN-Bus Frame-Recherche
- [ ] ELM327-Protokoll studieren
- [ ] Hardware beschaffen

## ⚠️ Disclaimer

- **Nur zu Demonstrations/Entwicklungszwecken**
- **Nicht für den Straßenverkehr bestimmt**
- **Keine Garantie für Kompatibilität mit bestimmten Apps**
- **Auf eigene Gefahr implementieren und testen**

## 📄 Lizenz

MIT License - Siehe [LICENSE](LICENSE) Datei

## 🤝 Mitwirken

Issues und Pull Requests sind willkommen!

---

**Erstellt:** 2026-01-15  
**Autor:** Esol1337HaXor  
**Projekt:** Dacia Spring OBD2 Adapter