#!/usr/bin/env python3
"""
Echte Fahrzeugdaten vom Dacia Spring holen - Test 2.

WICHTIG: Das Auto MUSS im ON/RUN Zustand sein (nicht nur ACC)!
- Fuß von der Bremse, Button drücken (kein starten)
- Oder: Zündung auf ON drehen

Experimentiert mit CAN-Protokoll und raw CAN-Frames.

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
logger = logging.getLogger("RealData-Test2")


class VehicleDataCollector:
    """Sammelt echte Fahrzeugdaten per BLE GATT."""
    
    def __init__(self):
        self.client = None
        self.responses = {}
        self.raw_data = bytearray()
        self.notification_count = 0
    
    async def notification_handler(self, sender, data: bytearray):
        """Notify-Callback."""
        self.raw_data = data
        self.notification_count += 1
    
    async def send_and_read(self, command: bytes, description: str, timeout: float = 3.0) -> str:
        """Sendet Command und liest Antwort via Notify."""
        try:
            self.raw_data = bytearray()
            await self.client.start_notify(VGLITE_CHAR, self.notification_handler)
            await self.client.write_gatt_char(VGLITE_CHAR, command)
            await asyncio.sleep(timeout)
            
            response = self.raw_data.decode('ascii', errors='ignore').strip()
            self.responses[description] = response
            return response
            
        except Exception as e:
            logger.error(f"❌ Fehler bei {description}: {e}")
            return ""
    
    async def setup_elm327(self):
        """Setzt ELM327 in den richtigen Modus."""
        logger.info("\n" + "=" * 60)
        logger.info("ELM327 Initialisierung")
        logger.info("=" * 60)
        
        # Standard Setup
        setup_cmds = [
            (b"ATE0\r", "Echo aus"),
            (b"ATH0\r", "Header aus"),
            (b"ATS0\r", "Spaces aus"),
            (b"ATC0\r", "Checksum aus"),
            (b"ATR0\r", "Response Format aus"),
            (b"ATL0\r", "Linefeed aus"),
            (b"ATST F\r", "Timeout auf Fast"),
        ]
        
        for cmd, desc in setup_cmds:
            await self.send_and_read(cmd, desc, 1.0)
            logger.info(f"  {desc}: {repr(self.responses.get(desc, ''))}")
    
    async def test_can_protocols(self):
        """Testet verschiedene CAN-Protokolle explizit."""
        logger.info("\n" + "=" * 60)
        logger.info("CAN-Protokoll-Test (explizit setzen)")
        logger.info("=" * 60)
        
        protocols = [
            ("ATSP 1", "ISO 15765-4 (CAN 500K 11bit)"),
            ("ATSP 2", "SAE J1939 (CAN 500K 29bit)"),
            ("ATSP 3", "ISO 13400 (WPM 10.4K)"),
            ("ATSP 4", "ISO 13400 (DPMM 10.4K)"),
            ("ATSP 5", "ISO 15765-4 (CAN 250K 11bit)"),
            ("ATSP 6", "SAE J1850 VPW"),
            ("ATSP 7", "SAE J1850 PWM"),
            ("ATSP 8", "ISO 15765-4 (CAN 500K 29bit)"),
            ("ATSP 9", "ISO 15765-4 (CAN 250K 29bit)"),
            ("ATSP A", "ISO 15765-4 (CAN 500K 11bit) (Europe 2014+)"),
            ("ATSP B", "ISO 15765-4 (CAN 500K 29bit) (Europe 2014+)"),
            ("ATSP C", "Dacia/Spring Custom?"),
        ]
        
        for cmd, desc in protocols:
            await self.send_and_read(cmd.encode(), desc, 1.0)
            resp = self.responses.get(desc, "")
            logger.info(f"  {desc}: {cmd} → {repr(resp)}")
            
            # Wenn OK, dann Speed testen
            if resp.strip() == "OK":
                await self.send_and_read(b"010D\r", f"010D nach {cmd}", 2.0)
                resp_speed = self.responses.get(f"010D nach {cmd}", "")
                if "NO DATA" not in resp_speed and resp_speed.strip() != ">":
                    logger.info(f"  *** POTENZIELLE DATEN GEFUNGEN! {cmd} → {repr(resp_speed)} ***")
    
    async def test_rpm_specific_pids(self):
        """Testet RPM-spezifische PIDs für EV."""
        logger.info("\n" + "=" * 60)
        logger.info("RPM-Spezifische PIDs für E-Auto")
        logger.info("=" * 60)
        
        # Für EV gibt es keine RPM, aber andere Werte
        pids = [
            "010D - Speed",
            "010E - Coolant Temp",
            "010F - Fuel Temp",
            "0110 - Fuel Pressure",
            "0114 - Control Module Voltage",
            "011C - Engine Oil Temperature",
            "011E - Turbo Boost Pressure",
        ]
        
        for pid in pids:
            parts = pid.split(" - ")
            cmd_bytes = parts[0].encode()
            desc = f"{parts[0]} - {parts[1]}"
            
            await self.send_and_read(cmd_bytes, desc, 2.0)
            resp = self.responses.get(desc, "")
            logger.info(f"  {desc}: {repr(resp)}")
    
    async def test_rpm_alternative(self):
        """Testet alternative RPM-PIDs."""
        logger.info("\n" + "=" * 60)
        logger.info("Alternative RPM/Pedal/Speed PIDs")
        logger.info("=" * 60)
        
        pids = [
            ("014C - Runtime Since Start", b"014C\r"),
            ("0146 - Accelerator Pedal Pos D", b"0146\r"),
            ("0147 - Accelerator Pedal Pos E", b"0147\r"),
            ("0148 - Accelerator Pedal Pos F", b"0148\r"),
            ("0149 - Absolute Load", b"0149\r"),
            ("014F - Commanded EGR", b"014F\r"),
            ("0150 - EGR Error", b"0150\r"),
            ("0152 - Absolute Throttle Pos E", b"0152\r"),
            ("0153 - Absolute Throttle Pos F", b"0153\r"),
            ("0154 - Absolute Throttle Pos G", b"0154\r"),
            ("0160 - Battery Level", b"0160\r"),
            ("0161 - SOH", b"0161\r"),
            ("0162 - Module Temperature", b"0162\r"),
            ("0163 - Current Differential", b"0163\r"),
        ]
        
        for desc, cmd in pids:
            await self.send_and_read(cmd, desc, 2.0)
            resp = self.responses.get(desc, "")
            logger.info(f"  {desc}: {repr(resp)}")
    
    async def continuous_speed_test(self, duration: int = 30):
        """Kontinuierlicher Speed-Test für X Sekunden."""
        logger.info("\n" + "=" * 60)
        logger.info(f"KONTINUIERLICHES SPEED-TEST ({duration}s)")
        logger.info("=" * 60)
        
        import time
        start = time.time()
        count = 0
        data_count = 0
        
        while time.time() - start < duration:
            count += 1
            await self.send_and_read(b"010D\r", f"speed_sample_{count}", 0.5)
            resp = self.responses.get(f"speed_sample_{count}", "")
            
            if "NO DATA" not in resp and resp.strip() not in [">", ""]:
                data_count += 1
                logger.info(f"  Sample {count}: {repr(resp)} *** DATA! ***")
            
            await asyncio.sleep(0.5)
        
        logger.info(f"\n  Gesamt: {count} Samples, {data_count} mit Daten")
    
    async def run_all_tests(self):
        """Führt alle Tests aus."""
        print("=" * 60)
        print("ECHTE FAHRZEUGDATEN TEST 2 - Dacia Spring")
        print("=" * 60)
        print(f"\n⚠️  WICHTIG: Auto MUSS im ON/RUN Zustand sein!")
        print("   - Fuß von der Bremse, Start-Button drücken (nicht starten)")
        print("   - ODER: Zündung auf ON drehen")
        print(f"\n📡 MAC: {VGLITE_MAC}")
        print(f"⏰ Start: {datetime.now()}")
        
        try:
            async with BleakClient(VGLITE_MAC) as client:
                self.client = client
                logger.info("✅ BLE verbunden!")
                
                # ELM327 Setup
                await self.setup_elm327()
                
                # CAN Protokoll-Test
                await self.test_can_protocols()
                
                # RPM Alternative PIDs
                await self.test_rpm_alternative()
                
                # Kurzer kontinuierlicher Speed-Test
                await self.continuous_speed_test(10)
                
                logger.info("\n" + "=" * 60)
                logger.info("ZUSAMMENFASSUNG")
                logger.info("=" * 60)
                
                for desc, response in self.responses.items():
                    if "NO DATA" not in response and response.strip() not in [">", ""]:
                        logger.info(f"  ✅ {desc}: {repr(response[:100])}")
                
                logger.info(f"\n⏰ Ende: {datetime.now()}")
                
        except Exception as e:
            logger.error(f"\n❌ Gesamtfehler: {e}")
        
        print("\n✅ Test abgeschlossen!")


async def main():
    collector = VehicleDataCollector()
    await collector.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())