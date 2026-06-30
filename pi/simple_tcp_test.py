#!/usr/bin/env python3
"""Minimaler TCP-Test für ELM327 Echo-Server."""
import socket
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5.0)
s.connect(('127.0.0.1', 2118))

# Welcome lesen
s.settimeout(1.0)
welcome = b""
try:
    while True:
        chunk = s.recv(4096)
        if not chunk: break
        welcome += chunk
except: pass
print(f"Welcome: {welcome!r}")

# ATZ senden
s.sendall(b"ATZ\r")
time.sleep(0.5)
resp = s.recv(4096)
print(f"ATZ: {resp!r}")

# ATI senden
s.sendall(b"ATI\r")
time.sleep(0.5)
resp = s.recv(4096)
print(f"ATI: {resp!r}")

# 0100 senden
s.sendall(b"0100\r")
time.sleep(0.5)
resp = s.recv(4096)
print(f"0100: {resp!r}")

s.close()