#!/bin/bash
# Startet den neuen SPP TCP Server auf Port 2117
# Stoppt vorher alle alten Server

echo "=== Alte Server stoppen ==="
sudo pkill -f elm327_tcp_server_ble.py 2>/dev/null || true
sudo pkill -f spp_tcp_server.py 2>/dev/null || true
sleep 2

echo "=== Ports prüfen ==="
sudo ss -tlnp | grep :211 || echo "Ports 2117/2118 frei"

echo "=== Neuen SPP Server starten ==="
cd ~/obd2-adapter
sudo python3 spp_tcp_server.py > /tmp/spp_server.log 2>&1 &
SERVER_PID=$!
echo "Server gestartet (PID: $SERVER_PID)"

sleep 3

echo "=== Server Status ==="
sudo ss -tlnp | grep :211
echo ""
echo "=== Log (letzte 20 Zeilen) ==="
sudo tail -20 /tmp/spp_server.log