#!/usr/bin/env python3
"""
BLE Android-Vlink Test — Testet das ANDROID-BLE-Signal vom vGate iCar Pro.

WICHTIG: Das Android-Vlink Signal hat MAC `13:E0:2F:8D:61:07` 
(nicht `D2:E0:2F:8D:61:07` — das ist das iOS-Signal!)

Das Android-Signal verwendet die vGate Standard UUIDs:
- Service: 0000ffe1-0000-1000-8000-00805f9b34fb
- Char:    0000ffe1-0000-1000-8000-00805f9b34fb

MUSS ALS ROOT AUSGEFÜHRT WERDEN!
"""
import asyncio
import sys
import logging
from datetime import datetime

import os
if os.geteuid() != 0:
    print("FEHLER: Script MUSS als root ausgeführt werden!")
    sys.exit(1)

from bleak import BleakScanner, BleakClient

# ============ KONFIGURATION — ANDROID-VLINK ============
ANDROID_VLINK_MAC = "13:E0:2F:8D:61:07"  # ← ANDROID-SIGNAL!
IOS_VLINK_MAC = "D2:E0:2F:8D:61:07"      # ← iOS-Signal (haben wir schon getestet)

# vGate Standard UUID (Android BLE)
VGLITE_SERVICE_ANDROID = "0000ffe1-0000-1000-8000-00805f9b34fb"
VGLITE_CHAR_ANDROID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Feasycom UUID (iOS BLE — haben wir schon getestet)
VGLITE_SERVICE_IOS = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
VGLITE_CHAR_IOS = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"

# Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Android-Vlink-Test")


class AndroidVlinkTest:
    """Testet das ANDROID-BLE-Signal vom vGate iCar Pro."""
    
    def __init__(self, mac: str):
        self.mac = mac
        self.client = None
        self.notification_count = 0
        self.raw_data = bytearray()
    
    async def notification_handler(self, sender, data: bytearray):
        """Notify-Callback."""
        self.notification_count += 1
        self.raw_data = data
        
        hex_str = ' '.join(f'{b:02X}' for b in data)
        ascii_str = data.decode('ascii', errors='replace')
        logger.info(f"📨 NOTIFY #{self.notification_count}:")
        logger.info(f"  HEX: {hex_str}")
        logger.info(f"  ASCII: {repr(ascii_str)}")
    
    async def connect_and_test(self):
        """Verbindet zum Android-Vlink und testet."""
        print("=" * 60)
        print("ANDROID-VLINK BLE TEST")
        print("=" * 60)
        print(f"\n📡 MAC: {self.mac}")
        print(f"📡 Service: {VGLITE_SERVICE_ANDROID}")
        print(f"📡 Char: {VGLITE_CHAR_ANDROID}")
        print(f"\n⏰ Start: {datetime.now()}")
        print("=" * 60)
        
        try:
            async with BleakClient(self.mac, timeout=10.0) as client:
                self.client = client
                logger.info("✅ BLE verbunden zum ANDROID-VLINK!")
                
                # Scan Services
                services = client.services
                logger.info(f"\n📋 Gefundene Services:")
                for svc in services:
                    logger.info(f"  Service: {svc.uuid}")
                    for ch in svc.characteristics:
                        props = str(ch.properties)
                        logger.info(f"    Char: {ch.uuid}")
                        logger.info(f"    Props: {props}")
                
                # Prüfe ob vGate UUID vorhanden
                has_vgate = any("ffe1" in str(svc.uuid) for svc in services)
                if has_vgate:
                    logger.info("\n✅ VGLITE UUID 0000ffe1 GEFUNDEN!")
                else:
                    logger.info("\n❌ VGLITE UUID 0000ffe1 NICHT GEFUNDEN!")
                
                # === TEST 1: Notify aktivieren ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST 1: Notify aktivieren")
                logger.info("=" * 60)
                
                # Finde vGate Characteristic
                vgate_char = None
                for svc in services:
                    if "ffe1" in str(svc.uuid):
                        for ch in svc.characteristics:
                            if "ffe1" in str(ch.uuid):
                                vgate_char = ch
                                break
                
                if vgate_char:
                    logger.info(f"  vGate Char gefunden: {vgate_char.uuid}")
                    await client.start_notify(vgate_char.uuid, self.notification_handler)
                    logger.info("  ✅ Notify aktiviert")
                else:
                    logger.info("  ❌ vGate Char nicht gefunden!")
                
                await asyncio.sleep(1.0)
                logger.info(f"  Notifications bisher: {self.notification_count}")
                
                # === TEST 2: ELM327 Commands ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST 2: ELM327 Commands senden")
                logger.info("=" * 60)
                
                commands = [
                    (b"ATZ\r", "ELM327 Reset"),
                    (b"ATI\r", "ELM327 Identify"),
                    (b"ATE0\r", "Echo OFF"),
                    (b"ATH0\r", "Header OFF"),
                    (b"ATS0\r", "Spaces OFF"),
                    (b"ATSP 0\r", "Protocol Auto"),
                ]
                
                for cmd, desc in commands:
                    logger.info(f"\n  📤 {desc}: {cmd}")
                    self.raw_data = bytearray()
                    
                    # Char finden für Write
                    write_char = vgate_char if vgate_char else VGLITE_CHAR_ANDROID
                    await client.write_gatt_char(write_char, cmd)
                    
                    # Auf Notify warten
                    await asyncio.sleep(1.0)
                    
                    if self.raw_data:
                        hex_str = ' '.join(f'{b:02X}' for b in self.raw_data)
                        ascii_str = self.raw_data.decode('ascii', errors='replace')
                        logger.info(f"  ✅ NOTIFY: {repr(ascii_str)}")
                        logger.info(f"      HEX: {hex_str}")
                    else:
                        logger.info(f"  ⏱️  Timeout — keine Notify-Daten")
                
                # === TEST 3: OBD2 PIDs ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST 3: OBD2 PIDs")
                logger.info("=" * 60)
                
                pids = [
                    (b"0100\r", "Supported PIDs"),
                    (b"010D\r", "Speed 010D"),
                    (b"010C\r", "RPM 010C"),
                    (b"222003\r", "Speed 222003"),
                    (b"22 20 03\r", "Speed 22 20 03"),
                    (b"22202E\r", "Throttle 22202E"),
                    (b"22 20 2E\r", "Throttle 22 20 2E"),
                    (b"223045\r", "Motor Speed"),
                    (b"229001\r", "Battery SOC"),
                ]
                
                for cmd, desc in pids:
                    logger.info(f"\n  📤 {desc}: {cmd}")
                    self.raw_data = bytearray()
                    
                    write_char = vgate_char if vgate_char else VGLITE_CHAR_ANDROID
                    await client.write_gatt_char(write_char, cmd)
                    
                    await asyncio.sleep(1.5)
                    
                    if self.raw_data:
                        hex_str = ' '.join(f'{b:02X}' for b in self.raw_data)
                        ascii_str = self.raw_data.decode('ascii', errors='replace')
                        logger.info(f"  ✅ NOTIFY: {repr(ascii_str)}")
                    else:
                        logger.info(f"  ⏱️  Timeout — keine Notify-Daten")
                
                # === TEST 4: Continuous Test ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST 4: Continuous Speed-Test (5s)")
                logger.info("=" * 60)
                
                for i in range(10):
                    self.raw_data = bytearray()
                    await client.write_gatt_char(VGLITE_CHAR_ANDROID, b"010D\r")
                    await asyncio.sleep(0.3)
                    
                    if self.raw_data:
                        ascii_str = self.raw_data.decode('ascii', errors='replace').strip()
                        logger.info(f"  #{i+1}: {repr(ascii_str)}")
                    else:
                        logger.info(f"  #{i+1}: (leer)")
                
                # === ZUSAMMENFASSUNG ===
                logger.info("\n" + "=" * 60)
                logger.info("ZUSAMMENFASSUNG")
                logger.info("=" * 60)
                logger.info(f"  Total Notifications: {self.notification_count}")
                
                if self.notification_count > 0:
                    logger.info(f"\n  ✅ ANDROID-VLINK FUNKTIONIERT!")
                    logger.info(f"  → Kann Daten via Notify empfangen!")
                else:
                    logger.info(f"\n  ⚠️  ANDROID-VLINK SENDET AUCH KEINE NOTIFYS!")
                    logger.info(f"  → Versuche READ-Methode...")
                
                logger.info(f"\n⏰ Ende: {datetime.now()}")
                
        except Exception as e:
            logger.error(f"\n❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ Test abgeschlossen!")


async def test_android_vlink():
    """Testet Android-Vlink."""
    test = AndroidVlinkTest(ANDROID_VLINK_MAC)
    await test.connect_and_test()


async def scan_all_vlinks():
    """Scant nach allen Vlink-Geräten."""
    logger.info("\n" + "=" * 60)
    logger.info("BLE SCAN — ALLE VLINK GERÄTE")
    logger.info("=" * 60)
    
    devices = await BleakScanner.discover(timeout=10.0)
    vlinks = [d for d in devices if d.name and "vlink" in d.name.lower()]
    
    logger.info(f"\nGefundene Vlink-Geräte: {len(vlinks)}")
    for d in vlinks:
        logger.info(f"  {d.address} — {d.name}")


async def main():
    print("=" * 60)
    print("ANDROID-VLINK vs IOS-VLINK BLE TEST")
    print("=" * 60)
    
    # Zuerst scan
    await scan_all_vlinks()
    
    # Dann Android-Vlink testen
    print("\n" + "=" * 60)
    await test_android_vlink()


if __name__ == "__main__":
    asyncio.run(main())