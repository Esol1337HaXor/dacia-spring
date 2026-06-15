# Projektbrief: OBD2 EV Adapter

## Projektname
OBD2-Kompatibilitätslayer für Sound-Apps in einem Dacia Spring (Elektroauto)

## Übergeordnete Ziele
- Entwicklung eines Hardware/Software-Adapters der sich als kompatibler ELM327-OBD2-Adapter ausgeben gegenüber Android Sound-Apps
- Echtzeit-Synthese realistischer Verbrennerdaten aus EV-Fahrzeugdaten
- Ermöglichen der Nutzung bestehender Motorsound-Apps (Potenza Drive, RevHeadz etc.) im Dacia Spring

## Scope
**In Scope:**
- CAN-Bus Datenakquisition vom Dacia Spring
- ELM327 Protokoll-Emulation über Bluetooth SPP
- Künstliche RPM-Simulation mit realistischem Verhalten
- Fahrzeuggeschwindigkeit-Übergabe
- Android App-Integration

**Out of Scope:**
- Modifikation der Sound-Apps selbst
- Fahrzeug-Steuerung oder -beeinflussung
- Commercial Deployment

## Erfolgskriterien
- [ ] Sound-App erkennt Fahrzeug als OBD2-kompatibel
- [ ] RPM-Werte werden in Echtzeit korrekt emuliert
- [ ] Geschwindigkeit wird zuverlässig übertragen
- [ ] Sound-App reagiert natürlicherweise auf Beschleunigung/Bremsen
- [ ] Keine spürbaren Latenzen (< 50ms Antwortzeit)

## Stakeholder
- Primary User: Eigenbedarf (Esol1337HaXor)
- Secondary: Open Source Community, EV-Enthusiasts

## Datum
- Erstellt: 2026-01-15
- Version: 1.0