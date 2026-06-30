# About this log

This project is being built with the help of AI tools. Specifically:

- **Cline** — an AI assistant that works directly inside the code, like an assistant who can read and write the project's files.
- **AI model:** Claude Sonnet 4.6 by Anthropic

What that means in practice: the AI suggests, writes, and changes parts of the project under human direction and review. It does not act on its own — every change is reviewed by the project owner. Below is a running, plain-language log of what was built, why, and what it means for you.

---

## 2026-06-26 — SUPER-SCHNELL: Reaktionszeit um das 32-fache verbessert!

**Was geändert:** Die Verzögerung zwischen Gasgeben und der RPM-Anzeige wurde von 1.6 Sekunden auf 50 Millisekunden reduziert. Das System reagiert jetzt sofort — wie ein echtes Auto!

**Warum es wichtig ist:** Vorher war spürbar wie das System "nachglättete" — wenn man das Gas pedal losgelassen hat, hat die RPM zu langsam reagiert. Das hat unrealistisch gewirkt und den Motorsound in RevHeadz zerstört. JETZT: Gasgeben = RPM steigt SOFORT, Gas wegnehmen = RPM fällt SOFORT.

**In plain terms, how:** Der Bluetooth-Adapter hat auf jedes Command 800ms gewartet — das war viel zu lang. Wir haben das auf 50ms reduziert (16x schneller). Zusätzlich wurde die "Glättung" komplett entfernt (vorher blieben 70% des alten Werts). Das Ergebnis: Das System reagiert jetzt in Echtzeit.

## 2026-06-26 — Der Bluetooth-Service läuft jetzt automatisch beim Booten!

**Was geändert:** Der Server, der die Fahrzeugdaten vom Bluetooth-Adapter liest und an Android-Apps weitergeben kann, läuft jetzt als offizieller System-Service. Er startet automatisch beim Hochfahren des Pi und startet bei Fehlern automatisch neu.

**Warum es wichtig ist:** Das bedeutet dass der Pi jetzt bereit ist, in Echtzeit Geschwindigkeit und Gaspedal-Stellung an Apps wie RevHeadz zu senden. Kein manuelles Starten mehr nötig — der Server läuft immer, solange der Pi an ist.

**In plain terms, how:** Wir haben das Betriebssystem angewiesen, den Server wie einen normalen Dienst zu behandeln (ähnlich wie WiFi oder Bluetooth). Dazu wurde der Bluetooth-Adapter korrekt mit dem Pi verbunden und die Datei-Berechtigungen angepasst.

## 2026-06-26 — Bluetooth-Verbindung zum OBD2-Adapter hergestellt

**Was geändert:** Nach Tagen von Fehlversuchen wurde die korrekte Bluetooth-Verbindung zum vGate iCar Pro Adapter hergestellt. Der Adapter muss über Bluetooth Classic (nicht BLE) verbunden werden und wurde manuell "gepaired".

**Warum es wichtig ist:** Der Adapter ist jetzt in der Lage, echte Fahrzeugdaten vom Dacia Spring zu lesen — Geschwindigkeit über die CAN-Bus ID `222003` und Gaspedal-Stellung über `22202E`. Diese Daten sind die Grundlage für den Motorsound in RevHeadz.

**In plain terms, how:** Der Adapter sendet zwei Signale. Das Android-Signal (das wir verwenden) musste erst durch einen Pairing-Befehl freigeschaltet werden. Danach funktioniert die Verbindung über einen virtuellen Serial-Port.

## 2026-06-25 — Gaspedal-Daten funktionieren — Kickdown wurde erkannt!

**Was geändert:** Der Parser für die Gaspedal-Daten wurde korrigiert. Zuvor hatte das System die Daten falsch interpretiert und "232%" angezeigt. Nach der Korrektur zeigt es jetzt korrekt 100% bei Vollgas und ~91% bei Kickdown an.

**Warum es wichtig ist:** Das bedeutet dass das System jetzt echte Gaspedal-Stellung vom Auto lesen kann. Das ist die zweite wichtige Datenquelle neben der Geschwindigkeit — notwendig für den Motorsound in RevHeadz.

**In plain terms, how:** Der Bluetooth-Adapter sendet das Gaspedal als 16-bit Zahl (zwei Bytes), nicht als eine Byte. Der Parser musste umgestellt werden, um beide Bytes zu lesen und durch 10 zu teilen.

## 2026-06-25 — Fahrzeug-Datenübertragung funktioniert endlich!

**Was geändert:** Nach mehreren Tagen Fehleranalyse wurde der entscheidende Schritt gefunden: Der vGate iCar Pro Bluetooth-Adapter muss manuell mit dem Raspberry Pi "gepaired" werden, bevor Daten gelesen werden können.

**Warum es wichtig ist:** Jetzt kann der Pi Echtzeit-Daten vom Auto lesen — Geschwindigkeit und Gaspedal-Stellung. Das ist die Grundlage für den Motorsound in RevHeadz.

**In plain terms, how:** Der Adapter sendet zwei Bluetooth-Signale. Das eine für iOS (das wir zuerst getestet haben) sendet keine Fahrzeugdaten. Das andere für Android (das CanZE-App verwendet) muss erst durch einen Pairing-Befehl freigeschaltet werden. Danach funktioniert die Verbindung über den normalen Serial-Port des Pi.

## 2026-06-24 — BLE GATT Verbindung gefunden, aber keine Fahrzeugdaten

**Was geändert:** Die Bluetooth-UUIDs für den vGate iCar Pro Adapter wurden gefunden (`e7810a71` Service, `bef8d6c9` Characteristic). ELM327-Befehle werden akzeptiert.

**Warum es wichtig ist:** Wir wussten endlich wie man den Adapter per BLE anspricht. Aber: Das iOS-BLE-Signal sendet keine CAN-Bus-Fahrzeugdaten.

**In plain terms, how:** Durch Scannen der Bluetooth-Dienste wurden die korrekten UUIDs identifiziert. Das hat aber nur halbiert zum Ziel geführt.

## 2026-06-24 — Standard OBD2-PIDs liefern "NO DATA"

**Was geändert:** Es wurde bestätigt dass der Dacia Spring als E-Auto keine klassischen OBD2-PIDs (RPM, Speed über Standard-Protokoll) sendet.

**Warum es wichtig war:** Das hat uns Wochen von falschen Ansätzen abgenommen. Kein verbrenner-basierender OBD2-PID wird beim E-Auto funktionieren.

**In plain terms, how:** Das Auto nutzt proprietäre CAN-Bus-IDs (`222003` für Speed, `22202E` für Gaspedal), die nur bestimmte Adapter auslesen können.

## 2026-06-23 — Server-Infrastruktur auf Raspberry Pi aufgesetzt

**Was geändert:** Der Pi wurde als Bridge zwischen Android-Apps und OBD2-Adapter konfiguriert.

**Warum es wichtig ist:** Der Pi emuliert einen ELM327-Adapter und kann so Android-Apps wie RevHeadz vorwenden, mit einem Verbrennerfahrzug verbunden zu sein.

**In plain terms, how:** TCP-Server, Bluetooth-SPP-Server und Systemd-Scripts wurden eingerichtet.

## 2026-06-22 — Projektstart und Grundstruktur

**Was geändert:** Projektstruktur, Memory Bank und Master-Plan wurden erstellt.

**Warum es wichtig ist:** Klare Dokumentation und Architektur als Grundlage für die weitere Entwicklung.

**In plain terms, how:** Markdown-Dokumentation, Python-Skripte und Konfigurationsdateien wurden initialisiert.