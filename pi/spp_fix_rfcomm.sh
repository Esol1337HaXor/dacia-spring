#!/bin/bash
#
# rfcomm0 neu erstellen + SPP Test
#

echo "=============================================="
echo "RFCOMM0 NEU ERSTELLEN + SPP TEST"
echo "=============================================="
echo ""

# Step 1: Alten rfcomm0 freigeben
echo "[1/4] Alten rfcomm0 freigeben..."
sudo rfcomm release /dev/rfcomm0 2>/dev/null || echo "  (kein alter rfcomm0 gefunden)"
sudo rm -f /dev/rfcomm0
echo "  ✅ rfcomm0 entfernt"
echo ""

# Step 2: Neu binden
echo "[2/4] Neu binden zu 13:E0:2F:8D:61:07 Channel 1..."
sudo rfcomm bind /dev/rfcomm0 13:E0:2F:8D:61:07 1
echo "  ✅ rfcomm0 neu gebunden"
echo ""

# Step 3: Status prüfen
echo "[3/4] Status prüfen..."
echo "  Device:"
ls -la /dev/rfcomm0
echo ""
echo "  rfcomm show:"
rfcomm show
echo ""

# Step 4: Verbindung testen
echo "[4/4] SPP Test mit minicom/screen..."
echo "  Option A: screen (9600 baud)"
echo "    sudo screen /dev/rfcomm0 9600"
echo "    Tippe: ATZ"
echo "    Beenden: STRG+A dann STRG+D"
echo ""
echo "  Option B: Python Test"
echo "    sudo python3 /home/lsd/obd2-adapter/spp_elm327_test.py"
echo ""

echo "=============================================="
echo "RFCOMM0 NEU ERSTELLT"
echo "=============================================="