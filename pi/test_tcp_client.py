#!/usr/bin/env python3
"""
Einfacher TCP-Test f체r den ELM327 Server auf dem Pi.

Auf dem Pi ausf체hren:
  cd ~/obd2-adapter
  source ~/obd2-adapter-env/bin/activate
  python3 test_tcp_client.py
"""

import socket
import time

SERVER_IP = "127.0.0.1"
SERVER_PORT = 2117
TIMEOUT = 3  # Sekunden

def test_connection():
    print("=" * 50)
    print("ELM327 TCP Server Test")
    print(f"  Ziel: {SERVER_IP}:{SERVER_PORT}")
    print("=" * 50)
    print()
    
    try:
        # Socket erstellen
        print("[1] Erstelle Socket...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        print("    OK")
        
        # Connect
        print(f"[2] Verbinde zu {SERVER_IP}:{SERVER_PORT}...")
        s.connect((SERVER_IP, SERVER_PORT))
        print("    Verbunden!")
        
        # Willkommen lesen
        print("[3] Warte auf Willkommensnachricht...")
        time.sleep(1)
        try:
            welcome = s.recv(4096).decode('utf-8', errors='ignore')
            print(f"    Empfangen ({len(welcome)} bytes):")
            print(f"    '{welcome.strip()}'")
        except socket.timeout:
            print("    TIMEOUT - keine WillkommenNachricht")
        
        # ATZ senden
        print()
        print("[4] Sende ATZ...")
        s.sendall(b'ATZ\r')
        time.sleep(1)
        try:
            resp = s.recv(4096).decode('utf-8', errors='ignore')
            print(f"    Antwort: '{resp.strip()}'")
        except socket.timeout:
            print("    TIMEOUT - keine Antwort")
        
        # Supported PIDs
        print()
        print("[5] Sende 0100 (Supported PIDs)...")
        s.sendall(b'0100\r')
        time.sleep(1)
        try:
            resp = s.recv(4096).decode('utf-8', errors='ignore')
            print(f"    Antwort: '{resp.strip()}'")
        except socket.timeout:
            print("    TIMEOUT - keine Antwort")
        
        # RPM
        print()
        print("[6] Sende 010C (RPM)...")
        s.sendall(b'010C\r')
        time.sleep(1)
        try:
            resp = s.recv(4096).decode('utf-8', errors='ignore')
            print(f"    Antwort: '{resp.strip()}'")
        except socket.timeout:
            print("    TIMEOUT - keine Antwort")
        
        # Speed
        print()
        print("[7] Sende 010D (Speed)...")
        s.sendall(b'010D\r')
        time.sleep(1)
        try:
            resp = s.recv(4096).decode('utf-8', errors='ignore')
            print(f"    Antwort: '{resp.strip()}'")
        except socket.timeout:
            print("    TIMEOUT - keine Antwort")
        
        print()
        print("=" * 50)
        print("TEST VOLLSTANDIG")
        print("=" * 50)
        
    except ConnectionRefusedError:
        print("FEHLER: Verbindung abgelehnt!")
        print("  Server l鋟ft wahrscheinlich nicht.")
        print("  Starte: python3 elm327_ble_tcp_server.py --no-ble")
    except socket.timeout:
        print("FEHLER: Timeout - Server antwortet nicht")
    except Exception as e:
        print(f"FEHLER: {e}")
    finally:
        try:
            s.close()
        except:
            pass


if __name__ == "__main__":
    test_connection()