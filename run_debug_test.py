#!/usr/bin/env python3
"""
Auto-Test Script — Startet Debug-Server V2 für 15 Sekunden, stoppt ihn dann

Zweck:
- RevHeadz hat 15 Sekunden Zeit zum Verbinden
- Server wird automatisch gestoppt
- Kann beliebig oft wiederholt werden

Nutzung:
    python run_debug_test.py
"""

import subprocess
import time
import sys
import os

DEBUG_PORT = 2118  # Pi-Server nutzt 2117 — Debug auf 2118!
TEST_DURATION = 15  # Sekunden

def main():
    print("=" * 60)
    print("DEBUG SERVER AUTO-TEST")
    print(f"  Server: debug_server_v2.py")
    print(f"  Port: {DEBUG_PORT}")
    print(f"  Dauer: {TEST_DURATION} Sekunden")
    print(f"  Log: revheadz_debug_v2.log")
    print("=" * 60)
    print()
    
    # Log-File löschen
    if os.path.exists("revheadz_debug_v2.log"):
        os.remove("revheadz_debug_v2.log")
        print("Log-File gelöscht")
    
    print(f"\n✅ Server startet in 3 Sekunden...")
    print(f"   RevHeadz JETZT verbinden zu: 192.168.178.197:{DEBUG_PORT}")
    print()
    time.sleep(3)
    
    # Debug-Server starten
    print("🚀 Server wird gestartet...")
    process = subprocess.Popen(
        [sys.executable, "debug_server_v2.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print(f"✅ Server PID: {process.pid}")
    print(f"⏱️  Test läuft ({TEST_DURATION}s) — RevHeadz verbinden!")
    print()
    
    # Warten
    start_time = time.time()
    try:
        while time.time() - start_time < TEST_DURATION:
            elapsed = int(time.time() - start_time)
            remaining = TEST_DURATION - elapsed
            print(f"\r   Verbleibend: {remaining}s ", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nAbgebrochen!")
    
    print("\n")
    print("=" * 60)
    print("Test beendet!")
    print("=" * 60)
    
    # Server stoppen
    print("🛑 Server wird gestoppt...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except:
        process.kill()
    
    print("✅ Server gestoppt")
    
    # Log ausgeben
    print("\n" + "=" * 60)
    print("LOG-AUSGABE:")
    print("=" * 60)
    
    if os.path.exists("revheadz_debug_v2.log"):
        with open("revheadz_debug_v2.log", "r", encoding="utf-8") as f:
            content = f.read()
        
        if content:
            print(content)
            
            # Analyse
            print("\n" + "=" * 60)
            print("ZUSAMMENFASSUNG:")
            print("=" * 60)
            
            lines = content.split('\n')
            
            # Unique Commands zählen
            commands = set()
            for line in lines:
                if '[CMD]' in line:
                    # Command extrahieren
                    if ':' in line:
                        cmd_part = line.split(':', 1)[1].strip()
                        commands.add(cmd_part[:50])
            
            print(f"  Unique Commands: {len(commands)}")
            for cmd in sorted(commands):
                print(f"    - {cmd}")
            
            # Prüfen ob Throttle-PIDs vorkommen
            throttle_pids = ['0111', '0146', '0142']
            for pid in throttle_pids:
                count = content.count(pid)
                print(f"  PID {pid} Anfragen: {count}")
            
            # Prüfen ob Speed/RPM angezeigt
            speed_count = content.count('010D')
            rpm_count = content.count('010C')
            print(f"\n  Speed-Anfragen (010D): {speed_count}")
            print(f"  RPM-Anfragen (010C): {rpm_count}")
            
        else:
            print(f"❌ LEERES LOG — RevHeadz hat sich NICHT verbunden!")
            print(f"   Tipp: Verbinde REVHEADZ zu 192.168.178.197:{DEBUG_PORT}")
    else:
        print("❌ KEIN LOG-FILE — Server lief eventuell nicht!")
    
    print("\n" + "=" * 60)
    print("FERTIG! Drücke ENTER für nächsten Test...")
    print("=" * 60)
    input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAbgebrochen!")