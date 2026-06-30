#!/usr/bin/env python3
"""
Continuous Speed/Throttle Test - Misst Echtzeit-Daten vom Dacia Spring.

Testet ob Speed/Throttle sich ändern wenn:
- Gaspedal betätigt wird
- Auto im Drive/R/Neutral steht

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
logger = logging.getLogger("Continuous-Speed")


class SpeedThrottleTest:
    """Misst Speed und Throttle kontinuierlich."""
    
    def __init__(self):
        self.client = None
        self.speed_data = []
        self.throttle_data = []
        self.raw_data = bytearray()
        self.count = 0
        self.running = True
    
    async def notification_handler(self, sender, data: bytearray):
        """Notify-Callback."""
        self.raw_data = data
    
    async def send_command_no_wait(self, cmd: bytes):
        """Sendet Command OHNE zu warten (nicht-blockierend)."""
        await self.client.write_gatt_char(VGLITE_CHAR, cmd)
    
    async def read_notify(self, timeout: float = 0.3) -> bytes:
        """Liest Notify mit Timeout."""
        self.raw_data = bytearray()
        self.count += 1
        
        await self.client.start_notify(VGLITE_CHAR, self.notification_handler)
        await asyncio.sleep(timeout)
        
        return bytes(self.raw_data)
    
    async def parse_speed_pid_010d(self, raw: bytes) -> float:
        """Parsst Speed aus OBD2 PID 010D."""
        text = raw.decode('ascii', errors='ignore')
        
        # Format: '41 0D XX' oder '410DXX'
        if '410D' in text.upper():
            idx = text.upper().find('410D')
            if idx + 2 < len(text):
                try:
                    byte_val = int(text[idx+4:idx+6], 16)
                    return float(byte_val)
                except ValueError:
                    pass
        
        # Auch ohne Space suchen
        if '41 0D' in text:
            parts = text.replace(' ', '').replace('\r', '').replace('\n', '')
            idx = parts.find('410D')
            if idx + 2 < len(parts):
                try:
                    byte_val = int(parts[idx+4:idx+6], 16)
                    return float(byte_val)
                except ValueError:
                    pass
        
        return -1.0
    
    async def parse_throttle_22202e(self, raw: bytes) -> float:
        """Parsst Throttle aus 22 20 2E."""
        text = raw.decode('ascii', errors='ignore').strip()
        
        # Antwort kommt als '62202E0000' oder '62 20 2E 00 00'
        cleaned = text.replace(' ', '').replace('\r', '').replace('\n', '')
        
        if cleaned.upper().startswith('62202E') and len(cleaned) >= 10:
            try:
                # Byte 4 ist Throttle in %
                throttle_byte = int(cleaned[8:10], 16)
                return float(throttle_byte)
            except ValueError:
                pass
        
        return -1.0
    
    async def parse_speed_222003(self, raw: bytes) -> float:
        """Parsst Speed aus 22 20 03."""
        text = raw.decode('ascii', errors='ignore').strip()
        
        # Antwort kommt als '6220030000' oder ähnlich
        cleaned = text.replace(' ', '').replace('\r', '').replace('\n', '')
        
        if cleaned.upper().startswith('622003') and len(cleaned) >= 10:
            try:
                # Byte 4 ist Speed in km/h
                speed_byte = int(cleaned[8:10], 16)
                return float(speed_byte)
            except ValueError:
                pass
        
        return -1.0
    
    async def run_test(self, duration: int = 60):
        """Führt Continuous-Test durch."""
        print("=" * 60)
        print("CONTINUOUS SPEED/THROTTLE TEST - Dacia Spring")
        print("=" * 60)
        print(f"\n⏰ Start: {datetime.now()}")
        print(f"⚠️  ANWEISUNG:")
        print(f"  1. Auto IMMER IM ON (Zündung an)")
        print(f"  2. Auto im PARK (Bremse gedrückt)")
        print(f"  3. Jetzt GAS GEBEN (Pedal bis durchtreten)")
        print(f"  4. Warten X Sekunden und wieder loslassen")
        print(f"  5. Test läuft {duration} Sekunden")
        print(f"\n📡 MAC: {VGLITE_MAC}")
        print(f"📡 Service: {VGLITE_SERVICE}")
        print(f"📡 Char: {VGLITE_CHAR}")
        print("=" * 60)
        
        try:
            async with BleakClient(VGLITE_MAC) as client:
                self.client = client
                logger.info("✅ BLE verbunden!")
                
                # ELM327 Setup
                logger.info("\n→ ELM327 Setup...")
                await self.send_command_no_wait(b"ATE0\r")
                await asyncio.sleep(0.1)
                await self.send_command_no_wait(b"ATH0\r")
                await asyncio.sleep(0.1)
                await self.send_command_no_wait(b"ATS0\r")
                await asyncio.sleep(0.1)
                await self.send_command_no_start_notify(b"ATSP 0\r")
                await asyncio.sleep(0.5)
                logger.info("  Setup fertig!")
                
                # Continuous Test
                start = datetime.now()
                speed_010d_max = 0.0
                speed_222003_max = 0.0
                throttle_22202e_max = 0.0
                
                speed_010d_min = 999.0
                throttle_22202e_min = 999.0
                
                while self.running and (datetime.now() - start).total_seconds() < duration:
                    elapsed = (datetime.now() - start).total_seconds()
                    
                    # Test 1: Speed PID 010D
                    await self.send_command_no_wait(b"010D\r")
                    raw = await self.read_notify(0.2)
                    speed = await self.parse_speed_pid_010d(raw)
                    
                    # Test 2: Speed PID 222003
                    await self.send_command_no_wait(b"222003\r")
                    raw = await self.read_notify(0.2)
                    speed_22 = await self.parse_speed_222003(raw)
                    
                    # Test 3: Throttle PID 22202E
                    await self.send_command_no_wait(b"22202E\r")
                    raw = await self.read_notify(0.2)
                    throttle = await self.parse_throttle_22202e(raw)
                    
                    # Stats aktualisieren
                    if speed > 0:
                        self.speed_data.append((elapsed, speed))
                        speed_010d_max = max(speed_010d_max, speed)
                        speed_010d_min = min(speed_010d_min, speed)
                    
                    if speed_22 > 0:
                        self.speed_data.append((elapsed, speed_22))
                        speed_222003_max = max(speed_222003_max, speed_22)
                    
                    if throttle >= 0:
                        self.throttle_data.append((elapsed, throttle))
                        throttle_22202e_max = max(throttle_22202e_max, throttle)
                        throttle_22202e_min = min(throttle_22202e_min, throttle)
                    
                    # Ausgabe jede Sekunde
                    if int(elapsed) > int(elapsed - 0.6):
                        logger.info(f"  t={elapsed:.1f}s | Speed 010D: {speed:.1f} km/h | Speed 222003: {speed_22:.1f} km/h | Throttle 22202E: {throttle:.1f}%")
                    
                    await asyncio.sleep(0.4)
                
                # Zusammenfassung
                logger.info("\n" + "=" * 60)
                logger.info("ZUSAMMENFASSUNG")
                logger.info("=" * 60)
                
                if self.speed_data:
                    logger.info(f"  Speed 010D: min={speed_010d_min:.1f}, max={speed_010d_max:.1f}, samples={len(self.speed_data)}")
                else:
                    logger.info(f"  Speed 010D: KEINE DATEN!")
                
                logger.info(f"  Speed 222003: max={speed_222003_max:.1f} km/h")
                logger.info(f"  Throttle 22202E: min={throttle_22202e_min:.1f}%, max={throttle_22202e_max:.1f}%")
                
                if throttle_22202e_max > 0:
                    logger.info(f"\n  ✅ THROTTLE DATEN GEFOUNDEN! Max: {throttle_22202e_max}%")
                else:
                    logger.info(f"\n  ⚠️  KEINE Throttle-Daten — Pedal vielleicht nicht betätigt?")
                
                logger.info(f"\n⏰ Ende: {datetime.now()}")
                
        except Exception as e:
            logger.error(f"\n❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ Test abgeschlossen!")
    
    async def send_command_no_start_notify(self, cmd: bytes):
        """Sendet Command OHNE start_notify."""
        await self.client.write_gatt_char(VGLITE_CHAR, cmd)


async def main():
    test = SpeedThrottleTest()
    
    # Duration: 30 Sekunden Test
    duration = 30
    
    try:
        await test.run_test(duration=duration)
    except KeyboardInterrupt:
        logger.info("\n  ⏹️  Test abgebrochen!")
        await test.run_test(duration=0)


if __name__ == "__main__":
    asyncio.run(main())