#!/bin/bash
cd /home/lsd/obd2-adapter
sudo python3 bt_spp_server.py > /home/lsd/obd2-adapter/bt_running.log 2>&1 &
echo "Server PID: $!"
sleep 2
cat /home/lsd/obd2-adapter/bt_running.log