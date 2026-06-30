#!/usr/bin/env python3
"""
Sucht alle aktuellen Bluetooth-Geräte auf dem Raspberry Pi.
Findet vGate iCar Pro mit RFCOMM-Test.
"""
import subprocess
import time

def run_cmd(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr)
    except:
        return ""

def main():
    print("=" * 60)
    print("Bluetooth-Geräte Suche")
    print("=" * 60)
    
    # 1. bluetoothctl scan
    print("\n[1] bluetoothctl devices (ohne Scan):")
    print("-" * 40)
    out = run_cmd("bluetoothctl devices")
    print(out if out.strip() else "(kein Output)")
    
    # 2. bluetoothctl paired-devices
    print("\n[2] bluetoothctl paired-devices:")
    print("-" * 40)
    out = run_cmd("bluetoothctl paired-devices")
    print(out if out.strip() else "(kein Output)")
    
    # 3. hcitool lescan - aktiv suchen
    print("\n[3] hcitool lescan --passive (10s Scan):")
    print("-" * 40)
    try:
        r = subprocess.run(
            "sudo hcitool lescan --passive --duplicate",
            shell=True, capture_output=True, text=True, timeout=12
        )
        print(r.stdout if r.stdout.strip() else "(kein Output)")
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        print(f"Fehler: {e}")
    
    # 4. bluetoothctl scan on (kurz)
    print("\n[4] bluetoothctl scan on (5s):")
    print("-" * 40)
    try:
        p = subprocess.Popen(
            "bluetoothctl << 'EOF'\nscan on\nEOF\n",
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        time.sleep(3)
        p.terminate()
        out, _ = p.communicate(timeout=2)
        print(out if out.strip() else "(kein Output)")
    except Exception as e:
        print(f"Fehler: {e}")
    
    # 5. rfcomm list
    print("\n[5] rfcomm show:")
    print("-" * 40)
    out = run_cmd("rfcomm show")
    print(out if out.strip() else "(kein Output)")
    
    print("\n" + "=" * 60)
    print("SCAN ABGESCHLOSSEN")
    print("=" * 60)
    print("\nBitte geben Sie die MAC-Adresse des vGate iCar Pro ein")
    print("das gerade am Pi verbunden ist.")

if __name__ == "__main__":
    main()