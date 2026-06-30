# SSH Zugang Raspberry Pi

**Erstellt:** 2026-06-26
**Zweck:** Dokumentation des funktionierenden SSH-Zugangs zum Raspberry Pi für Fernwartung und Dateitransfer.

---

## Zugangsdaten

| Parameter | Wert |
|-----------|------|
| **Host** | `192.168.178.87` |
| **Benutzer** | `lsd` |
| **Passwort** | `maxlose288` |
| **SSH Port** | 22 |

---

## Verbindungscommandos

### SSH Verbindung
```bash
ssh lsd@192.168.178.87
```

### SCP - Dateien hochladen
```bash
scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 <local_file> lsd@192.168.178.87:/home/lsd/obd2-adapter/
```

### SCP - Dateien herunterladen
```bash
scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 lsd@192.168.178.87:/home/lsd/obd2-adapter/<remote_file> .
```

###sudo Befehle via SSH
```bash
ssh lsd@192.168.178.87 "echo 'maxlose288' | sudo -S <command>"
```

### Service Status prüfen
```bash
ssh lsd@192.168.178.87 "systemctl status spp-elm327-server --no-pager"
```

### Logs anzeigen
```bash
ssh lsd@192.168.178.87 "journalctl -u spp-elm327-server --no-pager -n 50"
```

---

## Wichtige Pfade auf dem Pi

| Pfad | Beschreibung |
|------|--------------|
| `/home/lsd/obd2-adapter/` | Projektverzeichnis |
| `/home/lsd/obd2-adapter/spp_tcp_server.py` | Hauptserver |
| `/home/lsd/obd2-adapter/spp-elm327-server.service` | Systemd Service |
| `/etc/systemd/system/spp-elm327-server.service` | Installierter Service |
| `/dev/rfcomm0` | Bluetooth Classic Serial Port |

---

## Wichtige Services

| Service | Port | Beschreibung | Status |
|---------|------|--------------|--------|
| `spp-elm327-server` | 2117 | TCP ELM327 Server | ✅ Aktiv |
| `bluetooth` | - | Bluetooth Service | ✅ Aktiv |
| `ssh` | 22 | SSH Server | ✅ Aktiv |

---

## Häufig genutzte Befehle

### Service neustarten
```bash
ssh lsd@192.168.178.87 "echo 'maxlose288' | sudo -S systemctl restart spp-elm327-server"
```

### Service stoppen
```bash
ssh lsd@192.168.178.87 "echo 'maxlose288' | sudo -S systemctl stop spp-elm327-server"
```

### rfcomm0 neu erstellen
```bash
ssh lsd@192.168.178.87 "echo 'maxlose288' | sudo -S rfcomm release /dev/rfcomm0 && echo 'maxlose288' | sudo -S rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1"
```

### Bluetooth Device Status
```bash
ssh lsd@192.168.178.87 "bluetoothctl info 13:E0:2F:8D:61:07"
```

### Server Logs in Echtzeit
```bash
ssh lsd@192.168.178.87 "journalctl -u spp-elm327-server -f"
```

---

## Troubleshooting

### Service startet nicht
```bash
# 1. Status prüfen
systemctl status spp-elm327-server

# 2. Logs ansehen
journalctl -u spp-elm327-server -n 50

# 3. Service neu starten
sudo systemctl restart spp-elm327-server

# 4. Service File prüfen
cat /etc/systemd/system/spp-elm327-server.service
```

### rfcomm0 fehlt
```bash
# rfcomm0 neu erstellen
sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1
```

### Permissions Fehler
```bash
# Ordner Berechtigung fixen
sudo chmod 755 /home/lsd/obd2-adapter

# User zur dialout Group
sudo usermod -aG dialout lsd
```

---

## Sicherheitshinweise

- Das Passwort sollte regelmäßig geändert werden
- SSH Key-basierte Authentifizierung wird empfohlen
- Die `StrictHostKeyChecking=no` Option sollte nur für Tests verwendet werden