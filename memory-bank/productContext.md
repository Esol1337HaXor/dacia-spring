# Produktkontext: OBD2 EV Adapter

## Warum existiert dieses Projekt?
Bestehende Android-Sound-Apps für Motorsimulation (Potenza Drive, RevHeadz etc.) erwarten OBD2-Daten eines Verbrennungsmotors. Diese Apps interpretieren RPM und Last um daraus realistische Motorenklänge zu synthetisieren. Da der Dacia Spring ein Elektrofahrzeug ist, fehlen diese Daten nativ - die Apps erkennen kein kompatibles Fahrzeug oder verhalten sich inkorrekt.

## Problemstellung
- Sound-Apps erwarten OBD2-PIDs wie RPM (0x0C) die EVs nicht bereitstellen
- Der Dacia Spring hat keinen Verbrennungsmotor → keine echte Motordrehzahl
- Bestehende Lösungen (CanZE Plus) zeigen CAN-Daten an, emulieren aber keine OBD2-Geräte
- Keine open-source Lösung verfügbar die speziell für EV-Sounds optimiert ist

## Wie es funktionieren soll

### Datenfluss
```
Dacia Spring (CAN-Bus)
    ↓
OBD2-Adapter (CAN-Datenakquisition)
    ↓
RPM-Simulator (Echtzeit-Synthese)
    ↓
ELM327-Emulator (OBD2-Protokoll)
    ↓
Bluetooth SPP (Wireless)
    ↓
Android Sound-App (Potenza Drive etc.)
```

### Erwartetes Verhalten
1. **Fahrzeug aus/Ready=False:** App zeigt RPM=0 (kein Motor)
2. **Fahrzeug Ready, stehend:** App zeigt ~800-1000 RPM (Leerlauf)
3. **Beschleunigung:** RPM steigt dynamisch an (simuliert Gangwechsel)
4. **Bremsen/Rollpunkt:** RPM sinkt
5. **Volgas:** RPM steigt bis ~6000, Gangwechsel-Simulation → Drop auf ~3500

## User Experience Goals
- **Immersiv:** Sound reagiert natürlich auf Fahrzeuggeschwindigkeit und Beschleunigung
- **Realistisch:** Simulierte RPM sollten für die Sound-App nicht von echten unterscheiden sein
- **Zuverlässig:** Keine Unterbrechungen oder Lags während der Fahrt
- **Plug-and-Play:** Adapter einstecken, Bluetooth verbinden, Sound-App starten

## Zielgruppe
- Primär: Eigenbedarf (EV-Besitzer mit Interesse an Sound-Simulation)
- Sekundär: Open-Source-Community, EV-Enthusiasts, Projekt-Interessierte

## Einschränkung
- Kein kommerzielles Ziel
- Nur für den Einsatz im Dacia Spring optimiert (aber allgemein haltbar)
- Keine Garantie für Kompatibilität mit allen Sound-Apps