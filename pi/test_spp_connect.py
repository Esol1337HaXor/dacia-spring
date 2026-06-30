#!/usr/bin/env python3
"""Testet die SPP-Verbindung über rfcomm0."""
import serial
import time

PORT = "/dev/rfcomm0"
BAUD = 38400

print(f"Opening {PORT} at {BAUD}...")
try:
    s = serial.Serial(PORT, BAUD, timeout=2.0)
    print(f"Port opened: {s.is_open}")
    
    # ELM327 init
    cmds = [b"AT\r", b"ATE0\r", b"ATH0\r", b"ATS0\r", b"ATSP 0\r"]
    for cmd in cmds:
        s.write(cmd)
        time.sleep(0.5)
        resp = s.read_all().decode('ascii', errors='replace').strip()
        print(f"  {cmd.decode().strip()} -> {resp}")
    
    # Read Speed
    print("\nReading Speed (222003)...")
    s.write(b"222003\r")
    time.sleep(1.0)
    resp = s.read_all().decode('ascii', errors='replace').strip()
    print(f"  Response: {resp}")
    
    # Read Throttle
    print("\nReading Throttle (22202E)...")
    s.write(b"22202E\r")
    time.sleep(1.0)
    resp = s.read_all().decode('ascii', errors='replace').strip()
    print(f"  Response: {resp}")
    
    s.close()
    print("\n✅ SPP connection test successful!")
except Exception as e:
    print(f"❌ Error: {e}")