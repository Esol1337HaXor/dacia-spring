#!/usr/bin/env python3
"""Schneller Validator-Test gegen Echo-Server."""
import sys
sys.path.insert(0, '/home/lsd/obd2-adapter')

from adapter_validator import *

# Validator erstellen
v = ELM327Validator(
    connection_type=ConnectionType.TCP,
    target='127.0.0.1:2118',
    timeout=5.0
)

# Manuell testen
v.connect()
print(f"Connected: {v.is_connected}")

print("\n=== Test ATZ ===")
r = v.send_command('ATZ', strip_prompt=True)
print(f"Response: '{r}'")
print(f"Has elm327: {'elm327' in r.lower()}")

print("\n=== Test ATI ===")
r = v.send_command('ATI', strip_prompt=True)
print(f"Response: '{r}'")

print("\n=== Test 0100 ===")
r = v.send_command('0100', strip_prompt=True)
print(f"Response: '{r}'")

print("\n=== Test ATSP0 ===")
r = v.send_command('ATSP0', strip_prompt=True)
print(f"Response: '{r}'")

print("\n=== Test ATDPN ===")
r = v.send_command('ATDPN', strip_prompt=True)
print(f"Response: '{r}'")

v.disconnect()