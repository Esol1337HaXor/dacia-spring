#!/usr/bin/env python3
"""Test obd2_data_pipeline.py - liest Echte OBD2-Daten über TCP."""
import socket
import time
import json
import sys
import os

def test_tcp_obd2():
    """Teste TCP-Verbindung zum ELM327 Server."""
    host = "127.0.0.1"
    port = 2117
    
    print("=" * 50)
    print("ELM327 TCP OBD2 Live-Test")
    print(f"Ziel: {host}:{port}")
    print("=" * 50)
    
    try:
        # Verbindung
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))
        print("\n✅ Verbunden!")
        
        # Welcome lesen
        sock.settimeout(1.0)
        welcome = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                welcome += chunk
            except socket.timeout:
                break
        print(f"Welcome: {welcome.decode('ascii', errors='ignore').strip()}")
        
        # OBD2 PIDs abfragen
        pids = [
            ("0100", "Supported PIDs"),
            ("010C", "Engine RPM"),
            ("010D", "Vehicle Speed"),
            ("0105", "Coolant Temp"),
            ("0104", "Engine Load"),
            ("010F", "Intake Air Temp"),
            ("0111", "Control Module Voltage"),
        ]
        
        print("\n--- OBD2 PID Tests ---")
        results = {}
        
        for pid, desc in pids:
            sock.sendall(f"{pid}\r".encode())
            time.sleep(0.5)
            
            sock.settimeout(1.0)
            response = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
            except socket.timeout:
                pass
            
            # Antwort bereinigen
            text = response.decode('ascii', errors='ignore').strip()
            # Prompt entfernen
            if '>' in text:
                text = text.split('>', 1)[0].strip()
            
            results[pid] = text
            print(f"  {pid} ({desc:30s}): {text}")
        
        # RPM berechnen wenn verfügbar
        if '010C' in results and results['010C'].startswith('41 0C'):
            rpm_hex = results['010C'].split()[2:]
            if len(rpm_hex) >= 2:
                rpm = (256 * int(rpm_hex[0], 16) + int(rpm_hex[1], 16)) / 4
                print(f"\n💡 RPM berechnet: {rpm:.0f} RPM")
        
        # Speed anzeigen
        if '010D' in results and results['010D'].startswith('41 0D'):
            speed = int(results['010D'].split()[2], 16)
            print(f"💡 Speed: {speed} km/h")
        
        print("\n--- JSON Output ---")
        print(json.dumps(results, indent=2))
        
        sock.close()
        print("\n✅ Test abgeschlossen!")
        return results
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        return None

if __name__ == "__main__":
    results = test_tcp_obd2()
    sys.exit(0 if results else 1)