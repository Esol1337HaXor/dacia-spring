#!/usr/bin/env python3
"""Test ELM327 TCP Server connection"""
import socket

server_host = "192.168.178.87"
server_port = 4000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((server_host, server_port))
s.settimeout(5)

print(f"Verbunden mit {server_host}:{server_port}")
print("=" * 50)

# Welcome message
welcome = s.recv(1024).decode()
print(f"WELCOME: {welcome}")

# Test commands
commands = [
    ("ATZ", "Reset"),
    ("ATI", "Geräte-Info"),
    ("ATE0", "Echo aus"),
    ("0100", "Supported PIDs"),
    ("010C", "RPM"),
    ("010D", "Speed"),
]

for cmd, desc in commands:
    s.send((cmd + "\r").encode())
    response = s.recv(1024).decode()
    print(f"{cmd:6s} ({desc:20s}): {response.strip()}")

s.close()
print("=" * 50)
print("Test abgeschlossen!")