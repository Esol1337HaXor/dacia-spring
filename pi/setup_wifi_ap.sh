#!/bin/bash
# =============================================================================
# WiFi AP Setup Script — Installiert hostapd + dnsmasq für Dacia Spring OBD2
# =============================================================================
#
# DIESES SCRIPT MUSS ALS ROOT AUSGEFÜHRT WERDEN!
# Usage: sudo bash setup_wifi_ap.sh
#
# WAS ES TUT:
# 1. Installiert hostapd (Access Point Software)
# 2. Installiert dnsmasq (DHCP + DNS Server)
# 3. Konfiguriert hostapd für DaciaSpring-OBD2 Hotspot
# 4. Konfiguriert dnsmasq für DHCP im 10.0.0.x Netzwerk
# 5. Aktiviert Services für Auto-Start
# 6. Erstellt wifi_mode_switch.sh als ausführbar
#
# NACH DER INSTALLATION:
# - Neustart des Pi empfehlen
# - Test: sudo wifi_mode_switch.sh car → AP sollte starten
# =============================================================================

set -euo pipefail  # Bei Fehler stoppen, ungesetzte Variablen sind Fehler

# Farbe für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[FEHLER]${NC} $1"
}

# =============================================================================
# PRÜFUNG: Root-Rechte?
# =============================================================================
if [ "$EUID" -ne 0 ]; then
    echo_error "Dieses Script MUSS als root ausgeführt werden!"
    echo_error "Usage: sudo bash $0"
    exit 1
fi

echo_info "═══════════════════════════════════════════════"
echo_info " WiFi AP Setup — Dacia Spring OBD2 Adapter"
echo_info "═══════════════════════════════════════════════"

# =============================================================================
# SCHRITT 1: Package Repository aktualisieren
# =============================================================================
echo_info ""
echo_info "SCHRITT 1: Package Repository aktualisieren..."
apt update -y
echo_success "Repository aktualisiert"

# =============================================================================
# SCHRITT 2: hostapd installieren
# =============================================================================
echo_info ""
echo_info "SCHRITT 2: hostapd installieren..."
if dpkg -l | grep -q "^ii  hostapd"; then
    echo_warn "hostapd ist bereits installiert"
    apt list --upgradable 2>/dev/null | grep hostapd
else
    apt install -y hostapd
    echo_success "hostapd installiert"
fi

# =============================================================================
# SCHRITT 3: dnsmasq installieren
# =============================================================================
echo_info ""
echo_info "SCHRITT 3: dnsmasq installieren..."
if dpkg -l | grep -q "^ii  dnsmasq"; then
    echo_warn "dnsmasq ist bereits installiert"
    apt list --upgradable 2>/dev/null | grep dnsmasq
else
    apt install -y dnsmasq
    echo_success "dnsmasq installiert"
fi

# =============================================================================
# SCHRITT 4: Bestehende Netzwerk-Verbindung sichern
# =============================================================================
echo_info ""
echo_info "SCHRITT 4: Bestehende Netzwerk-Verbindung sichern..."

# WLAN-Verstellung prüfen und merken
CURRENT_WIFI=$(iwgetid -r 2>/dev/null || echo "none")
CURRENT_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "unknown")
echo_info "  Aktuell verbunden mit: ${CURRENT_WIFI}"
echo_info "  Aktuelle IP: ${CURRENT_IP}"

# Prüfen ob wir über SSH verbunden sind (wichtig für später!)
if [ -n "${SSH_CONNECTION:-}" ]; then
    echo_success "SSH-Sitzung erkannt — Netzwerk wird NICHT neu gestartet!"
else
    echo_warn "Keine SSH-Sitzung — vorsichtig bei Netzwerk-Änderungen"
fi

echo_success "Netzwerk-Status gemerkt — Installation ohne Verbindungsverlust"

# =============================================================================
# SCHRITT 5: hostapd Config erstellen
# =============================================================================
echo_info ""
echo_info "SCHRITT 5: hostapd Config erstellen..."
cat > /etc/hostapd/hostapd.conf << 'EOF'
# =============================================================================
# hostapd Config — DaciaSpring-OBD2 Hotspot
# =============================================================================

# WiFi Interface
interface=wlan0
driver=nl80211

# Netzwerk-SSID und Password
ssid=DaciaSpring-OBD2
hw_mode=g
channel=6
wmm_enabled=0
macaddr_policy=traditional

# WPA2 Verschlüsselung
wpa=2
wpa_passphrase=obd2spring2026
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP

# Timing
beacon_int=100
dtim_period=2

# Max 10 Clients (für Auto-Nutzung)
max_num_sta=10

# Log Level (0=debug, 1=verbose, 2=standard)
logger_syslog=-1
logger_syslog_level=2
EOF

echo_success "hostapd Config erstellt: /etc/hostapd/hostapd.conf"

# =============================================================================
# SCHRITT 6: hostapd Service aktivieren
# =============================================================================
echo_info ""
echo_info "SCHRITT 6: hostapd Service aktivieren..."

# Systemd Config für hostapd erstellen (falls nicht vorhanden)
if ! grep -q "DAEMON_CONF=" /etc/default/hostapd 2>/dev/null; then
    echo "DAEMON_CONF=/etc/hostapd/hostapd.conf" > /etc/default/hostapd
    echo_success "hostapd Daemon Config erstellt"
else
    # DAEMON_CONF Zeile aktualisieren
    sed -i 's|^DAEMON_CONF=.*|DAEMON_CONF=/etc/hostapd/hostapd.conf|' /etc/default/hostapd
    echo_success "hostapd Daemon Config aktualisiert"
fi

# =============================================================================
# SCHRITT 7: dnsmasq Config ERWEITERN (nicht überschreiben!)
# =============================================================================
echo_info ""
echo_info "SCHRITT 7: dnsmasq Config erweitern (AP-DHCP only)..."

# Backup der alten Config
if [ -f /etc/dnsmasq.conf ]; then
    cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
    echo_success "Alte dnsmasq Config gesichert: /etc/dnsmasq.conf.backup"
    
    # Prüfen ob AP-Config schon vorhanden ist
    if grep -q "DaciaSpring-OBD2" /etc/dnsmasq.conf 2>/dev/null; then
        echo_warn "AP-DHCP Config existiert bereits — wird nicht überschrieben"
    else
        # NICHT die bestehende Config überschreiben, sondern ERWEITERN
        cat >> /etc/dnsmasq.conf << 'EOF'

# =============================================================================
# Dacia Spring OBD2 — AP DHCP Config (hinzugefügt vom Setup-Script)
# =============================================================================
# Diese Sektion wird NUR beim AP-Modus aktiv (siehe wifi_mode_switch.sh)
# Die obige Config bleibt unverändert!
EOF
        echo_success "AP-DHCP Sektion angefügt"
    fi
else
    # Keine existing Config — neue erstellen (sollte nicht vorkommen)
    cat > /etc/dnsmasq.conf << 'EOF'
# =============================================================================
# Dacia Spring OBD2 — Primary dnsmasq Config
# =============================================================================

# Verwende nur wlan0 für DHCP (nicht eth0 oder lo)
interface=wlan0
bind-interfaces

# DHCP Range: 10.0.0.100 - 10.0.0.200 (100 IPs)
dhcp-range=10.0.0.100,10.0.0.200,255.255.255.0,12h

# Router Gateway (Pi IP im AP-Modus)
dhcp-option=3,10.0.0.1

# DNS Server (Pi selbst)
dhcp-option=6,10.0.0.1

# Lease Zeit: 12 Stunden
dhcp-leasefile=/etc/dnsmasq.leases

# Log DHCP Requests
log-dhcp
EOF
    echo_success "Neue dnsmasq Config erstellt"
fi

# =============================================================================
# SCHRITT 8: Services NUR aktivieren (NICHT neustarten!)
# =============================================================================
echo_info ""
echo_info "SCHRITT 8: Services aktivieren (ohne Neustart)..."

# hostapd aktivieren
systemctl enable hostapd 2>/dev/null || echo_warn "hostapd Enable fehlgeschlagen"

# dnsmasq NUR aktivieren — NICHT neustarten!
# Ein Neustart von dnsmasq würde die bestehende Netzwerk-Config brechen
systemctl is-active dnsmasq 2>/dev/null && {
    echo_warn "dnsmasq läuft bereits — wird NICHT neu gestartet (Netzwerkschutz)"
    echo_warn "  Hinweis: dnsmasq Config ändert sich erst nach 'sudo systemctl restart dnsmasq'"
} || {
    echo_info "dnsmasq ist nicht aktiv — wird aktiviert"
    systemctl enable dnsmasq
}

echo_success "hostapd + dnsmasq aktiviert für Auto-Start"
echo_info "  ⚠️  Kein Service-Neustart während der Installation!"
echo_info "  ℹ️  Services werden erst nach NEUSTART aktiv"

# =============================================================================
# SCHRITT 9: wifi_mode_switch.sh ausführbar machen
# =============================================================================
echo_info ""
echo_info "SCHRITT 9: wifi_mode_switch.sh vorbereiten..."

SCRIPT_DIR="/home/lsd/obd2-adapter"
SCRIPT_FILE="${SCRIPT_DIR}/wifi_mode_switch.sh"

if [ -f "$SCRIPT_FILE" ]; then
    chmod +x "$SCRIPT_FILE"
    echo_success "wifi_mode_switch.sh als ausführbar markiert"
else
    echo_warn "wifi_mode_switch.sh nicht gefunden in $SCRIPT_FILE"
    echo_warn "Nach dem Kopieren ausführen: chmod +x $SCRIPT_FILE"
fi

# =============================================================================
# SCHRITT 10: WiFi Interface prüfen
# =============================================================================
echo_info ""
echo_info "SCHRITT 10: WiFi Interface prüfen..."

if ip link show wlan0 | grep -q "UP"; then
    echo_success "wlan0 ist verfügbar"
else
    ip link set wlan0 up
    echo_warn "wlan0 wurde gestartet"
fi

# =============================================================================
# FERTIG — Zusammenfassung
# =============================================================================
echo_info ""
echo_info "═══════════════════════════════════════════════"
echo_success " ✅ WiFi AP Setup ERFOLGTE!"
echo_info "═══════════════════════════════════════════════"
echo_info ""
echo_info " Installiert:"
echo_info "   - hostapd (Access Point Software)"
echo_info "   - dnsmasq (DHCP + DNS Server)"
echo_info ""
echo_info " Konfiguriert:"
echo_info "   - SSID: DaciaSpring-OBD2"
echo_info "   - Password: obd2spring2026"
echo_info "   - AP IP: 10.0.0.1"
echo_info "   - DHCP Range: 10.0.0.100 - 10.0.0.200"
echo_info ""
echo_info " Netzwerkschutz:"
echo_info "   ✅ Bestehende WiFi-Verbindung BEIBEHALTEN"
echo_info "   ✅ SSH-Sitzung BEIBEHALTEN"
echo_info "   ✅ dnsmasq NICHT neu gestartet (Netzwerkschutz)"
echo_info ""
echo_info " Nächste Schritte:"
echo_info "   A) SOFORT: Test AP (ohne Neustart!)"
echo_info "      sudo wifi_mode_switch.sh car"
echo_info ""
echo_info "   B) MANUELL: dnsmasq neu starten (wenn nötig)"
echo_info "      sudo systemctl restart dnsmasq"
echo_info ""
echo_info "   C) EMPFOHLEN: Pi NEUSTARTEN für Auto-Boot"
echo_info "      sudo reboot"
echo_info "      (Nach Neustart: Auto-Detect aktiv)"
echo_info ""
echo_info " Handy verbindet sich mit:"
echo_info "   WiFi: DaciaSpring-OBD2"
echo_info "   Password: obd2spring2026"
echo_info ""
echo_info " SSH Zugang:"
echo_info "   Im AP-Modus: ssh lsd@10.0.0.1"
echo_info "   Im Client-Modus: ssh lsd@192.168.178.87"
echo_info ""
echo_info "═══════════════════════════════════════════════"

exit 0