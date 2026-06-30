#!/usr/bin/env python3
"""
BLE Notify Debugging — Zeigt ALLE Notify-Daten in Echtzeit.

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
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Notify-Debug")


class NotifyDebugger:
    """Debuggt BLE Notify-Kommunikation."""
    
    def __init__(self):
        self.client = None
        self.notification_count = 0
        self.responses = []
        self.event = asyncio.Event()
    
    async def notification_handler(self, sender, data: bytearray):
        """Notify-Callback mit DEBUG-Output."""
        self.notification_count += 1
        self.responses.append(data.copy())
        
        # Dezimal + ASCII darstellen
        hex_str = ' '.join(f'{b:02X}' for b in data)
        ascii_str = data.decode('ascii', errors='ignore')
        
        logger.info(f"📨 NOTIFY #{self.notification_count}:")
        logger.info(f"  Sender: {sender}")
        logger.info(f"  Hex: {hex_str}")
        logger.info(f"  ASCII: {repr(ascii_str)}")
        logger.info(f"  Raw bytes: {list(data)}")
        
        # Signal dass was angekommen ist
        self.event.set()
    
    async def send_command(self, cmd_bytes: bytes, description: str = ""):
        """Sendet Command und wartet auf Notify."""
        self.event.clear()
        
        if description:
            logger.info(f"\n📤 SEND: {description}")
            logger.info(f"  Bytes: {list(cmd_bytes)}")
            logger.info(f"  Hex: {' '.join(f'{b:02X}' for b in cmd_bytes)}")
        
        # Notify registrieren
        await self.client.start_notify(VGLITE_CHAR, self.notification_handler)
        
        # Command senden
        await self.client.write_gatt_char(VGLITE_CHAR, cmd_bytes)
        
        # Max 3 Sekunden warten
        try:
            await asyncio.wait_for(self.event.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.info(f"  ⏱️ Timeout — keine Notify-Daten empfangen")
        
        logger.info("")
    
    async def test_all(self):
        """Führt komplette Tests durch."""
        print("=" * 60)
        print("BLE NOTIFY DEBUGGING - ELM327")
        print("=" * 60)
        print(f"\n📡 MAC: {VGLITE_MAC}")
        print(f"⏰ Start: {datetime.now()}")
        
        try:
            async with BleakClient(VGLITE_MAC) as client:
                self.client = client
                logger.info("✅ BLE verbunden!")
                
                # === TEST 1: ELM327 Befehle ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST 1: ELM327 Basis-Befehle")
                logger.info("=" * 60)
                
                await self.send_command(b"\r", "Raw CR")
                await self.send_command(b"AT\r", "AT")
                await self.send_command(b"ATE0\r", "Echo ON")
                await self.send_command(b"ATZ\r", "Reset")
                await self.send_command(b"ATI\r", "Identify")
                await self.send_command(b"ATH0\r", "Header OFF")
                await self.send_command(b"ATS0\r", "Spaces OFF")
                await self.send_command(b"ATC0\r", "Checksum OFF")
                await self.send_command(b"ATSP 0\r", "Protocol Auto")
                
                # === TEST 2: OBD2 PIDs ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST 2: OBD2 PIDs (Speed, RPM, etc)")
                logger.info("=" * 60)
                
                await self.send_command(b"0100\r", "Supported PIDs")
                await self.send_command(b"010D\r", "Vehicle Speed")
                await self.send_command(b"010C\r", "Engine RPM")
                await self.send_command(b"0105\r", "Coolant Temp")
                await self.send_command(b"0111\r", "Throttle Position")
                await self.send_command(b"0114\r", "Control Module Voltage")
                
                # === TEST 3: Diagnostic PIDs ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST 3: Diagnostic PIDs (22XXXX)")
                logger.info("=" * 60)
                
                await self.send_command(b"222003\r", "Speed (222003)")
                await self.send_command(b"22 20 03\r", "Speed (22 20 03)")
                await self.send_command(b"22202E\r", "Throttle (22202E)")
                await self.send_command(b"229001\r", "Battery SOC")
                
                # === TEST 4: Verschiedene Timing-Tests ===
                logger.info("\n" + "=" * 60)
                logger.info("TEST 4: Timing-Test (schnelle Sequenz)")
                logger.info("=" * 60)
                
                # Viele PIDs hintereinander
                for i in range(5):
                    await self.send_command(b"010D\r", f"Speed Test #{i+1}")
                
                # === ZUSAMMENFASSUNG ===
                logger.info("\n" + "=" * 60)
                logger.info("ZUSAMMENFASSUNG")
                logger.info("=" * 60)
                logger.info(f"  Total Notifications: {self.notification_count}")
                logger.info(f"  Total Responses: {len(self.responses)}")
                
                if self.responses:
                    logger.info("\n  Alle empfangenen Daten:")
                    for i, resp in enumerate(self.responses):
                        hex_str = ' '.join(f'{b:02X}' for b in resp)
                        ascii_str = resp.decode('ascii', errors='ignore')
                        logger.info(f"    [{i}] Hex: {hex_str} | ASCII: {repr(ascii_str)}")
                
                logger.info(f"\n⏰ Ende: {datetime.now()}")
                
        except Exception as e:
            logger.error(f"\n❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ Test abgeschlossen!")


async def main():
    debugger = NotifyDebugger()
    await debugger.test_all()


if __name__ == "__main__":
    asyncio.run(main())