#!/bin/bash
# =============================================================================
# WiFi Auto-Mode — Dacia Spring OBD2 Adapter
# =============================================================================
#
# SUPER EINFACH:
#   - Prüft ob Heimnetz (192.168.178.x) verfügbar
#   - ✅ Ja → Client-Modus (Pi ist zu Hause)
#   - ❌ Nein → AP-Modus (Pi ist im Auto)
#
# ZUSÄTZLICHE BEFEHLE:
#   wifi_mode_switch.sh activate_ap → Erzwingt AP bis zum Neustart
#   wifi_mode_switch.sh logs       → Zeigt aktuelle Logs
#   wifi_mode_switch.sh status      → Zeigt aktuellen Status
#   wifi_mode_switch.sh recovery    → Startet Pi zurück falls gesteckt
#
# KONFIGURATION:
AP_SSID="DaciaSpring-OBD2"
AP_PASSWORD="obd2spring2026"
AP_IP="10.0.0.1"
AP_CHANNEL="6"
AP_INTERFACE="wlan0"

LOG_FILE="/home/lsd/obd2-adapter/wifi_switch.log"
FORCE_AP_FILE="/tmp/dacia_force_ap"
SSH_BACKUP_PORT="2222"

# =============================================================================
# LOGGING — Saubere, strukturierte Logs
# =============================================================================

log_header() {
    echo "" | tee -a "$LOG_FILE"
    echo "=======================================================================" | tee -a "$LOG_FILE"
    echo "  [$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
    echo "=======================================================================" | tee -a "$LOG_FILE"
}

log_step() {
    echo "  ▶ $1" | tee -a "$LOG_FILE"
}

log_ok() {
    echo -e "  ✅ \033[0;32m$1\033[0m" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "  ⚠️  \033[1;33m$1\033[0m" | tee -a "$LOG_FILE"
}

log_err() {
    echo -e "  ❌ \033[0;31m$1\033[0m" | tee -a "$LOG_FILE"
}

log_info() {
    echo "  ℹ️  $1" | tee -a "$LOG_FILE"
}

# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

is_force_ap() {
    [ -f "$FORCE_AP_FILE" ]
}

show_logs() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║          WiFi Switch Logs — Dacia Spring                ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo ""
    if [ -f "$LOG_FILE" ]; then
        tail -50 "$LOG_FILE"
    else
        echo "  Keine Logs gefunden."
    fi
    echo ""
    echo "╚══════════════════════════════════════════════════════════╝"
}

show_status() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║        WiFi Status — Dacia Spring OBD2 Adapter           ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    
    local wlan0_ip=$(ip addr show wlan0 2>/dev/null | grep "inet 192\.168\.178" | head -1 | awk '{print $2}' | cut -d/ -f1)
    local ap_ip=$(ip addr show wlan0 2>/dev/null | grep "inet 10\.0\.0\." | head -1 | awk '{print $2}' | cut -d/ -f1)
    local hostapd_running="❌ GESTOPPT"
    pgrep hostapd > /dev/null 2>&1 && hostapd_running="✅ LÄUFT"
    local wpa_running="❌ NICHT LAUFEND"
    pgrep -a wpa_supplicant 2>/dev/null | grep -q wlan0 && wpa_running="✅ LÄUFT"
    local force_ap="❌ DEAKTIVIERT"
    is_force_ap && force_ap="✅ AKTIVIERT (bleibt bis Neustart)"
    
    echo ""
    echo "  wlan0 IP: ${wlan0_ip:-KEINE 192.168.178.x IP}"
    echo "  AP IP:    ${ap_ip:-KEINE AP-IP}"
    echo ""
    echo "  hostapd:  $hostapd_running"
    echo "  wpa_supp: $wpa_running"
    echo "  Force-AP: $force_ap"
    echo ""
    
    if [ -n "$wlan0_ip" ] || [ "$wpa_running" = "✅ LÄUFT" ]; then
        echo "  🏠 STATUS: CLIENT-MODUS (Heimnetz)"
        [ -n "$wlan0_ip" ] && echo "     → RevHeadz unter ${wlan0_ip%%/*}:2117"
    elif [ -n "$ap_ip" ] || [ "$hostapd_running" = "✅ LÄUFT" ]; then
        echo "  🚗 STATUS: AP-MODUS (Auto)"
        [ -n "$ap_ip" ] && echo "     → RevHeadz unter ${ap_ip%%/*}:2117"
    else
        echo "  ⚠️  STATUS: UNBEKANNT — WiFi-Dienste stoppen?"
    fi
    
    echo ""
    echo "╚══════════════════════════════════════════════════════════╝"
}

# =============================================================================
# HAUPTLOGIK: Prüfe ob Heimnetz verfügbar ist
# =============================================================================

determine_mode() {
    if is_force_ap; then
        return 1
    fi
    
    local wlan0_ip=$(ip addr show wlan0 2>/dev/null | grep "inet 192\.168\.178" | head -1 | awk '{print $2}' | cut -d/ -f1)
    if [ -n "$wlan0_ip" ]; then
        return 0
    fi
    
    if pgrep -a wpa_supplicant 2>/dev/null | grep -q wlan0; then
        return 0
    fi
    
    return 1
}

# =============================================================================
# CLIENT-MODUS
# =============================================================================
switch_to_client() {
    log_header "CLIENT-MODUS AKTIVIERT"
    log_step "Prüfe Heimnetz-Verfügbarkeit..."
    
    local wlan0_ip=$(ip addr show wlan0 2>/dev/null | grep "inet 192\.168\.178" | head -1 | awk '{print $2}' | cut -d/ -f1)
    
    if [ -n "$wlan0_ip" ]; then
        log_ok "Heimnetz verfügbar — Client-Modus AKTIV"
        log_info "Pi IP: $wlan0_ip"
        log_info "RevHeadz: ${wlan0_ip}:2117"
        log_info "SSH: ssh lsd@${wlan0_ip}"
        return 0
    else
        log_warn "Keine 192.168.178.x IP gefunden"
        log_info "Pi versucht noch zu verbinden..."
        return 1
    fi
}

# =============================================================================
# AP-MODUS — OHNE Interface-Delete (SSH fällt sonst weg!)
# =============================================================================
switch_to_ap() {
    log_header "AP-MODUS AKTIVIERT — Auto-Einsatz"
    
    # 0. RECOVERY: Falls Pi gesteckt — prüfe ob wir noch SSH haben
    # Wenn ja → weiter. Wenn nein → Pi muss manuell neu starten.
    
    # 1. ALLE WiFi-Dienste GRÜNDLICH stoppen (wichtig!)
    log_step "Stoppe ALLE WiFi-Dienste..."
    
    # wpa_supplicant GRÜNDLICH beenden
    sudo pkill -9 wpa_supplicant 2>/dev/null || true
    sudo pkill -9 hostapd 2>/dev/null || true
    sudo pkill -9 dnsmasq 2>/dev/null || true
    sleep 3
    
    # Verifizieren: Alle weg?
    if pgrep -x wpa_supplicant > /dev/null 2>&1; then
        log_warn "  wpa_supplicant läuft noch — forcieren..."
        sudo kill -9 $(pgrep -x wpa_supplicant) 2>/dev/null || true
        sleep 2
    fi
    
    if pgrep -x hostapd > /dev/null 2>&1; then
        log_warn "  hostapd läuft noch — forcieren..."
        sudo kill -9 $(pgrep -x hostapd) 2>/dev/null || true
        sleep 1
    fi
    
    log_ok "WiFi-Dienste gestoppt"
    
    # 2. IPs von wlan0 entfernen (NICHT Interface löschen!)
    log_step "Entferne alte IPs von wlan0..."
    sudo ip addr flush wlan0 2>/dev/null
    sleep 1
    log_ok "IPs entfernt"
    
    # 3. hostapd Config erstellen
    log_step "Erstelle hostapd Config..."
    sudo bash -c "cat > /etc/hostapd/hostapd.conf << EOF
interface=${AP_INTERFACE}
driver=nl80211
ssid=${AP_SSID}
hw_mode=g
channel=${AP_CHANNEL}
wmm_enabled=0

# WPA2 Verschlüsselung
wpa=2
wpa_passphrase=${AP_PASSWORD}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP

beacon_int=100
dtim_period=2
max_num_sta=10
EOF
"
    log_ok "hostapd Config erstellt"
    
    # 4. dnsmasq Config erstellen
    log_step "Erstelle dnsmasq Config..."
    sudo bash -c "cat > /etc/dnsmasq.conf << EOF
interface=${AP_INTERFACE}
bind-interfaces
dhcp-range=${AP_IP}.100,${AP_IP}.200,255.255.255.0,12h
dhcp-option=3,${AP_IP}
dhcp-option=6,${AP_IP}
EOF
"
    log_ok "dnsmasq Config erstellt"
    
    # 5. hostapd starten (JETZT wo wpa_supplicant weg ist!)
    log_step "Starte hostapd..."
    sudo /usr/sbin/hostapd -B /etc/hostapd/hostapd.conf 2>/dev/null
    sleep 2
    
    if pgrep hostapd > /dev/null; then
        log_ok "hostapd gestartet ✅"
    else
        log_err "hostapd Start fehlgeschlagen!"
        log_err "Der BCM43438-Chip könnte im Client-Modus stecken bleiben."
        log_err "RECOVERY: 'sudo reboot' auf dem Pi ausführen."
        return 1
    fi
    
    # 6. dnsmasq starten
    log_step "Starte dnsmasq..."
    sudo /usr/sbin/dnsmasq --conf-file=/etc/dnsmasq.conf 2>/dev/null || true
    log_ok "dnsmasq gestartet"
    
    # 7. Alte IPs ENTFERNEN + AP-IP zuweisen
    log_step "Weise AP-IP ${AP_IP}/24 zu..."
    sudo ip addr flush wlan0 2>/dev/null
    sudo ip addr add "${AP_IP}/24" dev "${AP_INTERFACE}" 2>/dev/null || true
    sleep 1
    log_ok "AP-IP zugewiesen"
    
    # 8. Ergebnis
    log_header "AP-MODUS ERFOLGREICH AKTIVIERT!"
    log_ok "SSID: ${AP_SSID}"
    log_ok "Password: ${AP_PASSWORD}"
    log_ok "Pi IP: ${AP_IP}"
    log_info "RevHeadz: ${AP_IP}:2117"
    log_info "Handy verbindet sich mit: ${AP_SSID}"
    log_info "SSH: ssh lsd@${AP_IP}"
    
    return 0
}

# =============================================================================
# RECOVERY: Falls Pi nach AP-Start nicht mehr erreichbar
# =============================================================================
recovery_mode() {
    log_header "RECOVERY — Pi zurücksetzen"
    log_info "Starte Pi neu um zum Heimnetz zurückzukehren..."
    sudo reboot
}

# =============================================================================
# HAUPTPROGRAMM
# =============================================================================

case "${1}" in
    "activate_ap")
        log_header "AP-MODUS ERZWINGEN BIS ZUM NÄCHSTEN NEUSTART"
        sudo touch "$FORCE_AP_FILE"
        log_ok "Force-AP Flag gesetzt!"
        log_info "Flag-Datei: $FORCE_AP_FILE"
        log_info "Löschen mit: sudo rm $FORCE_AP_FILE"
        log_info ""
        log_info "Nächster Boot entscheidet automatisch zwischen Client/AP."
        log_info "Bis dahin bleibt der Pi IMMER im AP-Modus!"
        log_header "JETZT AP STARTEN?"
        log_info "Führe 'wifi_mode_switch.sh' ohne Parameter aus."
        ;;
        
    "logs")
        show_logs
        ;;
        
    "status")
        show_status
        ;;
        
    "recovery")
        recovery_mode
        ;;
        
    "")
        log_header "WiFi Auto-Mode — Dacia Spring OBD2 Adapter"
        
        if determine_mode; then
            switch_to_client
        else
            switch_to_ap
        fi
        ;;
        
    *)
        echo "WiFi Auto-Mode — Dacia Spring OBD2 Adapter"
        echo ""
        echo "Verwendung:"
        echo "  wifi_mode_switch.sh          → Auto (Heimnetz=Client, sonst=AP)"
        echo "  wifi_mode_switch.sh activate_ap → Erzwingt AP bis Neustart"
        echo "  wifi_mode_switch.sh logs     → Zeigt Logs"
        echo "  wifi_mode_switch.sh status   → Zeigt Status"
        echo "  wifi_mode_switch.sh recovery → Startet Pi neu (Notfall)"
        ;;
esac

exit 0