#!/usr/bin/env python3
"""Debug: Warum Validator empty responses liefert."""
import socket
import time

# 1. Einfacher TCP-Test direkt
print("=== Direkter TCP-Test ===")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5.0)
s.connect(('127.0.0.1', 2118))

# Welcome lesen
s.settimeout(0.5)
welcome = b""
try:
    while True:
        chunk = s.recv(4096)
        if not chunk: break
        welcome += chunk
except: pass
print(f"Welcome: {welcome!r}")

# Timeout zurücksetzen
s.settimeout(5.0)

# ATZ mit genau demselben Code wie Validator
print("\n=== ATZ (Validator-Code) ===")
s.sendall(b"ATZ\r")
time.sleep(0.2)

s.settimeout(0.3)
response = ""
for i in range(5):
    try:
        chunk = s.recv(4096)
        if chunk:
            response += chunk.decode('ascii', errors='ignore')
            print(f"  Read #{i+1}: {chunk!r} (total: {response!r})")
        else:
            print(f"  Read #{i+1}: empty (connection closed)")
            break
    except socket.timeout:
        print(f"  Read #{i+1}: timeout")
        break
    except Exception as e:
        print(f"  Read #{i+1}: error: {e}")
        break

print(f"\nFinal response: '{response}'")

s.close()