# Android App Einrichtung - Dacia Spring OBD2 Server

## Server-Status

Der ELM327 WiFi TCP Server l鋟ft auf dem Raspberry Pi:
- **IP-Adresse:** 192.168.178.87
- **Port:** 2117
- **Protokoll:** WiFi TCP (ELM327-Emulation)
- **Daten:** Simulierte RPM und Speed (da EV keinen Motor)

## Server starten/beenden

```bash
# Server starten
cd ~/obd2-adapter
source ~/obd2-adapter-env/bin/activate
nohup python3 elm327_ble_tcp_server.py --no-ble > /tmp/elm327_new.log 2>&1 &

# Server stoppen
pkill -f elm327_ble_tcp_server.py

# Server-Status
ps aux | grep elm327

# Logs ansehen
cat /tmp/elm327_new.log
```

## Handy mit demselben WiFi verbinden

Stellt sicher, dass euer Handy im gleichen WiFi-Netzwerk ist wie der Pi (192.168.178.xxx).

## App 1: Car Scanner ELM OBD2 (Empfohlen)

1. **App installieren:** [Car Scanner ELM OBD2](https://play.google.com/store/apps/details?id=elmarci.eldscanner)
2. **Verbindung einrichten:**
   - 諸ffnet die App
   - Geht zu `Einstellungen` -> `Ger鋞everbindung`
   - W鋒lt `WiFi` (nicht Bluetooth!)
   - **IP-Adresse:** 192.168.178.87
   - **Port:** 2117
   - **Verbinden** dr체cken
3. **Daten anzeigen:**
   - Auf das `+` Symbol tippen um Daten zu hinzuf체gen
   - Sucht nach `Motor-Drehzahl` oder `Engine RPM`
   - Sucht nach `Fahrzeuggeschwindigkeit` oder `Vehicle Speed`
   - Die Werte sollten jetzt live angezeigt werden (RPM ~850 im Leerlauf)

## App 2: RevHeadz (Motorsound)

1. **App installieren:** [RevHeadz](https://play.google.com/store/apps/details?id=com.revheadz)
2. **OBD2-Einstellungen:**
   - 諸ffnet RevHeadz
   - Geht zu `Einstellungen` -> `OBD2 Connection`
   - W鋒lt `TCP/IP` oder `WiFi`
   - **Host/IP:** 192.168.178.87
   - **Port:** 2117
3. **Sound aktivieren:**
   - W鋒lt einen Motorsound aus
   - Das Handyr sollte jetzt den simulierten Motorsound wiedergeben
   - Achtung: Da simulierte Daten verwendet werden, bleibt der Sound konstant (~Idle)

## App 3: Potenza Drive

1. **App installieren:** [Potenza Drive](https://play.google.com/store/apps/details?id=com.potenza.drive)
2. **Verbindung:**
   - W鋒lt `External Device` -> `WiFi`
   - IP: 192.168.178.87, Port: 2117
3. **Dashboard anpassen:**
   - Fügt RPM und Speed Widgets hinzu

## Testen ohne App

Ihr kчnnt die Verbindung auch mit einem einfachen TCP-Test pr체fen:

```bash
# Auf dem Pi ausf체hren
cd ~/obd2-adapter
source ~/obd2-adapter-env/bin/activate
python3 test_tcp_client.py
```

Erwartete Ausgabe:
```
[6] Sende 010C (RPM)...
    Antwort: '41 0C 0D 48'    <- RPM = 850

[7] Sende 010D (Speed)...
    Antwort: '41 0D 00'      <- Speed = 0 km/h
```

## Werte live erleben

Da das Auto im Leerlauf ist (Speed = 0), bleibt der simulierte RPM bei ~850.
Um ver鋘derte RPM-Werte zu sehen, kчnnt ihr:

1. **Speed simulieren:** Modifiziert den Server um Speed > 0 zu senden
2. **Echte Daten einbinden:** Wenn der Vlink Adapter verbunden ist, werden echte CAN-Daten verwendet

## Troubleshooting

### Verbindung fehlgeschlagen
- Pr체ft ob der Pi erreichbar ist: `ping 192.168.178.87`
- Pr체ft ob der Server l鋟ft: `ps aux | grep elm327`
- Pr체ft Port: `ss -tlnp | grep 2117`

### Keine Daten empfangen
- Server-Logs ansehen: `cat /tmp/elm327_new.log`
- Test-Script ausf체hren: `python3 test_tcp_client.py`

### Zu hohe Latenz
- Handy n鋒er an den Router bringen
- 5GHz WiFi statt 2.4GHz verwenden