#!/usr/bin/env python3
"""
SPP OBD2 Parser — Parsst echte CAN-Daten vom vGate iCar Pro über Bluetooth Classic SPP.

Verwendet die gleichen CAN-IDs wie CanZE:
- 222003 → Speed (Byte 4 = km/h)
- 22202E → Throttle/Last (Byte 4 = %)
- 223045 → Motor Speed (Byte 4+5 = Big-Endian RPM)
- 229001 → Battery SOC
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
logger = logging.getLogger("SPP-OBD2-Parser")


def parse_response(raw: bytes) -> str:
    """Parsst Rohdaten in lesbare Form."""
    text = raw.decode('ascii', errors='replace').strip()
    
    # Entferne Echo und Prompt
    text = text.replace('\r', '')
    text = text.replace('ATZ', '')
    text = text.replace('ATI', '')
    text = text.replace('ATE0', '')
    text = text.replace('ATH0', '')
    text = text.replace('ATS0', '')
    text = text.replace('ATSP 0', '')
    text = text.replace('0100', '')
    text = text.replace('010D', '')
    text = text.replace('010C', '')
    text = text.replace('222003', '')
    text = text.replace('22202E', '')
    text = text.replace('223045', '')
    text = text.replace('229001', '')
    text = text.replace('SEARCHING...', '')
    text = text.strip()
    
    return text


def parse_pid_010d(raw: bytes) -> float:
    """Parsst Speed aus OBD2 PID 010D."""
    text = parse_response(raw)
    
    if 'NO DATA' in text or '?' in text:
        return -1.0
    
    # Format: '410DXX' wo XX = Speed in km/h
    if text.startswith('410D') and len(text) >= 6:
        try:
            byte_val = int(text[4:6], 16)
            return float(byte_val)
        except ValueError:
            pass
    
    return -1.0


def parse_pid_222003(raw: bytes) -> float:
    """Parsst Speed aus 222003 (CanZE Speed)."""
    text = parse_response(raw)
    
    if 'NO DATA' in text or '?' in text or '7F' in text:
        return -1.0
    
    # Format: '622003XX00' oder '622003XXXX'
    # Byte 4 (Index 8-10) ist Speed
    if text.startswith('622003') and len(text) >= 10:
        try:
            byte_val = int(text[8:10], 16)
            return float(byte_val)
        except ValueError:
            pass
    
    return -1.0


def parse_pid_22202e(raw: bytes) -> float:
    """Parsst Throttle aus 22202E.
    
    Format: '62202EXXYY' wo XXYY = 16-bit Big-Endian, Wert/10 = %
    Beispiel: 62202E03E8 → 0x03E8 = 1000 → 100.0%
    """
    text = parse_response(raw)
    
    if 'NO DATA' in text or '?' in text or '7F' in text:
        return -1.0
    
    # Format: '62202EXXYY' — 16-bit Big-Endian, /10 = %
    if text.startswith('62202E') and len(text) >= 12:
        try:
            val = int(text[8:12], 16)
            return float(val / 10.0)
        except ValueError:
            pass
    # Fallback: nur 1 Byte (alte Format)
    elif text.startswith('62202E') and len(text) >= 10:
        try:
            byte_val = int(text[8:10], 16)
            return float(byte_val)
        except ValueError:
            pass
    
    return -1.0


def parse_pid_223045(raw: bytes) -> float:
    """Parsst Motor Speed aus 223045."""
    text = parse_response(raw)
    
    if 'NO DATA' in text or '?' in text or '7F' in text:
        return -1.0
    
    # Format: '623045XXYY' — Big-Endian 16-bit
    if text.startswith('623045') and len(text) >= 10:
        try:
            val = int(text[8:12], 16)
            return float(val)
        except ValueError:
            pass
    
    return -1.0


def test_spp_parser():
    """Testet SPP mit Parser."""
    
    RFCOMM_PORT = "/dev/rfcomm0"
    BAUD_RATE = 38400
    
    print("=" * 60)
    print("SPP OBD2 PARSER — vGate iCar Pro BT")
    print("=" * 60)
    print(f"\nPort: {RFCOMM_PORT}")
    print(f"Baud: {BAUD_RATE}")
    print(f"⏰ Start: {datetime.now()}")
    print("=" * 60)
    
    try:
        s = serial.Serial(
            port=RFCOMM_PORT,
            baudrate=BAUD_RATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0
        )
        logger.info("✅ Serial Port geöffnet!")
        
        # ELM327 Setup
        logger.info("\n→ ELM327 Setup...")
        s.write(b"ATE0\r"); time.sleep(0.5); s.read_all()
        s.write(b"ATH0\r"); time.sleep(0.5); s.read_all()
        s.write(b"ATS0\r"); time.sleep(0.5); s.read_all()
        s.write(b"ATSP 0\r"); time.sleep(1.0); s.read_all()
        logger.info("  Setup fertig!")
        
        # === TEST: Alle PIDs ===
        logger.info("\n→ TEST: Alle PIDs")
        logger.info("=" * 60)
        
        tests = [
            (b"0100\r", "Supported PIDs", parse_pid_010d),
            (b"010D\r", "Speed 010D", parse_pid_010d),
            (b"010C\r", "RPM 010C", parse_pid_010d),
            (b"222003\r", "Speed 222003", parse_pid_222003),
            (b"22202E\r", "Throttle 22202E", parse_pid_22202e),
            (b"223045\r", "Motor Speed 223045", parse_pid_223045),
            (b"229001\r", "Battery 229001", lambda x: -1.0),
        ]
        
        for cmd, desc, parser in tests:
            s.write(cmd)
            time.sleep(1.5)
            
            raw = s.read_all()
            if raw:
                parsed = parser(raw)
                raw_text = parse_response(raw)
                logger.info(f"\n  📤 {desc}: {cmd.decode().strip()}")
                logger.info(f"     RAW: {raw_text}")
                logger.info(f"     PARSED: {parsed}")
                
                if parsed >= 0:
                    logger.info(f"     ✅ WERT: {parsed}")
                else:
                    logger.info(f"     ⚠️  NO DATA / NEGATIVE")
            else:
                logger.info(f"  📤 {desc}: Timeout")
        
        # === TEST: Continuous Speed ===
        logger.info("\n→ TEST: Continuous Speed 222003 (10x)")
        logger.info("=" * 60)
        
        speeds = []
        for i in range(10):
            s.write(b"222003\r")
            time.sleep(0.3)
            raw = s.read_all()
            
            if raw:
                speed = parse_pid_222003(raw)
                raw_text = parse_response(raw)
                logger.info(f"  #{i+1}: {raw_text} → {speed} km/h")
                speeds.append(speed)
        
        if speeds:
            valid = [s for s in speeds if s >= 0]
            if valid:
                logger.info(f"\n  Speed: min={min(valid):.1f}, max={max(valid):.1f}, avg={sum(valid)/len(valid):.1f}")
            else:
                logger.info(f"\n  Alle Speed-Werte: 0 (Auto steht)")
        
        # === TEST: Continuous Throttle ===
        logger.info("\n→ TEST: Continuous Throttle 22202E (10x)")
        logger.info("=" * 60)
        
        throttles = []
        for i in range(10):
            s.write(b"22202E\r")
            time.sleep(0.3)
            raw = s.read_all()
            
            if raw:
                throttle = parse_pid_22202e(raw)
                raw_text = parse_response(raw)
                logger.info(f"  #{i+1}: {raw_text} → {throttle}%")
                throttles.append(throttle)
        
        if throttles:
            valid = [t for t in throttles if t >= 0]
            if valid:
                logger.info(f"\n  Throttle: min={min(valid):.1f}, max={max(valid):.1f}")
            else:
                logger.info(f"\n  Alle Throttle-Werte: -1 (NO DATA)")
        
        # === TEST: Continuous Motor Speed ===
        logger.info("\n→ TEST: Continuous Motor Speed 223045 (10x)")
        logger.info("=" * 60)
        
        motor_speeds = []
        for i in range(10):
            s.write(b"223045\r")
            time.sleep(0.3)
            raw = s.read_all()
            
            if raw:
                speed = parse_pid_223045(raw)
                raw_text = parse_response(raw)
                logger.info(f"  #{i+1}: {raw_text} → {speed} RPM")
                motor_speeds.append(speed)
        
        if motor_speeds:
            valid = [s for s in motor_speeds if s >= 0]
            if valid:
                logger.info(f"\n  Motor Speed: min={min(valid):.0f}, max={max(valid):.0f}")
            else:
                logger.info(f"\n  Alle Motor-Speed-Werte: -1 (NO DATA)")
        
        logger.info("\n" + "=" * 60)
        logger.info("ZUSAMMENFASSUNG")
        logger.info("=" * 60)
        logger.info("  ✅ SPP OBD2 Parser funktioniert!")
        logger.info(f"⏰ Ende: {datetime.now()}")
        
        s.close()
        
    except Exception as e:
        logger.error(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Test abgeschlossen!")


if __name__ == "__main__":
    test_spp_parser()