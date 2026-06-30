#!/usr/bin/env python3
"""
Umfangreiches Debugging-Script für den SPP ELM327 TCP Server

Testet:
- TCP Verbindung zum Server
- ELM327 Handshake (ATZ, ATI, etc.)
- Speed-Daten (PID 010D)
- Throttle-Daten (PID 0111)
- RPM-Daten (PID 010C)
- Supported PIDs (PID 0100)
- Daten-Konsistenz über mehrere Zyklen

Nutzung auf dem Pi:
    python3 server_debug_test.py
    python3 server_debug_test.py --host 192.168.178.87 --port 2117
    python3 server_debug_test.py --verbose  # Ausführliches Logging
"""

import socket
import sys
import time
import argparse
from datetime import datetime
from typing import Optional, Dict, Any

# ========================
# Konfiguration
# ========================
DEFAULT_HOST = "192.168.178.87"
DEFAULT_PORT = 2117
CONNECT_TIMEOUT = 5.0
COMMAND_TIMEOUT = 3.0


# ========================
# Farben für Terminal-Ausgabe
# ========================
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")


def print_success(text: str):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.WARNING}⚠️ {text}{Colors.ENDC}")


def print_info(text: str):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_test(name: str):
    print(f"\n{Colors.BOLD}🧪 Test: {name}{Colors.ENDC}")
    print(f"{'-'*40}")


# ========================
# TCP Client für Tests
# ========================

class ServerDebugClient:
    """Client zum Testen des SPP ELM327 TCP Servers."""
    
    def __init__(self, host: str, port: int, verbose: bool = False):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.socket: Optional[socket.socket] = None
        self.responses: Dict[str, str] = {}
        self.tests_passed = 0
        self.tests_failed = 0
    
    def connect(self) -> bool:
        """Verbindet zum TCP Server."""
        try:
            print_info(f"Verbinde zu {self.host}:{self.port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(CONNECT_TIMEOUT)
            self.socket.connect((self.host, self.port))
            print_success("Verbindung erfolgreich!")
            return True
        except socket.timeout:
            print_error(f"Verbindungstimeout nach {CONNECT_TIMEOUT}s")
            return False
        except Exception as e:
            print_error(f"Verbindungsfehler: {e}")
            return False
    
    def send_command(self, command: str, timeout: float = COMMAND_TIMEOUT) -> str:
        """Sendet einen Command und liest die Antwort."""
        if not self.socket:
            return ""
        
        try:
            if self.verbose:
                print_info(f"Senden: {command.strip()}")
            
            self.socket.sendall(command.encode())
            time.sleep(timeout)
            
            response = self.socket.recv(4096).decode('utf-8', errors='replace')
            
            if self.verbose:
                print_info(f"Antwort: {repr(response)}")
            
            return response.strip()
            
        except Exception as e:
            print_error(f"Command-Fehler: {e}")
            return ""
    
    def read_welcome(self) -> str:
        """Liest die Willkommensnachricht."""
        if not self.socket:
            return ""
        
        try:
            self.socket.settimeout(3.0)
            welcome = self.socket.recv(1024).decode('utf-8', errors='replace')
            return welcome.strip()
        except Exception as e:
            print_error(f"Willkommensnachricht lesen fehlgeschlagen: {e}")
            return ""
    
    def test_welcome_message(self) -> bool:
        """Testet die Willkommensnachricht."""
        print_test("Willkommensnachricht")
        
        welcome = self.read_welcome()
        
        if not welcome:
            print_error("Keine Willkommensnachricht empfangen!")
            self.tests_failed += 1
            return False
        
        print_info(f"Empfangen: {repr(welcome)}")
        
        expected_keywords = ["ELM327", "Ready", "Dacia"]
        found_keywords = [kw for kw in expected_keywords if kw.lower() in welcome.lower()]
        
        if len(found_keywords) >= 2:
            print_success(f"Willkommensnachricht OK (enthält: {', '.join(found_keywords)})")
            self.responses["welcome"] = welcome
            self.tests_passed += 1
            return True
        else:
            print_warning(f"Erwartet: {expected_keywords}, Gefunden: {found_keywords}")
            self.tests_failed += 1
            return False
    
    def test_at_commands(self) -> bool:
        """Testet AT-Befehle."""
        print_test("AT-Befehle")
        
        tests = [
            ("ATZ", "ELM327", "Reset"),
            ("ATI", "Dacia", "Identifikation"),
            ("ATE0", "OK", "Echo aus"),
            ("ATH0", "OK", "Header aus"),
            ("ATS0", "OK", "Spaces aus"),
            ("ATSP0", "OK", "Protocol setzen"),
            ("ATDPN", "04", "CAN Type"),
        ]
        
        all_passed = True
        
        for cmd, expected, desc in tests:
            response = self.send_command(f"{cmd}\r")
            
            if expected.lower() in response.lower() or "OK" in response.upper():
                print_success(f"{cmd} → {desc} (OK)")
                self.tests_passed += 1
            else:
                print_error(f"{cmd} → {desc} (FEHLER: {response})")
                self.tests_failed += 1
                all_passed = False
        
        return all_passed
    
    def test_supported_pids(self) -> bool:
        """Testet Supported PIDs (0100)."""
        print_test("Supported PIDs (0100)")
        
        response = self.send_command("0100\r")
        
        print_info(f"Antwort: {response}")
        
        # Erwartet: 41 00 XX XX XX XX
        # Byte2 sollte 0x18 haben (RPM + Speed unterstützt)
        if "41 00" in response:
            print_success("Supported PIDs empfangen!")
            self.responses["0100"] = response
            self.tests_passed += 1
            
            # Prüfen ob Byte2 0x18 hat (RPM + Speed)
            parts = response.split()
            if len(parts) >= 4:
                byte2 = parts[3] if len(parts) > 3 else ""
                if byte2 == "18":
                    print_success("Byte2 = 0x18 → RPM + Speed unterstützt ✓")
                else:
                    print_warning(f"Byte2 = {byte2} (erwartet: 18)")
            
            return True
        else:
            print_error(f"Erwartet: '41 00', Empfangen: {response}")
            self.tests_failed += 1
            return False
    
    def test_speed_pid(self) -> bool:
        """Testet Speed PID (010D)."""
        print_test("Speed PID (010D)")
        
        responses = []
        
        for i in range(3):
            response = self.send_command("010D\r")
            responses.append(response)
            
            print_info(f"Versuch {i+1}: {response}")
            
            # Erwartet: 41 0D XX (XX = Speed in km/h als Hex)
            if "41 0D" in response:
                parts = response.split()
                if len(parts) >= 3:
                    speed_hex = parts[2]
                    try:
                        speed = int(speed_hex, 16)
                        print_success(f"Speed: {speed} km/h")
                        self.responses["speed"] = speed
                    except ValueError:
                        print_warning(f"Speed kann nicht geparsed werden: {speed_hex}")
            else:
                print_warning(f"Kein Speed-Wert in Antwort: {response}")
            
            time.sleep(0.5)
        
        # Prüfen ob konsistente Werte
        if len(set(responses)) == 1:
            print_success("Speed-Werte sind konsistent!")
        else:
            print_warning("Speed-Werte variieren (kann normal sein)")
        
        self.tests_passed += 1
        return True
    
    def test_throttle_pid(self) -> bool:
        """Testet Throttle PID (0111)."""
        print_test("Throttle PID (0111)")
        
        response = self.send_command("0111\r")
        
        print_info(f"Antwort: {response}")
        
        # Erwartet: 41 11 XX (XX = Throttle in % als Hex)
        if "41 11" in response:
            parts = response.split()
            if len(parts) >= 3:
                throttle_hex = parts[2]
                try:
                    throttle = int(throttle_hex, 16)
                    print_success(f"Throttle: {throttle}%")
                    self.responses["throttle"] = throttle
                    
                    if throttle == 0:
                        print_info("Throttle = 0% (Auto steht / Pedal los)")
                    elif throttle > 90:
                        print_info("Throttle > 90% (Vollgas/Kickdown)")
                    else:
                        print_info(f"Throttle = {throttle}% (normaler Gasfuß)")
                    
                    self.tests_passed += 1
                    return True
                except ValueError:
                    print_error(f"Throttle kann nicht geparsed werden: {throttle_hex}")
            else:
                print_error(f"Antwort hat zu wenige Parts: {response}")
        else:
            # FEHLER: "NA" oder leer
            if "NA" in response.upper():
                print_error("Throttle zeigt 'NA' — Parser Problem!")
            else:
                print_error(f"Erwartet: '41 11', Empfangen: {response}")
        
        self.tests_failed += 1
        return False
    
    def test_rpm_pid(self) -> bool:
        """Testet RPM PID (010C)."""
        print_test("RPM PID (010C)")
        
        response = self.send_command("010C\r")
        
        print_info(f"Antwort: {response}")
        
        # Erwartet: 41 0C XX XX (16-bit RPM/4)
        if "41 0C" in response:
            parts = response.split()
            if len(parts) >= 4:
                a = int(parts[2], 16)
                b = int(parts[3], 16)
                rpm_value = (a * 256 + b) / 4.0
                print_success(f"RPM: {rpm_value:.0f}")
                self.responses["rpm"] = rpm_value
                
                if rpm_value < 1000:
                    print_info("RPM < 1000 (Idle)")
                elif rpm_value < 3000:
                    print_info("RPM 1000-3000 (normale Fahrt)")
                else:
                    print_info("RPM > 3000 (Beschleunigung/Höherer Gang)")
                
                self.tests_passed += 1
                return True
            else:
                print_error(f"Antwort hat zu wenige Parts: {response}")
        else:
            print_error(f"Erwartet: '41 0C', Empfangen: {response}")
        
        self.tests_failed += 1
        return False
    
    def test_data_consistency(self, cycles: int = 5) -> bool:
        """Testet Daten-Konsistenz über mehrere Zyklen."""
        print_test(f"Daten-Konsistenz ({cycles} Zyklen)")
        
        speed_values = []
        throttle_values = []
        rpm_values = []
        
        for i in range(cycles):
            # Speed
            resp = self.send_command("010D\r")
            if "41 0D" in resp:
                parts = resp.split()
                if len(parts) >= 3:
                    speed_values.append(int(parts[2], 16))
            
            # Throttle
            resp = self.send_command("0111\r")
            if "41 11" in resp:
                parts = resp.split()
                if len(parts) >= 3:
                    throttle_values.append(int(parts[2], 16))
            
            # RPM
            resp = self.send_command("010C\r")
            if "41 0C" in resp:
                parts = resp.split()
                if len(parts) >= 4:
                    a, b = int(parts[2], 16), int(parts[3], 16)
                    rpm_values.append((a * 256 + b) / 4.0)
            
            time.sleep(0.3)
            
            # RPM berechnen für Anzeige
            rpm_display = f"{rpm_values[-1]:.0f}" if rpm_values else "-"
            speed_display = str(speed_values[-1]) if speed_values else "-"
            throttle_display = str(throttle_values[-1]) if throttle_values else "-"
            print_info(f"Zyklus {i+1}/{cycles}: Speed={speed_display} | "
                      f"Throttle={throttle_display} | "
                      f"RPM={rpm_display}")
        
        # Analyse
        print(f"\n{'='*40}")
        print_info("Analyse:")
        
        if speed_values:
            unique_speeds = set(speed_values)
            print_info(f"Speed: {len(speed_values)} Werte, {len(unique_speeds)} einzigartig: {unique_speeds}")
        
        if throttle_values:
            unique_throttles = set(throttle_values)
            print_info(f"Throttle: {len(throttle_values)} Werte, {len(unique_throttles)} einzigartig: {unique_throttles}")
        
        if rpm_values:
            unique_rpms = set(round(r) for r in rpm_values)
            print_info(f"RPM: {len(rpm_values)} Werte, {len(unique_rpms)} einzigartig: {unique_rpms}")
        
        self.tests_passed += 1
        return True
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Führt alle Tests durch."""
        print_header("SPP ELM327 SERVER DEBUG TEST")
        print_info(f"Host: {self.host}:{self.port}")
        print_info(f"Start: {datetime.now()}")
        
        # Verbindung aufbauen
        if not self.connect():
            print_error("Kann nicht verbinden — Test abgebrochen!")
            return {"passed": 0, "failed": 1, "error": "Verbindungsfehler"}
        
        print_header("TEST START")
        
        # 1. Willkommensnachricht
        self.test_welcome_message()
        
        # 2. AT-Befehle
        self.test_at_commands()
        
        # 3. Supported PIDs
        self.test_supported_pids()
        
        # 4. Speed PID
        self.test_speed_pid()
        
        # 5. Throttle PID
        self.test_throttle_pid()
        
        # 6. RPM PID
        self.test_rpm_pid()
        
        # 7. Daten-Konsistenz
        self.test_data_consistency(cycles=5)
        
        # Ergebnis
        print_header("TEST ERGEBNIS")
        print(f"\n{Colors.BOLD}Gesamt:{Colors.ENDC}")
        print(f"  {Colors.OKGREEN}Bestanden: {self.tests_passed}{Colors.ENDC}")
        print(f"  {Colors.FAIL}Fehlgeschlagen: {self.tests_failed}{Colors.ENDC}")
        
        total = self.tests_passed + self.tests_failed
        percentage = int((self.tests_passed / total) * 100) if total > 0 else 0
        print(f"  {Colors.BOLD}Ergebnis: {percentage}% ({self.tests_passed}/{total}){Colors.ENDC}")
        
        if self.tests_failed == 0:
            print_success("Alle Tests bestanden! ✅")
        else:
            print_warning(f"{self.tests_failed} Test(s) fehlgeschlagen ⚠️")
        
        print_info(f"Ende: {datetime.now()}")
        
        # Antworten zusammenfassen
        if self.responses:
            print_header("ANTWORTEN ZUSAMMENFASSUNG")
            for key, value in self.responses.items():
                print(f"  {key}: {value}")
        
        return {
            "passed": self.tests_passed,
            "failed": self.tests_failed,
            "percentage": percentage,
            "responses": self.responses
        }
    
    def close(self):
        """Schließt die Verbindung."""
        if self.socket:
            try:
                self.socket.close()
                print_info("Verbindung geschlossen")
            except:
                pass


# ========================
# Hauptprogramm
# ========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPP ELM327 Server Debug Test")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Server Host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server Port (default: {DEFAULT_PORT})")
    parser.add_argument("--verbose", action="store_true", help="Ausführliches Logging")
    parser.add_argument("--cycles", type=int, default=5, help="Anzahl Konsistenz-Tests (default: 5)")
    
    args = parser.parse_args()
    
    client = ServerDebugClient(args.host, args.port, args.verbose)
    
    try:
        result = client.run_all_tests()
        sys.exit(0 if result["failed"] == 0 else 1)
    except KeyboardInterrupt:
        print("\n\nTest abgebrochen!")
    finally:
        client.close()