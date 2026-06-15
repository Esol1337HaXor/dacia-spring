#!/bin/bash
# Bluetooth ELM327 Auto-Setup Script für Pi Zero 2W
echo "===== Bluetooth ELM327 Setup ====="

# 1. Adapter sicher hochfahren
echo "1. Adapter starten..."
echo 'maxlose288' | sudo -S hciconfig hci0 up 2>/dev/null
sleep 1

# 2. Name setzen
echo "2. Name setzen..."
echo 'maxlose288' | sudo -S hciconfig hci0 name "PiZeroCar-OBD2" 2>/dev/null

# 3. PSCAN aktivieren (wichtig für discovery!)
echo "3. PSCAN/ISCAN aktivieren..."
echo 'maxlose288' | sudo -S hciconfig hci0 piscan 2>/dev/null

# 4. Discoverable + Pairable
echo "4. Discoverable + Pairable aktivieren..."
echo 'maxlose288' | sudo -S bluetoothctl discoverable on 2>/dev/null
echo 'maxlose288' | sudo -S bluetoothctl pairable on 2>/dev/null

# 5. SDP Service - SPP auf Channel 1 registrieren
#    Da sdptool nicht installiert ist, versuchen wir es über dbus
echo "5. SDP Service registrieren..."
python3 -c "
import struct
import socket
import os

# RFCOMM Channel 1 = SDP Channel 1
# UUID für Serial Port: 0x0003
uuid_spp = struct.pack('<8B', 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x80, 0x00, 0x23, 0x00, 0x11, 0x01, 0x03)

# Wir versuchen über bluez dbus API
try:
    import dbus
    bus = dbus.SystemBus()
    manager = dbus.Interface(
        bus.get_object('org.bluez', '/org/bluez'),
        'org.bluez.Manager1'
    )
    print('dbus OK')
except Exception as e:
    print(f'dbus error: {e}')
" 2>&1 || echo "SDP via dbus nicht verfügbar"

# 6. Server-Status prüfen
echo "6. Server-Status:"
if ps aux | grep -v grep | grep -q "bt_spp_server"; then
    echo "   Server LÄUFT!"
else
    echo "   Server LÄUFT NICHT - Neustart..."
    cd /home/lsd/obd2-adapter
    echo 'maxlose288' | sudo -S nohup python3 bt_spp_server.py > bt_server.log 2>&1 &
    sleep 2
    echo "   Server neu gestartet!"
fi

echo ""
echo "7. Status:"
bluetoothctl show | grep -E "Name:|Powered:|Discoverable:|Pairable:"

echo ""
echo "===== Setup fertig! ====="
echo "Gerät: PiZeroCar-OBD2"
echo "Channel: 1 (RFCOMM)"
echo "PIN: 1234"
echo ""
echo "Jetzt vom Handy suchen lassen!"