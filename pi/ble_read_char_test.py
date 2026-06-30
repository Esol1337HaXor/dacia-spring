#!/usr/bin/env python3
"""
BLE Read Characteristic Test — Testet ob Antworten via READ kommen.

IOS-Vlink sendet keine Notify-Daten! Stattdessen MUSS man die Antwort
via read_gatt_char (Characteristic Value Read) holen.

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
logger = logging.getLogger("BLE-Read-Char")


class BLEReadCharTest:
    """Testet read_gatt_char statt notify."""
    
    def __init__(self):
        self.client = None
    
    async def send_and_read(self, cmd: bytes, description: str, timeout: float = 2.0) -> bytes:
        """Sendet Command via WRITE und liest Antwort via READ."""
        try:
            logger.info(f"\n📤 SEND: {description}")
            logger.info(f"   CMD: {cmd}")
            logger.info(f"   HEX: {' '.join(f'{b:02X}' for b in cmd)}")
            
            # Command senden
            await self.client.write_gatt_char(VGLITE_CHAR, cmd)
            logger.info(f"   → Write erfolgreich")
            
            # Antwort lesen (statt Notify!)
            await asyncio.sleep(0.3)  # Warte auf Antwort vom Adapter
            response = await self.client.read_gatt_char(VGLITE_CHAR)
            
            if response and len(response) > 0:
                hex_str = ' '.join(f'{b:02X}' for b in response)
                ascii_str = response.decode('ascii', errors='replace')
                logger.info(f"   ✅ READ ERGEBNIS:")
                logger.info(f"      HEX: {hex_str}")
                logger.info(f"      DEC: {' '.join(str(b) for b in response)}")
                logger.info(f"      ASCII: {repr(ascii_str)}")
                logger.info(f"      LEN: {len(response)} bytes")
                return response
            else:
                logger.info(f"   ⚠️  READ: Leere Antwort")
                return b""
                
        except Exception as e:
            logger.error(f"   ❌ Fehler: {e}")
            return b""
    
    async def run_test(self):
        """Führt Tests durch."""
        print("=" * 60)
        print("BLE READ CHARACTERISTIC TEST")
        print("=" * 60)
        print(f"\n⚠️  WICHTIG: IOS-Vlink sendet KEINE Notify-Daten!")
        print(f"   Antworten MÜSSEN via read_gatt_char geholt werden.")
        print(f"\n⏰ Start: {datetime.now()}")
        print("=" * 60)
        
        try:
            async with BleakClient(VGLITE_MAC) as client:
                self.client = client
                logger.info("✅ BLE verbunden!")
                
                # ELM327 Setup (keine Notify!)
                logger.info("\n→ ELM327 Setup (READ-ONLY Modus)...")
                await self.client.write_gatt_char(VGLITE_CHAR, b"ATE0\r")
                await asyncio.sleep(0.2)
                resp = await self.client.read_gatt_char(VGLITE_CHAR)
                if resp and len(resp) > 0:
                    logger.info(f"  ATE0: {resp.decode('ascii', errors='replace').strip()}")
                
                await self.client.write_gatt_char(VGLITE_CHAR, b"ATH0\r")
                await asyncio.sleep(0.2)
                resp = await self.client.read_gatt_char(VGLITE_CHAR)
                if resp and len(resp) > 0:
                    logger.info(f"  ATH0: {resp.decode('ascii', errors='replace').strip()}")
                
                await self.client.write_gatt_char(VGLITE_CHAR, b"ATS0\r")
                await asyncio.sleep(0.2)
                resp = await self.client.read_gatt_char(VGLITE_CHAR)
                if resp and len(resp) > 0:
                    logger.info(f"  ATS0: {resp.decode('ascii', errors='replace').strip()}")
                
                await self.client.write_gatt_char(VGLITE_CHAR, b"ATSP 0\r")
                await asyncio.sleep(0.5)
                resp = await self.client.read_gatt_char(VGLITE_CHAR)
                if resp and len(resp) > 0:
                    logger.info(f"  ATSP 0: {resp.decode('ascii', errors='replace').strip()}")
                
                # === TEST: ELM327 Befehle ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST: ELM327 Befehle via READ")
                logger.info("=" * 60)
                
                tests = [
                    (b"ATZ\r", "ELM327 Reset"),
                    (b"ATI\r", "ELM327 Identify"),
                    (b"AT\r", "AT"),
                    (b"ATE0\r", "Echo OFF"),
                    (b"0100\r", "Supported PIDs"),
                    (b"010D\r", "Vehicle Speed"),
                    (b"010C\r", "Engine RPM"),
                    (b"222003\r", "Speed 222003"),
                    (b"22 20 03\r", "Speed 22 20 03"),
                    (b"22202E\r", "Throttle 22202E"),
                    (b"22 20 2E\r", "Throttle 22 20 2E"),
                    (b"223045\r", "Motor Speed (CanZE)"),
                    (b"229001\r", "Battery SOC (CanZE)"),
                    (b"22F190\r", "OBD Messages"),
                ]
                
                success_count = 0
                empty_count = 0
                
                for cmd, desc in tests:
                    resp = await self.send_and_read(cmd, desc, timeout=2.0)
                    if resp and len(resp) > 0:
                        success_count += 1
                    else:
                        empty_count += 1
                    await asyncio.sleep(0.2)
                
                # === TEST: Multi-Read ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST: Speed Multi-Read (5x)")
                logger.info("=" * 60)
                
                for i in range(5):
                    await self.client.write_gatt_char(VGLITE_CHAR, b"010D\r")
                    await asyncio.sleep(0.3)
                    resp = await self.client.read_gatt_char(VGLITE_CHAR)
                    if resp and len(resp) > 0:
                        text = resp.decode('ascii', errors='replace').strip()
                        logger.info(f"  Read #{i+1}: {repr(text)}")
                    else:
                        logger.info(f"  Read #{i+1}: (leer)")
                
                # === ZUSAMMENFASSUNG ===
                logger.info("\n" + "=" * 60)
                logger.info("ZUSAMMENFASSUNG")
                logger.info("=" * 60)
                logger.info(f"  Total Tests: {len(tests)}")
                logger.info(f"  Mit Antwort: {success_count}")
                logger.info(f"  Ohne Antwort: {empty_count}")
                
                if success_count > 0:
                    logger.info(f"\n  ✅ READ-MODUS FUNKTIONIERT!")
                else:
                    logger.info(f"\n  ❌ READ-MODUS ERGIBT AUCH KEINE DATEN!")
                    logger.info(f"  → IOS-Vlink unterstützt KEINE OBD2-Readbacks!")
                    logger.info(f"  → Adapter benötigt: OBDLink LX/MX oder CAN FD Adapter")
                
                logger.info(f"\n⏰ Ende: {datetime.now()}")
                
        except Exception as e:
            logger.error(f"\n❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ Test abgeschlossen!")


async def main():
    test = BLEReadCharTest()
    await test.run_test()


if __name__ == "__main__":
    asyncio.run(main())