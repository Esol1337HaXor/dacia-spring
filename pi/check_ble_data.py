#!/usr/bin/env python3
"""Prüft ob der BLE-Client echte OBD2-Daten vom Fahrzeug liefert."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ble_client_vgate import VgateBLEClient
import asyncio

async def test():
    print("=" * 50)
    print("BLE Live-Daten Test")
    print("MAC: D2:E0:2F:8D:61:07")
    print("=" * 50)
    
    client = VgateBLEClient("D2:E0:2F:8D:61:07", debug=True)
    await client.start()
    
    print("\n✅ BLE verbunden!")
    print("\nWarte auf OBD2-Daten (10 Sekunden)...\n")
    
    # 10 Sekunden warten und Daten loggen
    for i in range(20):
        await asyncio.sleep(0.5)
        
        speed = client.obd_data.speed
        rpm = client.obd_data.rpm
        load = client.obd_data.engine_load
        coolant = client.obd_data.coolant_temp
        
        print(f"  [{i*0.5:5.1f}s] Speed: {speed:6.1f} km/h | "
              f"RPM: {rpm:6.0f} | Load: {load:5.1f}% | "
              f"Kühlung: {coolant:4.0f}°C")
        
        # Wenn echte Daten da sind, abbrechen
        if speed > 0 or rpm > 0:
            print("\n✅ Echte Fahrzeugdaten empfangen!")
            break
    
    # Stop und zeige finale Daten
    await client.stop()
    
    print("\n" + "=" * 50)
    print("Finale OBD2-Daten:")
    print(f"  Speed:    {client.obd_data.speed:.1f} km/h")
    print(f"  RPM:      {client.obd_data.rpm:.0f}")
    print(f"  Engine:   {client.obd_data.engine_load:.1f}%")
    print(f"  Kühlung:  {client.obd_data.coolant_temp:.0f}°C")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test())