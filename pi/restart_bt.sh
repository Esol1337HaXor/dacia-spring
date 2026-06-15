#!/bin/bash
# Kill old processes
pkill -9 -f bt_spp_server
sleep 2

# Bluetooth setup
hciconfig hci0 piscan
hciconfig hci0 name "PiZeroCar-OBD2"
bluetoothctl discoverable on 2>/dev/null
bluetoothctl pairable on 2>/dev/null

# Start server
cd /home/lsd/obd2-adapter
nohup python3 bt_spp_server.py > bt_server.log 2>&1 &
sleep 3

# Show log
cat bt_server.log
echo "=== PROCESS CHECK ==="
ps aux | grep bt_spp | grep -v grep