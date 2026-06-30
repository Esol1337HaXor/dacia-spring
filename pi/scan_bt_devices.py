#!/usr/bin/env python3
"""
Scan für Bluetooth-Geräte auf dem Raspberry Pi.
Findet gepairte Geräte und prüft ob vGate iCar Pro erreichbar ist.
"""
import subprocess
import sys

def list_bluetooth_devices():
    """Listet alle Bluetooth-Geräte."""
    print("=" * 60)
    print("Bluetooth-Geräte Scan")
    print("=" * 60)
    
    # 1. bluetoothctl devices
    print("\n[1/3] bluetoothctl devices:")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout + result.stderr
        print(output if output.strip() else "(kein Output)")
    except Exception as e:
        print(f"Fehler: {e}")
    
    # 2. bluetoothctl paired-devices
    print("\n[2/3] bluetoothctl paired-devices:")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["bluetoothctl", "paired-devices"],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout + result.stderr
        print(output if output.strip() else "(kein Output)")
    except Exception as e:
        print(f"Fehler: {e}")
    
    # 3. hcitool lelist
    print("\n[3/3] hcitool lescan (5 Sekunden Scan):")
    print("-" * 40)
    try:
        result = subprocess.run(
            ["sudo", "hcitool", "lescan", "--le", "--duplicate", "--passive"],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout + result.stderr
        print(output if output.strip() else "(kein Output)")
    except subprocess.TimeoutExpired:
        print("(Scan abgeschlossen nach 10s)")
    except Exception as e:
        print(f"Fehler: {e}")

def check_vlink_mac():
    """Prüft bekannte IOS-Vlink MAC-Adressen."""
    print("\n" + "=" * 60)
    print("Bekannte MAC-Adressen prüfen:")
    print("=" * 60)
    
    known_macs = [
        "D2:E0:2F:8D:61:07",  # IOS-Vlink
        "D2:E0:2F:8D:61:08",  # Möglicher vGate
        "D2:E0:2F:8D:61:09",  # Möglicher vGate
    ]
    
    # hcitool con prüfen
    try:
        result = subprocess.run(
            ["bluetoothctl", "info", "--details"],
            capture_output=True, text=True, timeout=5
        )
        print(f"hcitool con: {result.stdout or result.stderr}")
    except:
        pass
    
    for mac in known_macs:
        print(f"\n  MAC: {mac}")
        # Prüfen ob Gerät antwortet (kurzer TCP-Connect-Test auf Port 3)
        import socket
        try:
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, 3)
            sock.settimeout(2.0)
            sock.connect((mac, 1))  # RFCOMM Channel 1
            print(f"    ✅ vGate iCar Pro {mac} ist ERREICHBAR!")
            sock.close()
        except Exception as e:
            print(f"    ❌ {mac} nicht erreichbar: {type(e).__name__}")

if __name__ == "__main__":
    list_bluetooth_devices()
    check_vlink_mac()
    print("\n✅ Scan abgeschlossen!")