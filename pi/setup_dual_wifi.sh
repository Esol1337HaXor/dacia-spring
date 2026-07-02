#!/bin/bash
# ============================================================
# Dual-WiFi Setup fuer Pi Zero 2W
# wlan1 (USB RTL8188EUS) → Client zu WaggumAirport
# wlan0 (integrated) → AP "DaciaSpring-OBD2"
# ============================================================
set -e

echo "============================================================"
echo "  Dual-WiFi Setup - wlan1 Client + wlan0 AP"
echo "============================================================"

# ----------------------------------------
# SCHRITT 1: wlan1 als Client konfigurieren
# ----------------------------------------
echo ""
echo "[1/5] wlan1 als Client zu WaggumAirport konfigurieren..."

# wpa_supplicant Config erstellen
sudo tee /etc/wpa_supplicant/wpa_supplicant-wlan1.conf > /dev/null << 'EOF'
ctrl_interface=DIR=/run/wpa_supplicant GROUP=netdev
country=DE
network={
    ssid="WaggumAirport"
    psk="DankefuermeineArbeitsstelle"
    key_mgmt=WPA-PSK
}
EOF

# Alten wpa_supplicant killen
sudo pkill -9 wpa_supplicant 2>/dev/null || true
sudo rm -f /run/wpa_supplicant/*

# wlan1 hochfahren
sudo ip link set wlan1 up

# wpa_supplicant starten
sudo wpa_supplicant -B -i wlan1 -c /etc/wpa_supplicant/wpa_supplicant-wlan1.conf
sleep 5

# DHCP Client starten
sudo dhcpcd wlan1 2>/dev/null || true
sleep 3

WLAN1_IP=$(ip addr show wlan1 | grep "inet " | awk '{print $2}' | cut -d/ -f1)
echo "  ✓ wlan1 verbunden: ${WLAN1_IP:-'pruefe manuell'}"
sudo iw dev wlan1 link 2>/dev/null | head -3 || true

# ----------------------------------------
# SCHRITT 2: wlan0 als AP vorbereiten
# ----------------------------------------
echo ""
echo "[2/5] wlan0 als AP vorbereiten..."

# wlan0 IP setzen
sudo ip addr add 10.0.0.1/24 dev wlan0 2>/dev/null || true
sudo ip link set wlan0 up
echo "  ✓ wlan0 IP: 10.0.0.1"

# ----------------------------------------
# SCHRITT 3: hostapd Config erstellen
# ----------------------------------------
echo ""
echo "[3/5] hostapd Config erstellen..."

sudo tee /etc/hostapd/hostapd.conf > /dev/null << 'EOF'
interface=wlan0
driver=nl80211
ssid=DaciaSpring-OBD2
hw_mode=g
channel=6
wpa=2
wpa_passphrase=dacia-spring-2026
wpa_key_mgmt=WPA-PSK
wpa_pair_pattern=TKIP
rsn_pair_pattern=CCMP
auth_algs=1
ignore_broadcast_ssid=0
EOF

echo "  ✓ hostapd Config: /etc/hostapd/hostapd.conf"

# ----------------------------------------
# SCHRITT 4: dnsmasq Config erstellen
# ----------------------------------------
echo ""
echo "[4/5] dnsmasq Config erstellen..."

sudo tee /etc/dnsmasq-ap.conf > /dev/null << 'EOF'
interface=wlan0
dhcp-range=10.0.0.100,10.0.0.200,255.255.255.0,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
bind-interfaces
EOF

echo "  ✓ dnsmasq Config: /etc/dnsmasq-ap.conf"

# ----------------------------------------
# SCHRITT 5: hostapd + dnsmasq starten
# ----------------------------------------
echo ""
echo "[5/5] hostapd + dnsmasq starten..."

# Alten hostapd killen
sudo pkill -9 hostapd 2>/dev/null || true
sudo pkill -9 dnsmasq 2>/dev/null || true

# hostapd starten
sudo /tmp/wpa-2.10/hostapd/hostapd -B /etc/hostapd/hostapd.conf
sleep 2

# dnsmasq starten
sudo dnsmasq --conf-file=/etc/dnsmasq-ap.conf
sleep 1

# ----------------------------------------
# ZUSAMMENFASSUNG
# ----------------------------------------
echo ""
echo "============================================================"
echo "  ✓ SETUP ABGESCHLOSSEN"
echo "============================================================"
echo ""
echo "  wlan1 (USB):  ${WLAN1_IP:-dynamic} ← WaggumAirport"
echo "  wlan0 (INT):  10.0.0.1 ← AP: DaciaSpring-OBD2"
echo "  AP DHCP:      10.0.0.100-200"
echo "  AP Passwort:  dacia-spring-2026"
echo ""
echo "  OBD2 Server:  10.0.0.1:2117 (ueber AP erreichbar)"
echo "  SSH ueber:    ${WLAN1_IP:-192.168.178.x}:22"
echo ""
echo "  Status pruefen:"
echo "    iw dev wlan0 info   → AP sollte 'type AP' zeigen"
echo "    iw client list      → verbundene Clients"
echo "    pgrep -a hostapd    → hostapd laeuft"
echo "    pgrep -a dnsmasq    → dnsmasq laeuft"
echo "============================================================"