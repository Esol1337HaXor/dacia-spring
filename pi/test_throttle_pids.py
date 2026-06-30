#!/usr/bin/env python3
"""Testet Throttle/Pedal-Position PIDs über BLE Notify."""
import socket
import time
import json
import sys

def test_throttle_pids():
    """Teste alle relevanten Throttle/Pedal PIDs."""
    host = "127.0.0.1"
    port = 2117
    
    print("=" * 60)
    print("Throttle/Pedal Position PID Test")
    print(f"Ziel: {host}:{port}")
    print("=" * 60)
    
    try:
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
                if not chunk: break
                welcome += chunk
            except socket.timeout:
                break
        print(f"Welcome: {welcome.decode('ascii', errors='ignore').strip()}")
        
        # Alle Throttle-relevanten PIDs
        pids = [
            # Pedal Position PIDs
            ("014B", "Pedal Position D (0-100%)"),
            ("014C", "Accelerator Pedal Position D"),
            ("014D", "Accelerator Pedal Position E"),
            ("014E", "Accelerator Pedal Position F"),
            ("019B", "Pedal Position D (alternative)"),
            ("019C", "Accelerator Pedal Position (alternative)"),
            
            # Throttle Position PIDs  
            ("0111", "Control Module Voltage"),
            ("0118", "Absolute Throttle Position D"),
            ("0145", "Fuel Pressure"),  # Für Kontext
            ("0146", "Intake Manifold Pressure"),
            ("011A", "Fuel Rate"),
            
            # Engine Load PIDs
            ("0104", "Calculated Engine Load"),
            ("014C", "Absolute Throttle Position"),
            
            # Zusätzliche EV-relevante PIDs
            ("015B", "Battery Pack Life"),
            ("015C", "Battery Temperature"),
            ("015D", "DC Actuator Control State"),
        ]
        
        print("\n--- PID Test Results ---\n")
        results = {}
        
        for pid, desc in pids:
            sock.sendall(f"{pid}\r".encode())
            time.sleep(0.5)
            
            sock.settimeout(1.0)
            response = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk: break
                    response += chunk
            except socket.timeout:
                pass
            
            # Antwort bereinigen
            text = response.decode('ascii', errors='ignore').strip()
            if '>' in text:
                text = text.split('>', 1)[0].strip()
            
            # Status
            if text.startswith("41"):
                status = "✅"
            elif "NO DATA" in text.upper():
                status = "❌"
            else:
                status = "⚠️"
            
            results[pid] = {
                "response": text,
                "status": "OK" if text.startswith("41") else "NO DATA"
            }
            
            print(f"  {status} {pid:5s} ({desc:45s}): {text}")
        
        print("\n--- Zusammenfassung ---")
        ok_count = sum(1 for r in results.values() if r["status"] == "OK")
        no_data_count = sum(1 for r in results.values() if r["status"] == "NO DATA")
        print(f"  ✅ Antworten: {ok_count}")
        print(f"  ❌ NO DATA: {no_data_count}")
        print(f"  📊 Total: {len(results)}")
        
        print("\n--- JSON Output ---")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
        sock.close()
        return results
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        return None

if __name__ == "__main__":
    results = test_throttle_pids()
    sys.exit(0 if results else 1)