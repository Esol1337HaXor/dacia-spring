#!/bin/bash
#
# vGate iCar Pro BT — Pairing Status prüfen + Pairing durchführen
#
# Prueft ob Pairing mit Android-Vlink (13:E0:2F:8D:61:07) besteht
# Falls nein: Fuehrt interaktives Pairing durch
#

VGLITE_ANDROID_MAC="13:E0:2F:8D:61:07"
VGLITE_IOS_MAC="D2:E0:2F:8D:61:07"

echo "=============================================="
echo "VGLITE iCAR PRO BT — PAIRING STATUS PRUEFEN"
echo "=============================================="
echo ""
echo "Android-Vlink MAC: $VGLITE_ANDROID_MAC"
echo "IOS-Vlink MAC:     $VGLITE_IOS_MAC"
echo ""

# Step 1: BLE Scan — Sind beide Gerate noch sichtbar?
echo "[1/4] BLE Scan — Sind beide Gerate sichtbar?"
echo "  (Bitte 5 Sekunden warten...)"
bluetoothctl scan on
sleep 5
bluetoothctl scan off

echo ""
echo "  GEFUNDENE GERATE:"
bluetoothctl devices 2>/dev/null | grep -i "vlink\|Vlink" || echo "  (keine Vlink-Gerate gefunden)"
echo ""

# Step 2: Pairing Status pruefen
echo "[2/4] Pairing-Status pruefen..."
echo ""

# Info abrufen (ohne interactive prompts)
INFO_ANDROID=$(bluetoothctl info "$VGLITE_ANDROID_MAC" 2>&1)

if echo "$INFO_ANDROID" | grep -q "Paired: yes"; then
    echo "  ✅ ANDROID-VLINK: BEREITS GEPARED!"
    echo "     $(echo "$INFO_ANDROID" | grep -i 'alias\|uuid\|manufacturer')"
elif echo "$INFO_ANDROID" | grep -q "Paired: no"; then
    echo "  ⚠️  ANDROID-VLINK: Gefunden ABER NICHT GEPARED"
else
    echo "  ❓ ANDROID-VLINK: Nicht in Device-Liste"
fi
echo ""

INFO_IOS=$(bluetoothctl info "$VGLITE_IOS_MAC" 2>&1)
if echo "$INFO_IOS" | grep -q "Paired: yes"; then
    echo "  ✅ IOS-VLINK: BEREITS GEPARED!"
elif echo "$INFO_IOS" | grep -q "Paired: no"; then
    echo "  ⚠️  IOS-VLINK: Gefunden ABER NICHT GEPARED"
else
    echo "  ❓ IOS-VLINK: Nicht in Device-Liste"
fi
echo ""

# Step 3: RFCOMM Status pruefen
echo "[3/4] RFCOMM Device pruefen..."
if [ -e /dev/rfcomm0 ]; then
    echo "  ✅ /dev/rfcomm0 existiert"
    ls -la /dev/rfcomm0
else
    echo "  ❌ /dev/rfcomm0 existiert NICHT"
fi
echo ""

# Step 4: Pairing durchfuehren oder SPP testen
echo "[4/4] NAECHSTE SCHRITTE"
echo "=============================================="
echo ""

if echo "$INFO_ANDROID" | grep -q "Paired: yes"; then
    echo "  ✅ Pairing besteht bereits!"
    echo ""
    echo "  SPP-Test mit rfcomm starten:"
    echo "    sudo rfcomm bind /dev/rfcomm0 $VGLITE_ANDROID_MAC 1"
    echo "    sudo python3 /home/lsd/obd2-adapter/bt_spp_test.py"
    echo ""
else
    echo "  ⚠️  KEIN Pairing — Manuelles Pairing erforderlich!"
    echo ""
    echo "  PAIRING ANLEITUNG:"
    echo "  1. bluetoothctl starten:"
    echo "       sudo bluetoothctl"
    echo ""
    echo "  2. Im bluetoothctl Prompt:"
    echo "       [bluetooth]# trust $VGLITE_ANDROID_MAC"
    echo "       [bluetooth]# pair $VGLITE_ANDROID_MAC"
    echo ""
    echo "  3. PIN falls gefragt: 1234 oder 0000"
    echo ""
    echo "  4. Nach erfolgreichem Pairing:"
    echo "       [bluetooth]# connect $VGLITE_ANDROID_MAC"
    echo ""
    echo "  5. Dann SPP-Test:"
    echo "       sudo rfcomm bind /dev/rfcomm0 $VGLITE_ANDROID_MAC 1"
    echo "       sudo screen /dev/rfcomm0 9600"
    echo "       # ELM327 Command testen:"
    echo "       ATZ"
    echo ""
fi

echo "=============================================="
echo "STATUS-PRUEFUNG ABGESCHLOSSEN"
echo "=============================================="