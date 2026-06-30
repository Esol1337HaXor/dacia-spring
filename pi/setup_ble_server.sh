#!/bin/bash
# ============================================
# ELM327 BLE Server Setup-Script
# ============================================
# Dieses Script:
# 1. Stoppt alte Server
# 2. Aktiviert neuen BLE Server mit DynamicSimEngine
# 3. Konfiguriert AutoStart bei Pi-Boot
# ============================================

set -e

echo "============================================"
echo "ELM327 BLE Server Setup"
echo "============================================"
echo ""

# Schritte dokumentieren
echo "Schritt 1: Alte Server stoppen..."
echo "--------------------------------------------"
pkill -f elm327_tcp_server_standalone.py 2>/dev/null || true
pkill -f elm327_tcp_server.py 2>/dev/null || true
pkill -f bt_spp_server.py 2>/dev/null || true
echo "✓ Alte Server gestoppt"
echo ""

echo "Schritt 1.5: BLE Dependencies installieren..."
echo "--------------------------------------------"
# pip direkt mit venv Python ausführen (kein source nötig)
sudo -u lsd /home/lsd/obd2-adapter/obd2-adapter-env/bin/pip install bleak > /dev/null 2>&1 || true
echo "✓ BLE Dependencies bereit"
echo ""

echo "Schritt 2: Systemd Service Datei kopieren..."
echo "--------------------------------------------"
sudo cp /home/lsd/obd2-adapter/elm327-server.service /etc/systemd/system/elm327-server.service
echo "✓ Service Datei kopiert"
echo ""

echo "Schritt 3: Systemd neu laden..."
echo "--------------------------------------------"
sudo systemctl daemon-reload
echo "✓ Systemd neu geladen"
echo ""

echo "Schritt 4: ELM327 BLE Server aktivieren..."
echo "--------------------------------------------"
sudo systemctl enable elm327-server.service
echo "✓ AutoStart aktiviert"
echo ""

echo "Schritt 5: ELM327 BLE Server starten..."
echo "--------------------------------------------"
sudo systemctl start elm327-server.service
echo "✓ Server gestartet"
echo ""

echo "Schritt 6: Status prüfen..."
echo "--------------------------------------------"
sudo systemctl status elm327-server.service --no-pager -l
echo ""

echo "============================================"
echo "Setup abgeschlossen!"
echo "============================================"
echo ""
echo "Server-Status: sudo systemctl status elm327-server"
echo "Server-Log:    tail -f /home/lsd/obd2-adapter/server.log"
echo "Server stoppen: sudo systemctl stop elm327-server"
echo "Server starten: sudo systemctl start elm327-server"
echo ""
echo "Nächsten Neustart:test:"
echo "  sudo reboot"
echo "  Nach Boot: sudo systemctl status elm327-server"
echo ""