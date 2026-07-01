#!/bin/bash
#
# Vollständige Installation des vGate iCar Pro BT OBD2-Systems
#
# Dies Skript richtet alles ein: Pairing, RFCOMM, systemd Service
#
# Verwendung: sudo bash install.sh
#

set -e

VGLITE_MAC="13:E0:2F:8D:61:07"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_FILE="$PROJECT_DIR/pi/spp-elm327-server.service"

echo "=============================================="
echo "vGate iCar Pro BT OBD2-System Installation"
echo "=============================================="
echo ""

# Schritt 0: Root prüfen
if [ "$EUID" -ne 0 ]; then
    echo "❌ Dieses Skript muss als root oder mit sudo ausgeführt werden!"
    exit 1
fi

# Schritt 1: Alte Services bereinigen
echo "[1/8] Alte Services bereinigen..."
systemctl stop elm327-server 2>/dev/null || true
systemctl stop spp-elm327-server 2>/dev/null || true
systemctl disable elm327-server 2>/dev/null || true
systemctl disable spp-elm327-server 2>/dev/null || true
rm -f /etc/systemd/system/elm327-server.service
echo "   Alte Services entfernt."
echo ""

# Schritt 2: Bluetooth aktivieren
echo "[2/8] Bluetooth aktivieren..."
bluetoothctl power on
bluetoothctl scan on
sleep 2
bluetoothctl scan off
echo "   Bluetooth aktiv."
echo ""

# Schritt 3: Pairing durchführen
echo "[3/8] Pairing mit vGate iCar Pro ($VGLITE_MAC)..."
bluetoothctl trust "$VGLITE_MAC" 2>/dev/null || true
bluetoothctl pair "$VGLITE_MAC" 2>/dev/null || {
    echo "   ⚠️  Pairing manuell nötig:"
    echo "   bluetoothctl"
    echo "   [bluetooth]# pair $VGLITE_MAC"
    echo "   PIN: 1234 oder 0000"
}
echo ""

# Schritt 4: RFCOMM Device erstellen
echo "[4/8] RFCOMM Device /dev/rfcomm0 erstellen..."
rfcomm release /dev/rfcomm0 2>/dev/null || true
rm -f /dev/rfcomm0
rfcomm bind /dev/rfcomm0 "$VGLITE_MAC" 1
echo "   /dev/rfcomm0 erstellt."
echo ""

# Schritt 5: Projekt-Pfade einrichten
echo "[5/8] Projekt-Pfade einrichten..."
chmod 755 "$PROJECT_DIR"
echo "   Projekt-Verzeichnis: $PROJECT_DIR"
echo ""

# Schritt 6: User zur dialout Group
echo "[6/8] User zur dialout Group hinzufügen..."
CURRENT_USER=$(whoami)
usermod -aG dialout "$CURRENT_USER" 2>/dev/null || true
echo "   $CURRENT_USER ist in dialout Group."
echo ""

# Schritt 7: systemd Service installieren
echo "[7/8] systemd Service installieren..."
cp "$SERVICE_FILE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable spp-elm327-server
echo "   Service installiert und aktiviert."
echo ""

# Schritt 8: Service starten
echo "[8/8] Service starten..."
systemctl start spp-elm327-server
echo "   Service gestartet."
echo ""

echo "=============================================="
echo "✅ Installation abgeschlossen!"
echo "=============================================="
echo ""
echo "Status prüfen: systemctl status spp-elm327-server"
echo "Logs ansehen:  journalctl -u spp-elm327-server -f"
echo "Server Port:   2117"
echo ""
echo "Nächste Schritte:"
echo "  1. Android-Gerät mit demselben WiFi verbinden"
echo "  2. Pi-Adresse ermitteln: hostname -I"
echo "  3. RevHeadz öffnen und verbinden"
echo "     IP: <Pi-Adresse>, Port: 2117"