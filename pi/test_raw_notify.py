#!/usr/bin/env python3
"""
Raw Notify Tester — Zeigt ALLE BLE Notify-Daten ohne Filter.

Auf dem Pi ausfuehren:
  cd ~/obd2-adapter
  source ~/obd2-adapter-env/bin/activate
  python3 test_raw_notify.py
"""

import asyncio
import time
from bleak import BleakClient

# Vlink iCar Pro Konfiguration
MAC = "D2:E0:2F:8D:61:07"

# Korrekte UUIDs aus ble_client_vgate.py
SERVICE_UUID = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
CHAR_UUID = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"


def raw_notify_handler(sender, data):
    """Zeigt ALLE raw Notify-Daten."""
    # Hex-Darstellung
    hex_str = ' '.join(f'{b:02X}' for b in data)
    
    # Text-Darstellung (druckbare Zeichen)
    text_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
    
    print(f"NOTIFY ({len(data)} bytes):")
    print(f"  Hex: {hex_str}")
    print(f"  Text: {text_str}")
    print()


async def test_raw_notify():
    """Testet raw Notify mit der korrekten UUID."""
    
    print("=" * 70)
    print("  Raw Notify Tester")
    print(f"  Ziel MAC: {MAC}")
    print(f"  Service UUID: {SERVICE_UUID}")
    print(f"  Characteristic UUID: {CHAR_UUID}")
    print("=" * 70)
    print()
    
    try:
        print(f"Verbinde zu {MAC}...")
        async with BleakClient(MAC) as client:
            print("Verbunden!")
            
            # Alle Services und Characteristics auflisten
            print("\nServices und Characteristics:")
            for service in client.services:
                print(f"  Service: {service.uuid}")
                for char in service.characteristics:
                    props = char.properties
                    props_str = []
                    if 'read' in props: props_str.append('READ')
                    if 'write' in props: props_str.append('WRITE')
                    if 'write_without_response' in props: props_str.append('WRITE_NO_RESP')
                    if 'write_nr' in props: props_str.append('WRITE_NR')
                    if 'notify' in props: props_str.append('NOTIFY')
                    if 'indicate' in props: props_str.append('INDICATE')
                    print(f"    Char: {char.uuid} ({', '.join(props_str)})")
            print()
            
            print(f"Richte Notify ein fuer: {CHAR_UUID}")
            await client.start_notify(CHAR_UUID, raw_notify_handler)
            print("Notify aktiv!")
            print()
            print("Warte 15 Sekunden auf Daten...")
            print("(Fahrzeug auf READY stellen!)")
            print()
            
            # 15 Sekunden warten
            start = time.time()
            while time.time() - start < 15:
                await asyncio.sleep(0.5)
                elapsed = time.time() - start
                print(f"\r  [{elapsed:.1f}s] ", end='', flush=True)
            
            print(f"\n\n15s gewartet - keine Notify-Daten gekommen (oder oben anzeigen)")
            
            # AT-Befehle senden und auf Antworten warten
            print()
            print("Sende AT-Befehle und warte auf Antwort...")
            
            at_commands = [
                ('ATZ\r', 'Reset ELM327'),
                ('ATE0\r', 'Echo aus'),
                ('ATH0\r', 'Header aus'),
                ('ATS0\r', 'Space aus'),
                ('ATSP0\r', 'Protokoll auto'),
                ('ATDPN\r', 'Detected Protocol Number'),
                ('0100\r', 'Supported PIDs 01-20'),
                ('010C\r', 'RPM'),
                ('010D\r', 'Speed'),
            ]
            
            for cmd, desc in at_commands:
                print(f"  Sende [{desc}]: {cmd.strip()}")
                await client.write_gatt_char(CHAR_UUID, cmd.encode())
                await asyncio.sleep(3.0)
            
            print()
            print("Warte nochmal 10 Sekunden auf letzte Antworten...")
            start = time.time()
            while time.time() - start < 10:
                await asyncio.sleep(0.5)
            
            print()
            print("=" * 70)
            print("  TEST VOLLSTANDIG")
            print("=" * 70)
            print()
            print("ZUSAMMENFASSUNG:")
            print(f"  - Connect: OK")
            print(f"  - Services gelistet: OK")
            print(f"  - Notify eingerichtet: OK")
            print(f"  - AT-Befehle gesendet: {len(at_commands)}")
            print()
            print("Pruefe die Ausgabe oben:")
            print("  - Waren NOTIFY-Eintraege dazwischen?")
            print("  - Wenn JA: Das sind die CAN-Frames!")
            print("  - Wenn NEIN: Fahrzeug nicht bereit oder kein CAN-Bus Data")
            print()
            
    except Exception as e:
        import traceback
        print(f"Fehler: {e}")
        traceback.print_exc()
    
    print("Fertig!")


if __name__ == "__main__":
    try:
        asyncio.run(test_raw_notify())
    except KeyboardInterrupt:
        print("\n\nTester gestoppt.")