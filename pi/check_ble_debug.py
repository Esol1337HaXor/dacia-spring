#!/usr/bin/env python3
"""Debug: Prüft ob BLE Notify Antworten liefert."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ble_client_vgate import VgateBLEClient
import asyncio

async def test():
    print("=" * 50)
    print("BLE Notify Debug Test")
    print("MAC: D2:E0:2F:8D:61:07")
    print("=" * 50)
    
    # Manuell ohne Init-Kommandos
    from bleak import BleakClient
    VLINK_CHAR_UUID = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"
    
    answers = []
    
    def notify_handler(sender, data):
        text = data.decode("utf-8", errors="replace")
        answers.append(text)
        print(f"  📨 NOTIFY: {text!r}")
    
    print("\n[1/4] Verbinde zu BLE...")
    async with BleakClient("D2:E0:2F:8D:61:07") as client:
        print("  ✅ Connected!")
        
        print("\n[2/4] Starte Notify...")
        await client.start_notify(VLINK_CHAR_UUID, notify_handler)
        await asyncio.sleep(0.5)
        
        print("\n[3/4] Sende ATE0 (Echo aus)...")
        await client.write_gatt_char(VLINK_CHAR_UUID, b"ATE0\r")
        await asyncio.sleep(0.5)
        
        print("\n[4/4] Sende 010D (Speed)...")
        answers.clear()
        await client.write_gatt_char(VLINK_CHAR_UUID, b"010D\r")
        await asyncio.sleep(1.0)
        
        if answers:
            print(f"\n✅ Antworten erhalten ({len(answers)}):")
            for a in answers:
                print(f"  {a!r}")
        else:
            print("\n❌ Keine BLE Notify Antworten!")
        
        print("\n[5/5] Sende 0100 (PIDs)...")
        answers.clear()
        await client.write_gatt_char(VLINK_CHAR_UUID, b"0100\r")
        await asyncio.sleep(1.0)
        
        if answers:
            print(f"✅ Antworten ({len(answers)}):")
            for a in answers:
                print(f"  {a!r}")
        
        await client.stop_notify(VLINK_CHAR_UUID)

    print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test())