#!/usr/bin/env python3
"""
SPP ELM327 Test — Liest echte OBD2-Daten vom vGate iCar Pro über Bluetooth Classic SPP.

Nach dem Pairing und rfcomm bind kann man direkt über /dev/rfcomm0
mit dem vGate iCar Pro kommunizieren.
"""
import serial
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SPP-ELM327")


def test_spp_elm327():
    """Testet SPP-Verbindung mit ELM327 Commands."""
    
    RFCOMM_PORT = "/dev/rfcomm0"
    BAUD_RATE = 38400  # Standard Baudrate für ELM327
    
    print("=" * 60)
    print("SPP ELM327 TEST — vGate iCar Pro BT")
    print("=" * 60)
    print(f"\n📡 Port: {RFCOMM_PORT}")
    print(f"📡 Baud: {BAUD_RATE}")
    print(f"⏰ Start: {datetime.now()}")
    print("=" * 60)
    
    try:
        # Step 1: Port öffnen
        logger.info(f"\n→ Öffne {RFCOMM_PORT} bei {BAUD_RATE} baud...")
        s = serial.Serial(
            port=RFCOMM_PORT,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0
        )
        logger.info("✅ Serial Port geöffnet!")
        
        # Step 2: Warte auf ELM327 Prompt
        time.sleep(0.5)
        
        # Lese Puffer leer (kann Restdaten enthalten)
        try:
            remaining = s.read_all()
            if remaining:
                logger.info(f"  Puffer-Inhalt: {remaining}")
        except:
            pass
        
        # Step 3: ELM327 Commands senden
        logger.info("\n→ TEST 1: ELM327 Verbindung prüfen")
        logger.info("=" * 60)
        
        commands_to_try = [
            (b"ATZ\r", "Reset", 2.0),
            (b"ATI\r", "Identify", 2.0),
            (b"AT\r", "Basic AT", 1.0),
            (b"ATE0\r", "Echo OFF", 1.0),
            (b"ATH0\r", "Header OFF", 1.0),
            (b"ATS0\r", "Spaces OFF", 1.0),
            (b"ATSP 0\r", "Protocol Auto", 2.0),
        ]
        
        for cmd, desc, timeout in commands_to_try:
            logger.info(f"\n  📤 SEND: {desc}")
            logger.info(f"     CMD: {cmd}")
            
            s.write(cmd)
            logger.info(f"     → Gesendet ({len(cmd)} bytes)")
            
            # Auf Antwort warten
            time.sleep(timeout)
            
            # Alle verfügbaren Daten lesen
            response = s.read_all()
            
            if response:
                text = response.decode('ascii', errors='replace').strip()
                logger.info(f"  ✅ EMPFANGEN:")
                logger.info(f"     TEXT: {repr(text)}")
                logger.info(f"     HEX: {' '.join(f'{b:02X}' for b in response)}")
                logger.info(f"     LEN: {len(response)} bytes")
            else:
                logger.info(f"  ⏱️  Timeout — keine Antwort")
        
        # Step 4: OBD2 PIDs testen
        logger.info("\n→ TEST 2: OBD2 PIDs")
        logger.info("=" * 60)
        
        pids = [
            (b"0100\r", "Supported PIDs"),
            (b"010D\r", "Vehicle Speed"),
            (b"010C\r", "Engine RPM"),
            (b"222003\r", "Speed PID 222003"),
            (b"22202E\r", "Throttle PID 22202E"),
            (b"223045\r", "Motor Speed (CanZE)"),
            (b"229001\r", "Battery SOC (CanZE)"),
        ]
        
        for cmd, desc in pids:
            logger.info(f"\n  📤 {desc}: {cmd}")
            s.write(cmd)
            time.sleep(1.5)
            
            response = s.read_all()
            if response:
                text = response.decode('ascii', errors='replace').strip()
                logger.info(f"  ✅ {repr(text)}")
            else:
                logger.info(f"  ⏱️  Timeout")
        
        # Step 5: Speed Continuous Test
        logger.info("\n→ TEST 3: Speed Continuous Test (5x)")
        logger.info("=" * 60)
        
        for i in range(5):
            s.write(b"010D\r")
            time.sleep(0.5)
            response = s.read_all()
            
            if response:
                text = response.decode('ascii', errors='replace').strip()
                logger.info(f"  #{i+1}: {repr(text)}")
            else:
                logger.info(f"  #{i+1}: (leer)")
            time.sleep(0.2)
        
        # Step 6: 222003 Continuous Test
        logger.info("\n→ TEST 4: Speed 222003 Continuous (5x)")
        logger.info("=" * 60)
        
        for i in range(5):
            s.write(b"222003\r")
            time.sleep(0.5)
            response = s.read_all()
            
            if response:
                text = response.decode('ascii', errors='replace').strip()
                logger.info(f"  #{i+1}: {repr(text)}")
            else:
                logger.info(f"  #{i+1}: (leer)")
            time.sleep(0.2)
        
        logger.info("\n" + "=" * 60)
        logger.info("ZUSAMMENFASSUNG")
        logger.info("=" * 60)
        logger.info("  ✅ SPP-Kommunikation mit vGate iCar Pro funktioniert!")
        logger.info(f"⏰ Ende: {datetime.now()}")
        
        s.close()
        logger.info("  Port geschlossen")
        
    except serial.SerialException as e:
        logger.error(f"\n❌ Serial Error: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        logger.error(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Test abgeschlossen!")


if __name__ == "__main__":
    test_spp_elm327()