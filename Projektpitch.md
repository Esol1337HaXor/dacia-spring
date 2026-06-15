Projektidee: OBD2-Kompatibilitätslayer für Sound-Apps in einem Dacia Spring (Elektroauto)

Ausgangslage:

Ich möchte bestehende Android-Apps für Motorsounds (z. B. Potenza Drive, RevHeadz oder ähnliche Apps) in einem Dacia Spring nutzen. Diese Apps erwarten typischerweise die OBD2-Daten eines Verbrennungsmotors, insbesondere eine Motordrehzahl (RPM über PID 0x0C).

Das Problem ist, dass der Dacia Spring als Elektrofahrzeug keine klassische Verbrenner-Motordrehzahl bereitstellt. Die App verbindet sich zwar mit dem Fahrzeug bzw. dem OBD2-Adapter, meldet dann aber Inkompatibilität oder funktioniert nicht korrekt, weil keine gültigen RPM-Werte verfügbar sind.

Bekannte Fakten:

* Der Dacia Spring kann über OBD2 und CAN-Bus umfangreich ausgelesen werden.
* Die App CanZE Plus unterstützt den Spring und kann zahlreiche Fahrzeugdaten anzeigen.
* Fahrzeuggeschwindigkeit ist verfügbar.
* Ready-/Ignition-Status ist verfügbar.
* Weitere Daten wie Leistungsaufnahme, Rekuperation, Stromfluss, Fahrpedalstellung oder ähnliche EV-spezifische Werte könnten ebenfalls verfügbar sein.
* Die gewünschte Sound-App benötigt vermutlich hauptsächlich RPM und Geschwindigkeit.

Ziel:

Entwicklung eines Hardware-/Software-Adapters, der sich gegenüber einer Android-Sound-App wie ein kompatibler ELM327-OBD2-Adapter verhält, intern aber die echten Fahrzeugdaten des Dacia Spring verwendet und fehlende Verbrennerdaten künstlich erzeugt.

Geplante Architektur:

Variante 1 (bevorzugt):

Dacia Spring
→ echter OBD/CAN-Zugriff
→ Raspberry Pi Zero 2 W oder ESP32
→ Bluetooth Classic (SPP)
→ Android Sound-App

Der Raspberry Pi bzw. ESP32 soll als virtueller ELM327 auftreten.

Funktionen des Adapters:

1. Verbindung zum Fahrzeug herstellen und reale Daten auslesen.
2. Bluetooth Serial Port Profile (SPP) bereitstellen.
3. Sich gegenüber Android-Apps als ELM327-kompatibles Gerät ausgeben.
4. Standard-ELM327-Kommandos beantworten.
5. Standard-PIDs weiterreichen oder selbst erzeugen.

Besonderes Augenmerk auf folgende PIDs:

* PID 0x0D (Fahrzeuggeschwindigkeit):

  * Echte Werte aus dem Fahrzeug liefern.

* PID 0x0C (Motordrehzahl/RPM):

  * Künstlich erzeugen.

Idee zur RPM-Simulation:

Die RPM sollen nicht einfach linear aus der Geschwindigkeit berechnet werden, sondern möglichst realistisch wirken.

Beispielparameter:

Eingänge:

* Geschwindigkeit
* Beschleunigung
* Leistungsaufnahme (kW)
* Rekuperationsleistung
* Fahrpedalstellung
* Ready-Status

Ausgänge:

* Virtuelle Motordrehzahl
* Virtuelle Last

Mögliche Logik:

Wenn Fahrzeug nicht "Ready":
→ RPM = 0

Wenn Fahrzeug "Ready" aber steht:
→ RPM = 800–1000 (virtueller Leerlauf)

Bei Beschleunigung:
→ RPM steigt schnell an

Virtuelle Schaltvorgänge:
→ RPM steigt bis z. B. 6000
→ fällt auf 3500 zurück
→ steigt erneut

Dadurch entsteht für die Sound-App das Verhalten eines mehrgängigen Verbrennungsmotors.

Fragen zur technischen Umsetzung:

1. Reicht es aus, nur PID 0x0C (RPM) zu emulieren, oder erwarten typische Sound-Apps weitere Sensorwerte?
2. Welche Standard-PIDs werden von bekannten Sound-Apps normalerweise abgefragt?
3. Kann ein Raspberry Pi Zero 2 W zuverlässig einen ELM327 emulieren?
4. Ist ein ESP32 für Bluetooth-Classic-SPP-ELM327-Emulation ausreichend?
5. Gibt es existierende Open-Source-Projekte zur ELM327-Emulation, die als Basis verwendet werden können?
6. Wie würden echte ELM327-Kommandos wie ATZ, ATI, 010C, 010D usw. am besten implementiert?
7. Wie lässt sich ein möglichst realistisches RPM-Modell für ein Elektrofahrzeug erzeugen?
8. Kann man EV-spezifische Daten wie Leistung und Rekuperation sinnvoll in die virtuelle Motordrehzahl integrieren?

Ziel des Projekts:

Eine bestehende Android-Sound-App soll glauben, mit einem Verbrennerfahrzeug verbunden zu sein, obwohl tatsächlich ein Dacia Spring verwendet wird. Die fehlenden Verbrennerdaten sollen in Echtzeit aus den vorhandenen EV-Daten synthetisiert werden, um ein möglichst realistisches Fahrerlebnis zu erzeugen.
