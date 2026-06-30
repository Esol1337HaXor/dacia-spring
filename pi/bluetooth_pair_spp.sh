#!/bin/bash
#
# Bluetooth Pairing + SPP Test für vGate iCar Pro BT
#
# Das Android-Vlink Signal (13:E0:2F:8D:61:07) ist BLUETOOTH CLASSIC
# Es MUSS GEPARED sein bevor SPP/RFCOMM funktioniert!

set -e

VGLITE_MAC="13:E0:2F:8D:61:07"
VGLITE_IOS_MAC="D2:E0:2F:8D:61:07"

echo "=============================================="
echo "VGLITE iCAR PRO BT — PAIRING + SPP TEST"
echo "=============================================="
echo ""

# Step 1: Bluetooth Status
echo "[1/6] Bluetooth Status..."
bluetoothctl list
echo ""

# Step 2: Enable Bluetooth
echo "[2/6] Bluetooth aktivieren..."
bluetoothctl power on
bluetoothctl scan on
sleep 3
bluetoothctl scan off
echo ""

# Step 3: Check existing pairing
echo "[3/6] Vorhandene Pairs prüfen..."
bluetoothctl info "$VGLITE_MAC" 2>&1 | grep -i "paired\|alias\|trusted" || echo "NICHT GEPARED!"
echo ""

# Step 4: Pair with Android-Vlink
echo "[4/6] Pair mit Android-Vlink ($VGLITE_MAC)..."
# bluetoothctl interaktiv: pair + trust + connect
cat << EOF | bluetoothctl
pair $VGLITE_MAC
trust $VGLITE_MAC
connect $VGLITE_MAC
EOF
echo ""

# Step 5: Try RFCOMM SPP
echo "[5/6] RFCOMM SPP Test nach Pairing..."
timeout 5 bash -c 'echo -e "ATZ\r" | nc -w 2 13:E0:2F:8D:61:07 1 2>&1' || echo "Channel 1: Connection refused/timeout"
echo ""

# Step 6: Show all devices
echo "[6/6] Alle Bluetooth Geräte:"
bluetoothctl devices
echo ""

echo "=============================================="
echo "TEST ABGESCHLOSSEN"
echo "=============================================="