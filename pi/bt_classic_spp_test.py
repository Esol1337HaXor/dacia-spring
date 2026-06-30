#!/usr/bin/env python3
"""
Bluetooth Classic SPP/RFCOMM Test — Testet das ANDROID-VLINK Signal.

Das Android-Vlink Signal (`13:E0:2F:8D:61:07`) verwendet Bluetooth Classic
mit SPP (Serial Port Profile), NICHT BLE GATT!

MUSS ALS ROOT AUSGEFÜHRT WERDEN!
"""
import asyncio
import serial
import serial.tools.list_ports
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("BT-Classic-SPP")


def scan_bluetooth_classes():
    """Scant nach Bluetooth Classic Geräten."""
    logger.info("\n" + "=" * 60)
    logger.info("BLUETOOTH CLASSIC SCAN")
    logger.info("=" * 60)
    
    # Prüfe ob rfcomm Devices existieren
    import os
    rfcomm_devs = [p for p in os.listdir('/dev') if p.startswith('rfcomm')]
    if rfcomm_devs:
        logger.info(f"  RFComm Devices: {rfcomm_devs}")
    else:
        logger.info("  Keine RFComm Devices gefunden")
    
    # Prüfe Bluetooth Adapter
    result = os.popen("bluetoothctl list").read()
    logger.info(f"\n  Bluetooth Adapter:\n{result}")
    
    # Prüfe paired devices
    result = os.popen("bluetoothctl paired-devices").read()
    logger.info(f"  Paired Devices:\n{result}")
    
    # Scanne nach Geräten (kurz)
    logger.info("  Scanne nach Bluetooth Classic Geräten...")
    result = os.popen("bluetoothctl scan on").read()
    import time
    time.sleep(5)
    os.popen("bluetoothctl scan off").read()
    
    result = os.popen("bluetoothctl devices").read()
    logger.info(f"  Devices:\n{result}")


def try_rfcomm_connection():
    """Versucht eine RFCOMM Verbindung zum Android-Vlink."""
    ANDROID_VLINK_MAC = "13:E0:2F:8D:61:07"
    
    logger.info("\n" + "=" * 60)
    logger.info("RFCOMM VERBINDUNGSTEST")
    logger.info("=" * 60)
    logger.info(f"  Ziel: {ANDROID_VLINK_MAC}")
    logger.info(f"  Port: 1 (standard SPP)")
    
    # Prüfe welche RFCOMM Channels verfügbar sind
    logger.info("\n  Scanne RFCOMM Channels...")
    
    # Versuche Verbindung auf Channel 1, 2, 3...
    for channel in range(1, 10):
        try:
            logger.info(f"\n  Versuch Channel {channel}...")
            
            # Prüfe ob rfcomm connect möglich ist
            cmd = f"timeout 2 rfcomm connect {channel} {ANDROID_VLINK_MAC} {channel} 2>&1 || true"
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            
            logger.info(f"  Channel {channel}: {result.stdout[:100] if result.stdout else 'No response'}")
            
        except Exception as e:
            logger.info(f"  Channel {channel}: {e}")


async def test_spp_with_pyserial():
    """Testet SPP mit pyserial."""
    ANDROID_VLINK_MAC = "13:E0:2F:8D:61:07"
    
    logger.info("\n" + "=" * 60)
    logger.info("PYSERIAL SPP TEST")
    logger.info("=" * 60)
    
    # Versuche verschiedene Ports
    ports_to_try = [
        f"/dev/rfcomm0",
        f"/dev/rfcomm1",
    ]
    
    # Suche nach verfügbaren Ports
    available_ports = [p.device for p in serial.tools.list_ports.comports()]
    logger.info(f"  Verfügbare Ports: {available_ports}")
    
    for port in available_ports:
        if 'rfcomm' in port:
            try:
                logger.info(f"\n  Versuche {port}...")
                s = serial.Serial(port, 9600, timeout=2)
                logger.info(f"  ✅ Verbunden zu {port}")
                
                # ELM327 Commands senden
                commands = [b"ATZ\r", b"ATI\r", b"ATE0\r", b"ATSP 0\r"]
                
                for cmd in commands:
                    s.write(cmd)
                    logger.info(f"  Gesendet: {cmd}")
                    
                    response = s.read_all()
                    if response:
                        logger.info(f"  Empfangen: {response}")
                    else:
                        logger.info(f"  Kein Antwort")
                
                s.close()
                logger.info("  Verbindung geschlossen")
                return True
                
            except Exception as e:
                logger.info(f"  ❌ {port}: {e}")
    
    logger.info("\n  ⚠️  Keine RFCOMM-Verbindung möglich!")
    return False


async def main():
    print("=" * 60)
    print("BLUETOOTH CLASSIC SPP TEST — ANDROID-VLINK")
    print("=" * 60)
    print(f"\n⏰ Start: {datetime.now()}")
    print("=" * 60)
    
    # 1. Bluetooth Scan
    scan_bluetooth_classes()
    
    # 2. RFCOMM Verbindungstest
    try_rfcomm_connection()
    
    # 3. pyserial SPP Test
    await test_spp_with_pyserial()
    
    print(f"\n⏰ Ende: {datetime.now()}")
    print("\n✅ Test abgeschlossen!")


if __name__ == "__main__":
    asyncio.run(main())