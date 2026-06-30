#!/usr/bin/env python3
"""
Raw Notify Dump - Zeigt ALLE empfangenen Bytes OHNE Parsing.

So sehen wir WAS IOS-Vlink wirklich sendet.

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

from bleak import BleakClient

# ============ KONFIGURATION ============
VGLITE_MAC = "D2:E0:2F:8D:61:07"
VGLITE_SERVICE = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
VGLITE_CHAR = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"

# Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Raw-Notify-Dump")


class RawNotifyDump:
    """Dumped alle empfangenen Notify-Daten raw."""
    
    def __init__(self):
        self.client = None
        self.raw_responses = []
        self.notification_count = 0
    
    async def notification_handler(self, sender, data: bytearray):
        """Notify-Callback — zeige ALLES raw."""
        self.notification_count += 1
        
        hex_str = ' '.join(f'{b:02X}' for b in data)
        ascii_str = data.decode('ascii', errors='replace')
        int_vals = ' '.join(f'{b}' for b in data)
        
        logger.info(f"📨 NOTIFY #{self.notification_count} (Handle 27):")
        logger.info(f"  RAW HEX:  {hex_str}")
        logger.info(f"  RAW DEC:  {int_vals}")
        logger.info(f"  ASCII:    {repr(ascii_str)}")
        logger.info(f"  LEN:      {len(data)} bytes")
        
        self.raw_responses.append(data.copy())
    
    async def send_and_dump(self, cmd: str, description: str):
        """Sendet Command und zeigt raw Antwort."""
        logger.info(f"\n{'='*60}")
        logger.info(f"📤 SEND: {description}")
        logger.info(f"   CMD: {repr(cmd.encode())}")
        logger.info(f"   HEX: {' '.join(f'{b:02X}' for b in cmd.encode())}")
        logger.info(f"{'='*60}")
        
        self.raw_responses = []
        
        await self.client.start_notify(VGLITE_CHAR, self.notification_handler)
        await self.client.write_gatt_char(VGLITE_CHAR, cmd.encode())
        
        await asyncio.sleep(1.0)
        
        logger.info(f"\n📊 ERHALTENE NOTIFYS: {len(self.raw_responses)}")
        for i, resp in enumerate(self.raw_responses):
            logger.info(f"  Notify #{i+1}: {len(resp)} bytes")
        
        logger.info("")
    
    async def run_test(self):
        """Führt Raw-Test durch."""
        print("=" * 60)
        print("RAW NOTIFY DUMP - IOS-Vlink")
        print("=" * 60)
        print(f"\n⚠️  ANWEISUNG:")
        print(f"  1. Auto IMMER IM ON (Zündung an)")
        print(f"  2. PEDAL BETÄTIGEN WÄHREND DEM TEST!")
        print(f"  3. Test: 20 Sekunden (Pedal wechseln)")
        print(f"\n⏰ Start: {datetime.now()}")
        print("=" * 60)
        
        try:
            async with BleakClient(VGLITE_MAC) as client:
                self.client = client
                logger.info("✅ BLE verbunden!")
                
                # ELM327 Setup
                await self.client.write_gatt_char(VGLITE_CHAR, b"ATE0\r")
                await asyncio.sleep(0.1)
                await self.client.write_gatt_char(VGLITE_CHAR, b"ATH0\r")
                await asyncio.sleep(0.1)
                await self.client.write_gatt_char(VGLITE_CHAR, b"ATS0\r")
                await asyncio.sleep(0.1)
                await self.client.write_gatt_char(VGLITE_CHAR, b"ATSP 0\r")
                await asyncio.sleep(0.5)
                
                # === TEST: Verschiedene Commands ===
                tests = [
                    ("ATZ", "ELM327 Reset"),
                    ("ATI", "ELM327 Identify"),
                    ("010D", "Speed PID 010D"),
                    ("01 0D", "Speed PID 01 0D (with space)"),
                    ("222003", "Speed 222003 (no space)"),
                    ("22 20 03", "Speed 22 20 03 (with spaces)"),
                    ("22202E", "Throttle 22202E (no space)"),
                    ("22 20 2E", "Throttle 22 20 2E (with spaces)"),
                    ("22F190", "OBD Message Count"),
                    ("221000", "PID 1000"),
                    ("222000", "PID 2000"),
                    ("223045", "Motor Speed (CanZE)"),
                    ("229001", "Battery SOC (CanZE)"),
                ]
                
                for cmd, desc in tests:
                    await self.send_and_dump(cmd, desc)
                    await asyncio.sleep(0.5)
                
                # === TEST: Continuous Throttle ===
                logger.info("\n" + "=" * 60)
                logger.info("CONTINUOUS THROTTLE TEST (10s)")
                logger.info("=" * 60)
                
                for i in range(20):
                    await self.send_and_dump("22 20 2E", f"Throttle #{i+1}")
                    await asyncio.sleep(0.5)
                
                # === ZUSAMMENFASSUNG ===
                logger.info("\n" + "=" * 60)
                logger.info("ZUSAMMENFASSUNG — ALLE RAW ANTWORTEN")
                logger.info("=" * 60)
                
                total_notifications = sum(len(r) for r in self.raw_responses)
                logger.info(f"  Total Command-Tests: {len(tests)}")
                logger.info(f"  Total Notifications: {total_notifications}")
                
                # Zeige Unique Responses
                unique = {}
                for resp_group in self.raw_responses:
                    for resp in resp_group:
                        key = bytes(resp).hex()
                        if key not in unique:
                            unique[key] = []
                        unique[key].append(resp)
                
                logger.info(f"\n  Unique Response Patterns: {len(unique)}")
                for i, (hex_key, responses) in enumerate(unique.items()):
                    hex_str = ' '.join(f'{b:02X}' for b in responses[0])
                    ascii_str = responses[0].decode('ascii', errors='replace')
                    logger.info(f"  [{i:2d}] Hex: {hex_str}")
                    logger.info(f"       ASCII: {repr(ascii_str)}")
                    logger.info(f"       Count: {len(responses)}")
                
                logger.info(f"\n⏰ Ende: {datetime.now()}")
                
        except Exception as e:
            logger.error(f"\n❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ Test abgeschlossen!")


async def main():
    dump = RawNotifyDump()
    await dump.run_test()


if __name__ == "__main__":
    asyncio.run(main())