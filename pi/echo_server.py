#!/usr/bin/env python3
"""Einfacher ELM327 Echo-Server zum Testen des Validators."""
import socket
import threading
import time

def handler(conn):
    conn.sendall(b'ELM327 v2.3\r\nOK\r\n> ')
    while True:
        data = conn.recv(1024)
        if not data: break
        cmd = data.decode('ascii', errors='ignore').strip()
        echo = cmd + '\r\n'
        if cmd == 'ATZ': echo += 'ELM327 v2.3\r\nOK\r\n> '
        elif cmd == 'ATI': echo += 'ELM327 Sport\r\n> '
        elif cmd == 'ATSP0': echo += 'OK\r\n> '
        elif cmd == 'ATDPN': echo += '6\r\n> '
        elif cmd in ('0100','010C','010D','0105','0104'): echo += '41 00 98 18 00 00\r\n> '
        else: echo += 'NO DATA\r\n> '
        conn.sendall(echo.encode())
    conn.close()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1', 2118))
s.listen(3)
print('Echo server auf Port 2118')
while True:
    c,a = s.accept()
    threading.Thread(target=handler, args=(c,), daemon=True).start()