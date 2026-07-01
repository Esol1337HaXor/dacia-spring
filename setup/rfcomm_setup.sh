#!/bin/bash
#
# RFCOMM Device /dev/rfcomm0 neu erstellen
#
# Wird nach jedem Neustart benötigt, da rfcomm0 nicht persistent ist
#
# Verwendung: sudo bash rfcomm_setup.sh
#

VGLITE_MAC="13:E0:2F:8D:61:07"

echo "=============================================="
echo "RFCOMM Device neu erstellen"
echo "=============================================="
echo ""

# Alten rfcomm0 freigeben
echo "[1/2] Alten rfcomm0 freigeben..."
sudo rfcomm release /dev/rfcomm0 2>/dev/null || echo "  (kein alter rfcomm0 gefunden)"
sudo rm -f /dev/rfcomm0
echo "   ✓ rfcomm0 entfernt"
echo ""

# Neu binden
echo "[2/2] Neu binden zu $VGLITE_MAC Channel 1..."
sudo rfcomm bind /dev/rfcomm0 "$VGLITE_MAC" 1
echo "   ✓ /dev/rfcomm0 erstellt"
echo ""

echo "=============================================="
echo "RFCOMM Device bereit"
echo "=============================================="
echo ""
echo "Server neu starten: sudo systemctl restart spp-elm327-server"