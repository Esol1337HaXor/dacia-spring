#!/bin/bash
# ============================================================
# wlan0 AP Start Script fuer DaciaSpring-OBD2
# Fuer RTL8188EUS (wlan0 USB WiFi Adapter)
# ============================================================
set -e

echo "============================================================"
echo "  wlan0 AP Start — DaciaSpring-OBD2"
echo "============================================================"

# 1. wlan0 IP setzen
echo "[1/4] wlan0 IP auf 10.0.0.1 setzen..."
sudo ip addr add 10.0.0.1/24 dev wlan0 2>/dev/null || true
echo "  OK wlan0 IP: 10.0.0.1"

# 2. hostapd Config erstellen (RTL8188EUS — Treiber rtl871xdrv)
echo "[2/4] hostapd Config erstellen..."
sudo tee /etc/hostapd/hostapd-wlan0.conf > /dev/null << 'EOF'
interface=wlan0
driver=rtl871xdrv
ssid=DaciaSpring-OBD2
hw_mode=g
channel=6
wpa=2
psk=dacia-spring-2026
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP CCMP
rsn_pairwise=CCMP TKIP
EOF
echo "  OK hostapd Config"

# 3. dnsmasq Config erstellen
echo "[3/4] dnsmasq Config erstellen..."
sudo tee /etc/dnsmasq-ap.conf > /dev/null << 'EOF'
interface=wlan0
dhcp-range=10.0.0.100,10.0.0.200,255.255.255.0,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
bind-interfaces
EOF
echo "  OK dnsmasq Config"

# 4. hostapd + dnsmasq starten
echo "[4/4] hostapd + dnsmasq starten..."
sudo pkill hostapd 2>/dev/null || true
sudo pkill dnsmasq 2>/dev/null || true
sleep 1

sudo hostapd -B /etc/hostapd/hostapd-wlan0.conf
sleep 2

sudo dnsmasq --conf-file=/etc/dnsmasq-ap.conf
sleep 1

# 5. Status
echo ""
echo "============================================================"
echo "  OK AP GESTARTET"
echo "============================================================"
echo ""
echo "  WiFi:  DaciaSpring-OBD2"
echo "  PW:    dacia-spring-2026"
echo "  IP:    10.0.0.1"
echo "  DHCP:  10.0.0.100-200"
echo ""
echo "  Status pruefen:"
echo "    iw dev wlan0 station list"
echo "    pgrep -a hostapd"
echo "    pgrep -a dnsmasq"
echo "    ip addr show wlan0 | grep 10"
echo "============================================================"