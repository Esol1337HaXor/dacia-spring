#!/bin/bash
# Installiert den SPP ELM327 Server als systemd Service
# Korrigiert Probleme:
#   1. rfcomm0 wird beim Service-Start automatisch erstellt
#   2. Permissions für /home/lsd/obd2-adapter sind korrekt
#   3. User=lsd statt User=root
#   4. Keine Security-Restriktionen die Serial Port blockieren

set -e

SERVICE_FILE="spp-elm327-server.service"
TARGET_DIR="/etc/systemd/system"
PROJECT_DIR="/home/lsd/obd2-adapter"

echo "=== SPP ELM327 Server Installation ==="
echo ""

# Schritt 0: Prüfen ob wir als root sind (für sudo)
if [ "$EUID" -ne 0 ]; then 
    echo "Dieses Skript muss als root oder mit sudo ausgeführt werden!"
    exit 1
fi

# Schritt 1: Alten Service stoppen und entfernen
echo "=== Schritt 1: Alten Service stoppen ==="
systemctl stop elm327-server 2>/dev/null || true
systemctl stop spp-elm327-server 2>/dev/null || true
systemctl disable elm327-server 2>/dev/null || true
rm -f "$TARGET_DIR/elm327-server.service"
echo "Alter Service entfernt."

# Schritt 2: Service-File kopieren
echo ""
echo "=== Schritt 2: Service-File kopieren ==="
cp "$SERVICE_FILE" "$TARGET_DIR/$SERVICE_FILE"
echo "Service-File nach $TARGET_DIR/$SERVICE_FILE kopiert."

# Schritt 3: Ordner-Permissions sicherstellen
echo ""
echo "=== Schritt 3: Permissions prüfen ==="
chmod 755 /home/lsd/obd2-adapter 2>/dev/null || true
echo "Ordner-P permissions gesetzt."

# Schritt 4: User zur dialout Group hinzufügen
echo ""
echo "=== Schritt 4: User zur dialout Group hinzufügen ==="
usermod -aG dialout lsd 2>/dev/null || true
echo "User lsd ist jetzt in dialout Group."

# Schritt 5: Systemd neu laden
echo ""
echo "=== Schritt 5: Systemd neu laden ==="
systemctl daemon-reload
echo "Neu geladen."

# Schritt 6: Service aktivieren
echo ""
echo "=== Schritt 6: Service aktivieren ==="
systemctl enable "$SERVICE_FILE"
echo "Service aktiviert."

# Schritt 7: rfcomm0 erstellen (wenn Device gepairt ist)
echo ""
echo "=== Schritt 7: rfcomm0 erstellen ==="
rfcomm release /dev/rfcomm0 2>/dev/null || true
rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1 && echo "rfcomm0 erstellt." || echo "rfcomm0 creation skipped (device may not be paired)."

# Schritt 8: Service starten
echo ""
echo "=== Schritt 8: Service starten ==="
systemctl start "$SERVICE_FILE"
echo "Service gestartet."

# Schritt 9: Status prüfen
echo ""
echo "=== Schritt 9: Status prüfen ==="
systemctl status "$SERVICE_FILE" --no-pager -l || echo "Service läuft noch nicht — Logs prüfen mit: journalctl -u $SERVICE_FILE -n 50"

echo ""
echo "=== Installation abgeschlossen ==="
echo ""
echo "Wichtige Befehle:"
echo "  systemctl status $SERVICE_FILE    # Status prüfen"
echo "  journalctl -u $SERVICE_FILE -n 50  # Logs anzeigen"
echo "  rfcomm show                       # rfcomm0 Status"
echo "  bluetoothctl info 13:E0:2F:8D:61:07  # Device Status"