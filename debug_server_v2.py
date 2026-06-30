#!/usr/bin/env python3
"""
Debug ELM327 TCP Server V2 — Mit Speed + RPM Simulation

Zweck:
- Simuliert Speed (0-120 km/h im Kreis)
- Simuliert RPM basierend auf Speed
- Protokolliert JEDEN Command von RevHeadz
- Findet heraus wie RevHeadz Throttle ermittelt

Nutzung:
    python3 debug_server_v2.py
    
Port: 2117
Verbindung vom Android: 192.168.178.197:2117
"""

import socket
import sys
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# ========================
# Konfiguration
# ========================
TCP_PORT = 2118  # Pi-Server nutzt 2117 — Debug auf 2118!
HOST = "0.0.0.0"

# Logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("revheadz_debug_v2.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("debug-elm327-v2")

# ========================
# Farbcodes
# ========================
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_command(text: str):
    print(f"{Colors.RED}[CMD] {text}{Colors.RESET}")

def print_response(text: str):
    print(f"{Colors.GREEN}[RES] {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.BLUE}[INF] {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}[WRN] {text}{Colors.RESET}")

def print_sim(text: str):
    print(f"{Colors.CYAN}[SIM] {text}{Colors.RESET}")

# ========================
# Speed + RPM Simulation
# ========================

class VehicleSimulator:
    """Simuliert ein fahrendes Auto mit Speed + RPM."""
    
    def __init__(self):
        self.speed = 0.0          # km/h
        self.rpm = 850.0          # Idle RPM
        self.throttle_virtual = 0.0  # Virtuell 0-100%
        self.gear = 1             # Gang
        self.last_change = time.time()
        self.cycle = 0            # 0=stop, 1=accel, 2=cruise, 3=decel
        
        print_info("Vehicle Simulator initialisiert")
        print_info("  Speed-Simulation: 0 → 120 → 0 km/h (alle ~60s)")
        print_info("  RPM basiert auf Speed + virtuellem Throttle")
    
    def update(self):
        """Aktualisiert Speed + RPM basierend auf Simulations-Zyklus."""
        now = time.time()
        elapsed = now - self.last_change
        
        # Zyklus alle 10 Sekunden ändern
        if elapsed > 10.0:
            self.cycle = (self.cycle + 1) % 4
            self.last_change = now
            
            if self.cycle == 0:
                print_sim("🔄 Zyklus: STOP (0 km/h)")
            elif self.cycle == 1:
                print_sim("🚀 Zyklus: ACCELERATE (0 → 120 km/h)")
            elif self.cycle == 2:
                print_sim("⏸️  Zyklus: CRUISE (120 km/h)")
            elif self.cycle == 3:
                print_sim("🛑 Zyklus: DECELERATE (120 → 0 km/h)")
        
        # Speed berechnen
        if self.cycle == 0:
            # Stop
            self.speed = 0.0
        elif self.cycle == 1:
            # Accelerate: 0 → 120 in 10s = 12 km/h pro Sekunde
            accel_time = min(10.0, now - self.last_change)
            self.speed = (120.0 / 10.0) * accel_time
        elif self.cycle == 2:
            # Cruise: 120 km/h
            self.speed = 120.0
        elif self.cycle == 3:
            # Decelerate: 120 → 0 in 10s
            decel_time = min(10.0, now - self.last_change)
            self.speed = 120.0 - (120.0 / 10.0) * decel_time
        
        # RPM basierend auf Speed + virtuellem Throttle
        if self.speed < 1:
            self.rpm = 850.0 + (self.throttle_virtual * 50)  # Idle + Throttle
        else:
            # RPM = f(Speed, Throttle, Gear)
            base_rpm = 850 + (self.speed * 25)  # 25 RPM pro km/h
            
            if self.cycle == 1:  # Beschleunigen → höhere RPM
                self.rpm = base_rpm + 800
            elif self.cycle == 2:  # Cruise → moderate RPM
                self.rpm = base_rpm + 200
            elif self.cycle == 3:  # Verzögern → niedrigere RPM
                self.rpm = base_rpm - 200
            else:
                self.rpm = base_rpm
            
            # Clamp
            self.rpm = max(800, min(6500, self.rpm))
        
        return self.speed, self.rpm, self.throttle_virtual
    
    def get_rpm_bytes(self) -> tuple:
        """Gibt RPM als zwei Hex-Bytes (für ELM327 Response)."""
        value = int(self.rpm) * 4
        a = (value >> 8) & 0xFF
        b = value & 0xFF
        return a, b
    
    def get_speed_byte(self) -> int:
        """Gibt Speed als ein Hex-Byte."""
        return min(255, int(self.speed))


# ========================
# Debug Command Processor V2
# ========================

class DebugOBD2ProcessorV2:
    """Verarbeitet ELM327-Befehle mit EXTENSIVEM Debug + Vehicle Sim."""
    
    def __init__(self, vehicle_sim: VehicleSimulator):
        self.vehicle_sim = vehicle_sim
        self.echo = False
        self.ready = False
        self.spaces = False
        self.connected_at = datetime.now()
        self.command_count = 0
        
        # Tracking
        self.throttle_requests = []
        self.speed_requests = []
        self.rpm_requests = []
        self.all_commands = []
        
        print_info("Debug-OBD2 Processor V2 initialisiert")
        
        # Throttle-Test: Simuliere Throttle-Änderungen
        self.test_throttle_cycle = 0
    
    def process_command(self, command: str) -> str:
        """Verarbeitet einen Command mit LIVING DEBUG."""
        line = command.strip()
        self.command_count += 1
        
        if not line:
            return ""
        
        normalized = line.replace(" ", "").upper()
        
        print_command(f"#{self.command_count}: {repr(line)} (norm: {repr(normalized)})")
        self.all_commands.append(normalized)
        
        # Vehicle Sim aktualisieren
        speed, rpm, throttle = self.vehicle_sim.update()
        rpm_a, rpm_b = self.vehicle_sim.get_rpm_bytes()
        speed_byte = self.vehicle_sim.get_speed_byte()
        
        response = ""
        
        # --- AT Commands ---
        if normalized == "ATZ":
            response = "ELM327 v2.3\r\nOK\r\n> "
            self.ready = True
            print_info(f"ATZ → Reset")
            
        elif normalized == "ATI":
            response = "Dacia Spring OBD2 Debug V2\r\n> "
            print_info("ATI → Identifikation")
            
        elif normalized in ["ATE0", "ATE1"]:
            self.echo = (normalized == "ATE1")
            response = "OK\r\n> "
            print_info(f"ATE{normalized[-1]} → Echo {'an' if self.echo else 'aus'}")
            
        elif normalized in ["ATH0", "ATH1"]:
            response = "OK\r\n> "
            print_info(f"ATH{normalized[-1]} → Header")
            
        elif normalized in ["ATS0", "ATS1"]:
            self.spaces = (normalized == "ATS1")
            response = "OK\r\n> "
            print_info(f"ATS{normalized[-1]} → Spaces {'an' if self.spaces else 'aus'}")
            
        elif normalized == "ATSP0":
            response = "OK\r\n> "
            print_info("ATSP0 → Protocol auto")
            
        elif normalized == "ATDPN":
            response = "04\r\n> "
            print_info("ATDPN → CAN 11/500")
            
        # --- OBD2 PIDs ---
        elif normalized == "0100":
            response = "41 00 98 18 02 00\r\n> "
            print_info(f"0100 → Supported PIDs: {response.strip()}")
            
        elif normalized == "0104":
            load = min(100, max(0, int(rpm - 400) / 6))
            response = f"41 04 {load:02X}\r\n> "
            print_info(f"0104 → Engine Load: {load}% (berechnet aus RPM)")
            
        elif normalized == "0105":
            temp = 30
            response = f"41 05 {temp + 40:02X}\r\n> "
            print_info(f"0105 → Coolant Temp: {temp}°C")
            
        elif normalized == "010C":
            # RPM — ECHTER Sim-Wert!
            self.rpm_requests.append(time.time())
            response = f"41 0C {rpm_a:02X} {rpm_b:02X}\r\n> "
            print_info(f"010C → RPM: {rpm:.0f} (hex: {rpm_a:02X} {rpm_b:02X}) | Speed: {speed:.0f}")
            
        elif normalized == "010D":
            # Speed — ECHTER Sim-Wert!
            self.speed_requests.append(time.time())
            response = f"41 0D {speed_byte:02X}\r\n> "
            print_info(f"010D → Speed: {speed:.0f} km/h (hex: {speed_byte:02X})")
            
        elif normalized == "010E":
            response = "41 0E 0C\r\n> "
            print_info("010E → Timing Advance")
            
        elif normalized == "0111":
            # Throttle Position
            self.throttle_requests.append(time.time())
            throttle_val = min(100, int(throttle))
            response = f"41 11 {throttle_val:02X}\r\n> "
            print_info(f"0111 → Throttle: {throttle_val}% (Sim: {throttle:.0f})")
            
        elif normalized == "0146":
            # Engine Load (andere PID!)
            self.throttle_requests.append(time.time())
            load = min(100, max(0, int((rpm - 850) / 57)))
            response = f"41 46 {load:02X}\r\n> "
            print_info(f"0146 → Engine Load: {load}% (berechnet)")
            print_info("   ⚠️ RevHeadz fragt Engine Load ab — könnte Throttle sein!")
            
        elif normalized == "0142":
            # Power Output (E-Auto!)
            self.throttle_requests.append(time.time())
            response = f"41 42 32\r\n> "
            print_info(f"0142 → Power Output: 50%")
            print_info("   ⚠️ RevHeadz fragt Power Output ab — E-Auto Throttle!")
            
        elif normalized == "0120":
            response = "41 20 00 00 01 00\r\n> "
            print_info("0120 → Support PIDs 21-40")
            
        else:
            response = "NO DATA\r\n> "
            print_warning(f"Unbekannt: {repr(line)}")
        
        print_response(response.strip())
        
        # Analyse alle 20 Commands
        if self.command_count % 20 == 0:
            self.print_analysis()
        
        return response
    
    def print_analysis(self):
        """Gibt Analyse aus."""
        now = time.time()
        
        recent_throttle = [t for t in self.throttle_requests if now - t < 60]
        recent_speed = [t for t in self.speed_requests if now - t < 60]
        recent_rpm = [t for t in self.rpm_requests if now - t < 60]
        
        print_info("=" * 60)
        print_info("ANALYSE (letzte 60s):")
        print_info(f"  Commands gesamt: {self.command_count}")
        print_info(f"  Throttle-Requests (0111/0146/0142): {len(recent_throttle)}")
        print_info(f"  Speed-Requests (010D): {len(recent_speed)}")
        print_info(f"  RPM-Requests (010C): {len(recent_rpm)}")
        print_info(f"  Unique Commands: {len(set(self.all_commands[-100:]))}")
        
        # Zeige unique Commands
        unique = set(self.all_commands[-100:])
        print_info(f"  Unique Commands: {unique}")
        print_info("=" * 60)


# ========================
# TCP Server Handler
# ========================

class DebugTCPServerHandlerV2:
    """Behandelt TCP-Verbindungen."""
    
    def __init__(self, client_socket: socket.socket, addr: tuple, processor: DebugOBD2ProcessorV2):
        self.socket = client_socket
        self.addr = addr
        self.processor = processor
        self.connect_time = datetime.now()
    
    def handle(self):
        """Verarbeitet TCP-Verbindung."""
        print_info("=" * 60)
        print_info(f"📱 VERBINDUNG: {self.addr}")
        print_info(f"   Zeit: {self.connect_time}")
        print_info("=" * 60)
        
        welcome = "Dacia Spring OBD2 Debug V2\r\nELM327 v2.3\r\nReady\r\n> "
        self.socket.sendall(welcome.encode())
        print_response(f"[WELCOME] {repr(welcome)}")
        
        buffer = ""
        try:
            while True:
                data = self.socket.recv(4096)
                if not data:
                    print_info(f"🔌 VERBINDUNG GE SCHLOSSEN: {self.addr}")
                    break
                
                raw_hex = data.hex()
                raw_text = data.decode('utf-8', errors='replace')
                print_info(f"📨 RAW ({len(data)} bytes): hex={raw_hex} text={repr(raw_text)}")
                
                buffer += raw_text
                
                while '\r' in buffer or '\n' in buffer:
                    if '\r' in buffer:
                        line, buffer = buffer.split('\r', 1)
                    elif '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                    else:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    print_info(f"\n{'='*60}")
                    print_info(f"VERARBEITE: {repr(line)}")
                    print_info(f"{'='*60}\n")
                    
                    response = self.processor.process_command(line)
                    if response:
                        self.socket.sendall(response.encode())
                        
        except Exception as e:
            print_warning(f"TCP Fehler: {e}")
        finally:
            disconnect_time = datetime.now()
            duration = (disconnect_time - self.connect_time).total_seconds()
            print_info(f"\n{'='*60}")
            print_info(f"🔌 GETRENNT: {self.addr}")
            print_info(f"   Dauer: {duration:.1f}s")
            print_info(f"   Commands: {self.processor.command_count}")
            print_info(f"{'='*60}\n")
            self.socket.close()


# ========================
# Hauptserver
# ========================

class DebugElm327ServerV2:
    """Debug ELM327 TCP Server V2."""
    
    def __init__(self, tcp_port: int = TCP_PORT):
        self.tcp_port = tcp_port
        self.vehicle_sim = VehicleSimulator()
        self.processor = DebugOBD2ProcessorV2(self.vehicle_sim)
        self._tcp_server: Optional[socket.socket] = None
    
    def start(self):
        """Startet den Debug-Server."""
        # Vehicle Sim Thread starten
        sim_running = True
        
        def sim_loop():
            while sim_running:
                speed, rpm, throttle = self.vehicle_sim.update()
                print_sim(f"🚗 Speed: {speed:.0f} km/h | RPM: {rpm:.0f} | Throttle: {throttle:.0f}%")
                time.sleep(2)  # Alle 2 Sekunden aktualisieren
        
        sim_thread = threading.Thread(target=sim_loop, daemon=True)
        sim_thread.start()
        
        print_info("=" * 60)
        print_info("DEBUG ELM327 SERVER V2 START")
        print_info(f"  Port: {self.tcp_port}")
        print_info(f"  Host: {HOST}")
        print_info(f"  Log: revheadz_debug_v2.log")
        print_info(f"  Start: {datetime.now()}")
        print_info("=" * 60)
        
        self._tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_server.bind((HOST, self.tcp_port))
        self._tcp_server.listen(5)
        
        print_info(f"✅ Server bereit auf {HOST}:{self.tcp_port}")
        print_info(f"📱 Verbinde Android zu: 192.168.178.197:{self.tcp_port}")
        print_info("⏹️  STRG+C zum Stoppen")
        print_info("=" * 60)
        
        try:
            while True:
                client_sock, addr = self._tcp_server.accept()
                t = threading.Thread(
                    target=DebugTCPServerHandlerV2(client_sock, addr, self.processor).handle,
                    daemon=True
                )
                t.start()
        except KeyboardInterrupt:
            sim_running = False
            print_info("\nServer gestoppt")
        finally:
            if self._tcp_server:
                self._tcp_server.close()


# ========================
# Hauptprogramm
# ========================

if __name__ == "__main__":
    server = DebugElm327ServerV2(tcp_port=TCP_PORT)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer gestoppt")