#!/bin/bash
# Fix Bluetooth Agent für Pairing
echo "=== Bluetooth Agent Fix ==="

# 1. Alten Agent deaktivieren
echo -e "remove-device B8:27:EB:F3:C7:61" | bluetoothctl 2>/dev/null

# 2. Agent auf PinCode setzen
echo -e "agent PinCode\ndefault-agent" | bluetoothctl 2>&1

# 3. Discoverable + Pairable
echo -e "discoverable on\npairable on" | bluetoothctl 2>&1

echo "=== Agent gesetzt auf PinCode ==="
echo "PIN für Pairing: 1234"