#!/usr/bin/env python3
"""
SPP Baudrate Scan — Testet verschiedene Baudraten für vGate iCar Pro.
"""
import serial
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SPP-Baud-Scan")


def test_baud_rate(port, baudrate):
    """Testet eine einzelne Baudrate."""
    try:
        s = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0
        )
        
        # Puffer leer
        s.reset_input_buffer()
        time.sleep(0.2)
        
        # ATZ senden
        s.write(b"ATZ\r")
        time.sleep(2.0)
        
        # Antwort lesen
        response = s.read_all()
        s.close()
        
        return response
        
    except serial.SerialException as e:
        return f"ERROR: {e}"


def main():
    print("=" * 60)
    print("SPP BAUDRATE SCAN — vGate iCar Pro")
    print("=" * 60)
    print(f"\nPort: /dev/rfcomm0")
    print("Test: ATZ Befehl bei verschiedenen Baudraten")
    print("=" * 60)
    
    baudrates_to_try = [
        1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600
    ]
    
    for baud in baudrates_to_try:
        print(f"\n  Test: {baud} baud...")
        response = test_baud_rate("/dev/rfcomm0", baud)
        
        if response and isinstance(response, bytes) and len(response) > 0:
            text = response.decode('ascii', errors='replace').strip()
            hex_str = ' '.join(f'{b:02X}' for b in response)
            print(f"    ✅ ANSWER FOUND at {baud} baud!")
            print(f"       TEXT: {repr(text)}")
            print(f"       HEX:  {hex_str}")
            print(f"       LEN:  {len(response)} bytes")
            
            # Wenn Antwort gefunden — sofort stoppen!
            print(f"\n  🎯 RICHTIGE BAUDRATE: {baud}")
            return baud
        else:
            print(f"    ⏱️  Timeout / Keine Antwort")
    
    print("\n" + "=" * 60)
    print("⚠️  KEINE BAUDRATE FUNKTIONIERT!")
    print("=" * 60)
    
    # Vielleicht ist rfcomm nicht wirklich connected?
    print("\n→ Mögliche Ursachen:")
    print("   1. vGate iCar Pro ist nicht connected (bluetoothctl: connect 13:E0:2F:8D:61:07)")
    print("   2. Auto ist nicht im ON-Modus (OBD2-Stromlos)")
    print("   3. rfcomm0 ist stale — mit rfcomm release /dev/rfcomm0 neu erstellen")
    return -1


if __name__ == "__main__":
    result = main()
    print(f"\n\nErgebnis: Baudrate {result}")