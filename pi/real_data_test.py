#!/usr/bin/env python3
"""
Echte Fahrzeugdaten vom Dacia Spring holen.

Experimentiert mit verschiedenen PID-Formaten über BLE GATT
um echte Speed, Throttle, Battery Daten zu erhalten.

MUSS ALS ROOT AUSGEFÜHRT WERDEN!
"""
import asyncio
import sys
import logging
from datetime import datetime

import os
if os.geteuid() != 0:
    print("=" * 60)
    print("FEHLER: Script MUSS als root ausgeführt werden!")
    print("=" * 60)
    print("Befehl: sudo python3 real_data_test.py")
    sys.exit(1)

from bleak import BleakScanner, BleakClient

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
logger = logging.getLogger("RealData-Test")


class VehicleDataCollector:
    """Sammelt echte Fahrzeugdaten per BLE GATT."""
    
    def __init__(self):
        self.client = None
        self.responses = {}
        self.raw_data = bytearray()
    
    async def notification_handler(self, sender, data: bytearray):
        """Notify-Callback."""
        self.raw_data = data
    
    async def send_and_read(self, command: bytes, description: str, timeout: float = 3.0) -> str:
        """Sendet Command und liest Antwort via Notify."""
        try:
            # Notify registrieren
            await self.client.start_notify(VGLITE_CHAR, self.notification_handler)
            
            # Command senden
            await self.client.write_gatt_char(VGLITE_CHAR, command)
            
            # Warten
            await asyncio.sleep(timeout)
            
            # Antwort holen
            response = self.raw_data.decode('ascii', errors='ignore').strip()
            self.raw_data = bytearray()
            
            self.responses[description] = response
            return response
            
        except Exception as e:
            logger.error(f"❌ Fehler bei {description}: {e}")
            return ""
    
    async def test_standard_obd2(self):
        """Testet Standard OBD2 PIDs (01XX Format)."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 1: Standard OBD2 PIDs (01XX Format)")
        logger.info("=" * 60)
        
        tests = [
            (b"0100\r", "0100 - Supported PIDs"),
            (b"010D\r", "010D - Vehicle Speed"),
            (b"010C\r", "010C - Engine RPM"),
            (b"0105\r", "0105 - Coolant Temp"),
            (b"0104\r", "0104 - Engine Load"),
            (b"010B\r", "010B - Intake Temp"),
            (b"0111\r", "0111 - Throttle Position"),
            (b"0142\r", "0142 - Run Time"),
            (b"014B\r", "014B - Throttle Pos B"),
        ]
        
        for cmd, desc in tests:
            logger.info(f"\n→ {desc}: {cmd}")
            response = await self.send_and_read(cmd, desc, timeout=2.0)
            if response:
                logger.info(f"  Antwort: {repr(response)}")
            else:
                logger.info(f"  Antwort: (leer/timeout)")
    
    async def test_diagnostic_pids(self):
        """Testet erweiterte Diagnostic PIDs (22XXXX Format)."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 2: Diagnostic PIDs (22XXXX Format)")
        logger.info("=" * 60)
        
        tests = [
            # CanZE Renault ZE Format
            (b"22F190\r", "22F190 - OBD Messages"),
            (b"221000\r", "221000 - System Parameter 0"),
            (b"221010\r", "221010 - System Parameter 16"),
            
            # ELM327 Extended Diagnostic (SID 0x22)
            (b"22 20 03\r", "22 20 03 - Speed (CanZE)"),
            (b"222003\r", "222003 - Speed (Concat)"),
            (b"22 20 2E\r", "22 20 2E - Throttle (CanZE)"),
            (b"22202E\r", "22202E - Throttle (Concat)"),
            (b"22 30 45\r", "22 30 45 - Motor Speed (CanZE)"),
            (b"223045\r", "223045 - Motor Speed (Concat)"),
            (b"22 90 01\r", "22 90 01 - Battery SOC (CanZE)"),
            (b"229001\r", "229001 - Battery SOC (Concat)"),
            
            # Verschiedene andere PIDs
            (b"22 10 00\r", "22 10 00 - PID 1000"),
            (b"22 20 00\r", "22 20 00 - PID 2000"),
            (b"22 22 00\r", "22 22 00 - PID 2200"),
            (b"22 28 00\r", "22 28 00 - PID 2800"),
            (b"22 30 00\r", "22 30 00 - PID 3000"),
            (b"22 40 00\r", "22 40 00 - PID 4000"),
            (b"22 50 00\r", "22 50 00 - PID 5000"),
            (b"22 60 00\r", "22 60 00 - PID 6000"),
            (b"22 70 00\r", "22 70 00 - PID 7000"),
            (b"22 80 00\r", "22 80 00 - PID 8000"),
            (b"22 90 00\r", "22 90 00 - PID 9000"),
            (b"22 A0 00\r", "22 A0 00 - PID A000"),
            (b"22 B0 00\r", "22 B0 00 - PID B000"),
            (b"22 C0 00\r", "22 C0 00 - PID C000"),
            (b"22 D0 00\r", "22 D0 00 - PID D000"),
            (b"22 E0 00\r", "22 E0 00 - PID E000"),
            (b"22 F0 00\r", "22 F0 00 - PID F000"),
        ]
        
        for cmd, desc in tests:
            logger.info(f"\n→ {desc}: {cmd}")
            response = await self.send_and_read(cmd, desc, timeout=2.0)
            if response:
                logger.info(f"  Antwort: {repr(response)}")
            else:
                logger.info(f"  Antwort: (leer/timeout)")
    
    async def test_raw_hex(self):
        """Testet rohe hex-Befehle."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 3: Raw Hex Commands")
        logger.info("=" * 60)
        
        tests = [
            (b"\r", "Raw CR"),
            (b"AT\r", "AT"),
            (b"ATI\r", "ATI"),
            (b"ATE0\r", "ATE0"),
            (b"ATH0\r", "ATH0"),
            (b"ATS0\r", "ATS0"),
            (b"ATSP 0\r", "ATSP 0"),
            (b"ATDP\r", "ATDP - Display Protocol"),
            (b"01\r", "01"),
            (b"01 00\r", "01 00"),
            (b"ATC0\r", "ATC0 - No Checksum"),
            (b"ATR0\r", "ATR0 - No Response Formatting"),
            (b"L0\r", "L0 - No Line Feed"),
        ]
        
        for cmd, desc in tests:
            logger.info(f"\n→ {desc}: {cmd}")
            response = await self.send_and_read(cmd, desc, timeout=2.0)
            if response:
                logger.info(f"  Antwort: {repr(response)}")
            else:
                logger.info(f"  Antwort: (leer/timeout)")
    
    async def test_byte_by_byte(self):
        """Testet einzelne Bytes manuell."""
        logger.info("\n" + "=" * 60)
        logger.info("TEST 4: Manual Byte-by-Byte")
        logger.info("=" * 60)
        
        commands = [
            ("ATZ", b"ATZ\r"),
            ("ATI", b"ATI\r"),
            ("0100", b"0100\r"),
            ("01 00", b"01 00\r"),
            ("AT SP 0", b"AT SP 0\r"),
            ("010D", b"010D\r"),
            ("01 0D", b"01 0D\r"),
            ("222003", b"222003\r"),
            ("22 20 03", b"22 20 03\r"),
        ]
        
        for name, cmd in commands:
            try:
                logger.info(f"\n→ {name}: {cmd}")
                await self.client.write_gatt_char(VGLITE_CHAR, cmd)
                await asyncio.sleep(2.0)
                
                # Versuche zu lesen
                try:
                    val = await self.client.read_gatt_char(VGLITE_CHAR)
                    response = val.decode('ascii', errors='ignore').strip() if val else ""
                except:
                    response = ""
                
                logger.info(f"  Antwort: {repr(response[:200]) if response else '(leer)'}")
                
            except Exception as e:
                logger.error(f"  ❌ Fehler: {e}")
    
    async def run_all_tests(self):
        """Führt alle Tests aus."""
        print("=" * 60)
        print("ECHTE FAHRZEUGDATEN TEST - Dacia Spring")
        print("=" * 60)
        print(f"\n📡 MAC: {VGLITE_MAC}")
        print(f"📡 Service: {VGLITE_SERVICE}")
        print(f"📡 Char: {VGLITE_CHAR}")
        print(f"⏰ Start: {datetime.now()}")
        
        try:
            async with BleakClient(VGLITE_MAC) as client:
                self.client = client
                logger.info("✅ BLE verbunden!")
                
                # Test 1: Standard OBD2
                await self.test_standard_obd2()
                
                # Test 2: Diagnostic PIDs
                await self.test_diagnostic_pids()
                
                # Test 3: Raw Hex
                await self.test_raw_hex()
                
                # Test 4: Manual Byte-by-Byte
                await self.test_byte_by_byte()
                
                logger.info("\n" + "=" * 60)
                logger.info("ZUSAMMENFASSUNG")
                logger.info("=" * 60)
                for desc, response in self.responses.items():
                    if response:
                        logger.info(f"  {desc}: {repr(response[:100])}")
                
                logger.info(f"\n⏰ Ende: {datetime.now()}")
                
        except Exception as e:
            logger.error(f"\n❌ Gesamtfehler: {e}")
        
        print("\n✅ Test abgeschlossen!")


async def main():
    collector = VehicleDataCollector()
    await collector.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())