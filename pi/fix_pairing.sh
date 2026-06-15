#!/bin/bash
# Fix Bluetooth pairing - PIN Agent konfigurieren
echo "=== Bluetooth Pairing Fix ==="

# Agent auf PinCode setzen (erlaubt 4-stellige PINs)
echo -e "agent PinCode\ndefault-agent" | bluetoothctl

# Pairable auf yes setzen
echo -e "pairable on" | bluetoothctl

# Discoverable auf on setzen
echo -e "discoverable on" | bluetoothctl

echo "Agent konfiguriert!"
echo "PIN: 1234"