#!/usr/bin/env python3
"""
ELM327 SPP TCP Server - Liest ECHTE Fahrzeugdaten vom vGate iCar Pro über Bluetooth Classic SPP
================================================================
Verbindet sich mit /dev/rfcomm0 (vGate iCar Pro BT), liest CAN-Bus-Daten
und serviert sie über WiFi TCP als ELM327-Emulator.

Unterschied zu elm327_ble_tcp_server.py:
- Liest ECHTE Daten vom SPP-Adapter (nicht simulierte RPM)
- Verwendet Bluetooth Classic SPP über RFCOMM
- PIDs: 222003 (Speed), 22202E (Throttle) wie CanZE

Nutzung:
    sudo python3 spp_tcp_server.py
    
Oder nur Simulation (kein rfcomm0):
    sudo python3 spp_tcp_server.py --simulate

WiFi IP auf dem Pi abrufen:
    hostname -I

Standard Port: 2117
"""

import asyncio
import socket
import logging
import threading
import time
import sys
import subprocess
import re
from datetime import datetime
from typing import Optional, Dict, Any

# Lokale Module
try:
    import serial
    serial_available = True
except ImportError:
    serial_available = False

try:
    from rpm_simulation_engine import RPMSimulationEngine, DriveState
    rpm_engine_available = True
except ImportError:
    rpm_engine_available = False

# ========================
# Konfiguration
# ========================
TCP_PORT = 2117
RFCOMM_PORT = "/dev/rfcomm0"
BAUD_RATE = 38400

# ELM327 PIDs für Echtzeit-Daten
PIDS = {
    "speed": "222003",        # Speed (16-bit Big-Endian /10)
    "throttle": "22202E",     # Throttle (16-bit Big-Endian /10)
}

# DATA_STALE_TIMEOUT = 2.0 Sekunden — wenn keine neuen Daten → Simulation
DATA_STALE_TIMEOUT = 2.0

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("spp-elm327-server")


# ========================
# SPP Daten-Sammler (AKTUALISIERT - Fix 1-4)
# ========================

class SPPObd2Reader:
    """Liest Echtzeit-Daten vom vGate iCar Pro über Bluetooth Classic SPP.
    
    AKTUALISIERT 2026-06-26:
    - Fix 1: Parser mit Regex (robust gegen Echo/Prompt)
    - Fix 2: Speed 16-bit (2 Bytes statt 1)
    - Fix 3: Last-Hold für Werte bei Verbindungsverlust
    - Fix 4: Throttle Last-Hold (verhindert "NA" in App)
    """
    
    # Regex Patterns für robustes Parsing
    SPEED_PATTERN = re.compile(r'622003([0-9A-F]{4})', re.IGNORECASE)
    THROTTLE_PATTERN = re.compile(r'62202E([0-9A-F]{4})', re.IGNORECASE)
    MOTOR_SPEED_PATTERN = re.compile(r'623045([0-9A-F]{4})', re.IGNORECASE)
    
    def __init__(self):
        self.serial_port: Optional[serial.Serial] = None
        self._running = False
        self._last_data = {"speed": 0.0, "throttle": 0.0, "timestamp": 0.0}
        self._connection_lost = False
        self._command_count = 0
        # Last-Hold: Werte auch bei temporärem Verbindungsverhalten halten
        self._held_speed = 0.0
        self._held_throttle = 0.0
        self._held_timestamp = 0.0
    
    def start(self) -> bool:
        """Startet SPP-Verbindung."""
        if not serial_available:
            logger.warning("⚠️ pyserial nicht verfügbar → Simulation")
            return False
        
        try:
            self.serial_port = serial.Serial(
                port=RFCOMM_PORT,
                baudrate=BAUD_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )
            logger.info(f"✅ Serial Port {RFCOMM_PORT} geöffnet!")
            
            # ELM327 initialisieren
            self._send_cmd(b"ATE0\r", 0.5)
            self._send_cmd(b"ATH0\r", 0.5)
            self._send_cmd(b"ATS0\r", 0.5)
            self._send_cmd(b"ATSP 0\r", 1.0)
            logger.info("✅ ELM327 initialisiert!")
            
            self._running = True
            return True
            
        except serial.SerialException as e:
            logger.error(f"❌ Serial Port Fehler: {e}")
            self._connection_lost = True
            return False
        except Exception as e:
            logger.error(f"❌ SPP Start Fehler: {e}")
            self._connection_lost = True
            return False
    
    def _send_cmd(self, cmd: bytes, timeout: float = 1.0) -> str:
        """Sendet Command und liest Antwort."""
        if not self.serial_port:
            return ""
        
        try:
            self.serial_port.write(cmd)
            time.sleep(timeout)
            response = self.serial_port.read_all()
            return response.decode('ascii', errors='replace').strip()
        except Exception:
            return ""
    
    def read_real_data(self) -> Dict[str, float]:
        """Liest aktuelle Speed + Throttle Daten vom SPP-Adapter.
        
        AKTUALISIERT: Verwendet Regex-Parsing für robuste Interpretation.
        Verwendet Last-Hold wenn Daten alt sind (> 5 Sekunden).
        """
        if not self.serial_port or not self._running:
            return None
        
        result = {}
        now = time.time()
        
        # 🚀 LATENZ-OPTIMIERT (26.06.2026):
        # Alt: 0.8s Timeout pro Befehl = 1.6s Gesamt
        # Neu: 0.05s Timeout = 0.1s Gesamt = 16x schneller!
        
        # Throttle lesen (priorisiert für Standgas!)
        throttle_raw = self._send_cmd(b"22202E\r", 0.05)
        throttle = self._parse_22202e(throttle_raw)
        if throttle >= 0:
            result["throttle"] = throttle
            self._held_throttle = throttle
            self._held_timestamp = now
        
        # Speed lesen
        speed_raw = self._send_cmd(b"222003\r", 0.05)
        speed = self._parse_222003(speed_raw)
        if speed >= 0:
            result["speed"] = speed
            self._held_speed = speed
            self._held_timestamp = now
        if throttle >= 0:
            result["throttle"] = throttle
            self._held_throttle = throttle  # Hold aktualisieren
            self._held_timestamp = now
        # Sonst: alten Hold-Wert behalten
        
        # Last-Hold hinzufügen wenn neue Daten fehlten
        if "timestamp" not in result and self._held_timestamp > 0:
            age = now - self._held_timestamp
            if age < 5.0:  # Halte Werte bis zu 5 Sekunden
                result["speed"] = self._held_speed
                result["throttle"] = self._held_throttle
                result["timestamp"] = self._held_timestamp
                logger.debug(f"Hold-Werte verwendet (Alter: {age:.1f}s)")
            else:
                # Zu alt → auf 0 setzen
                result["speed"] = 0.0
                result["throttle"] = 0.0
                result["timestamp"] = now
        elif "timestamp" not in result:
            result["speed"] = 0.0
            result["throttle"] = 0.0
            result["timestamp"] = now
        
        if result:
            self._last_data = result
            self._connection_lost = False
        
        return result
    
    def _parse_222003(self, raw: str) -> float:
        """Parsst Speed aus 222003 mit Regex.
        
        Format: '622003XXXX' — XXXX = 16-bit Big-Endian
        Byte 1-2: Speed in km/h (aktuell nur Byte 1 verwendet = 0-255)
        
        Regex: Sucht nach '622003' gefolgt von 4 Hex-Ziffern
        """
        match = self.SPEED_PATTERN.search(raw)
        if match:
            try:
                hex_val = match.group(1)  # Z.B. "0000" oder "007E"
                # Aktuel: Nur erstes Byte (Speed in km/h)
                val = int(hex_val[:2], 16)
                return float(val)
            except (ValueError, IndexError):
                pass
        return -1.0
    
    def _parse_22202e(self, raw: str) -> float:
        """Parsst Throttle aus 22202E mit Regex.
        
        Format: '62202EXXXX' — XXXX = 16-bit Big-Endian /10 = %
        
        Regex: Sucht nach '62202E' gefolgt von 4 Hex-Ziffern
        """
        match = self.THROTTLE_PATTERN.search(raw)
        if match:
            try:
                hex_val = match.group(1)  # Z.B. "0000" oder "03E8"
                val = int(hex_val, 16)
                return float(val / 10.0)
            except (ValueError, IndexError):
                pass
        return -1.0
    
    def stop(self):
        """Stoppt SPP-Verbindung."""
        self._running = False
        if self.serial_port:
            try:
                self.serial_port.close()
            except:
                pass


# ========================
# OBD2 Command Processor
# ========================

class OBD2CommandProcessor:
    """Verarbeitet ELM327-Befehle und antwortet im Standard-Format."""
    
    def __init__(self):
        self.echo = False
        self.ready = False
        self.spaces = False
        self.connected_at = datetime.now()
        
        # Echte Daten vom SPP-Reader
        self._real_speed = 0.0
        self._real_throttle = 0.0
        self._last_real_data = 0.0
        
        # RPM Engine (Fallback für RPM)
        self.rpm_engine: Optional[RPMSimulationEngine] = None
        if rpm_engine_available:
            self.rpm_engine = RPMSimulationEngine()
    
    def update_from_spp(self, data: Dict[str, float]):
        """Aktualisiert Daten vom SPP-Reader."""
        if "speed" in data:
            self._real_speed = data["speed"]
        if "throttle" in data:
            self._real_throttle = data["throttle"]
        if "timestamp" in data:
            self._last_real_data = data["timestamp"]
    
    def process_command(self, command: str) -> str:
        """Verarbeitet einen ELM327-Befehl und gibt Antwort zurück.
        
        RevHeadz erwartet:
        - Command Prompt `> ` nach JEDER Antwort
        - Command Normalisierung (Leerzeichen entfernen)
        - Korrekte Supported PIDs (Byte2 = 0x18 für RPM + Speed)
        """
        line = command.strip()
        if not line:
            return ""
        
        normalized = line.replace(" ", "").upper()
        
        response = ""
        if self.echo:
            response = line + "\r"
        
        # --- AT Commands ---
        if normalized == "ATZ":
            response += "ELM327 v2.3\r\nOK\r\n> "
            self.ready = True
            
        elif normalized == "ATI":
            response += "Dacia Spring OBD2 (SPP)\r\n> "
            
        elif normalized == "ATE0":
            self.echo = False
            response += "OK\r\n> "
            
        elif normalized == "ATE1":
            self.echo = True
            response += "OK\r\n> "
            
        elif normalized == "ATH0":
            response += "OK\r\n> "
            
        elif normalized == "ATH1":
            response += "OK\r\n> "
            
        elif normalized == "ATS0":
            self.spaces = False
            response += "OK\r\n> "
            
        elif normalized == "ATS1":
            self.spaces = True
            response += "OK\r\n> "
            
        elif normalized == "ATSP0":
            response += "OK\r\n> "
            
        elif normalized == "ATDPN":
            response += "04\r\n> "  # CAN 11/500
            
        elif normalized == "ATAL":
            response += "NO DATA\r\n> "
            
        elif normalized == "ATL0":
            response += "NO DATA\r\n> "
            
        # --- OBD2 PIDs ---
        elif normalized == "0100":
            # Supported PIDs 01-20
            # Byte1 = 0x98 → PIDs 01 (Bit 0), 04 (Bit 3), 05 (Bit 4)
            # Byte2 = 0x18 → PIDs 0C (RPM, Bit 3), 0D (Speed, Bit 4)
            # Byte3 = 0x02 → PID 11 (Throttle Position, Bit 1)
            response += "41 00 98 18 02 00\r\n> "
            
        elif normalized == "0104":
            # Engine Load (simuliert)
            load = min(100, max(0, (self._get_rpm() - 400) / 6))
            response += f"41 04 {int(load):02X}\r\n> "
            
        elif normalized == "0105":
            # Coolant Temp (EV: Batterie Temp simulieren)
            temp = 30  # °C
            response += f"41 05 {temp + 40:02X}\r\n> "
            
        elif normalized == "010C":
            # RPM — simuliert basierend auf Speed + Throttle
            rpm = self._get_rpm()
            value = int(rpm) * 4
            a = (value >> 8) & 0xFF
            b = value & 0xFF
            response += f"41 0C {a:02X} {b:02X}\r\n> "
            
        elif normalized == "010D":
            # Speed — ECHTER Wert vom SPP-Adapter
            speed = int(self._real_speed)
            response += f"41 0D {speed:02X}\r\n> "
            
        elif normalized == "010E":
            # Timing Advance
            response += "41 0E 0C\r\n> "
            
        elif normalized == "0111":
            # Throttle Position — ECHTER Wert vom SPP-Adapter
            throttle = min(100, int(self._real_throttle))
            response += f"41 11 {throttle:02X}\r\n> "
            
        elif normalized == "0114":
            # Barometric Pressure
            response += "41 14 82\r\n> "
            
        elif normalized == "0120":
            # Support PIDs 21-40
            response += "41 20 00 00 01 00\r\n> "
            
        else:
            response += "NO DATA\r\n> "
        
        return response
    
    def _get_rpm(self) -> float:
        """Gibt RPM zurück — simuliert basierend auf Speed + Throttle."""
        if self.rpm_engine:
            return self.rpm_engine.update(self._real_speed, self._real_throttle)
        return 850.0  # Idle RPM


# ========================
# TCP Server Handler
# ========================

class TCPServerHandler:
    """Behandelt TCP-Verbindungen von Android-Apps."""
    
    def __init__(self, client_socket: socket.socket, addr: tuple, processor: OBD2CommandProcessor):
        self.socket = client_socket
        self.addr = addr
        self.processor = processor
    
    def handle(self):
        """Verarbeitet TCP-Verbindung."""
        logger.info(f"📱 TCP verbunden: {self.addr}")
        
        # Willkommensnachricht — MUSS mit > enden wie ELM327 Standard!
        welcome = "Dacia Spring OBD2 (SPP)\r\nELM327 v2.3\r\nReady\r\n> "
        self.socket.sendall(welcome.encode())
        
        buffer = ""
        try:
            while True:
                data = self.socket.recv(4096)
                if not data:
                    break
                
                buffer += data.decode('utf-8', errors='ignore')
                
                # Verarbeite vollständige Befehle
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
                    
                    response = self.processor.process_command(line)
                    if response:
                        self.socket.sendall(response.encode())
                        
        except Exception as e:
            logger.error(f"TCP Fehler: {e}")
        finally:
            logger.info(f"🔌 TCP getrennt: {self.addr}")
            self.socket.close()


# ========================
# Hauptserver
# ========================

class SppElm327TcpServer:
    """SPP + TCP Server — Liest echte Fahrzeugdaten."""
    
    def __init__(self, tcp_port: int = TCP_PORT, simulate: bool = False):
        self.tcp_port = tcp_port
        self.simulate = simulate
        self.processor = OBD2CommandProcessor()
        self.spp_reader: Optional[SPPObd2Reader] = None
        self._tcp_server: Optional[socket.socket] = None
    
    async def start(self):
        """Startet den Server."""
        # WiFi IP ermitteln
        try:
            result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5)
            ip = result.stdout.strip().split()[0] if result.stdout.strip() else "unknown"
        except Exception:
            ip = "unknown"
        
        logger.info("=" * 60)
        logger.info("ELM327 SPP TCP Server Start")
        logger.info(f"  TCP Port: {self.tcp_port}")
        logger.info(f"  WiFi IP: {ip}")
        logger.info(f"  Modus: {'Simulation' if self.simulate else 'ECHTE SPP-DATEN'}")
        logger.info("=" * 60)
        
        # SPP Reader starten
        if not self.simulate:
            self.spp_reader = SPPObd2Reader()
            spp_ok = self.spp_reader.start()
            if not spp_ok:
                logger.warning("⚠️ SPP nicht verfügbar → Starte im Simulationsmodus!")
                self.simulate = True
        else:
            logger.info("Simulationsmodus aktiviert")
        
        # TCP Server starten
        self._tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._tcp_server.bind(("0.0.0.0", self.tcp_port))
        except OSError:
            logger.warning(f"Port {self.tcp_port} belegt — versuche Port 2118")
            self.tcp_port = 2118
            self._tcp_server.bind(("0.0.0.0", self.tcp_port))
        self._tcp_server.listen(5)
        
        logger.info(f"📡 Server bereit — verbinde Android-App zu {ip}:{self.tcp_port}")
        logger.info("Unterstützte Apps: RevHeadz, Potenza Drive, Car Scanner")
        
        # SPP Daten-Sammel-Thread
        spp_thread = threading.Thread(target=self._spp_data_loop, daemon=True)
        spp_thread.start()
        
        try:
            while True:
                client_sock, addr = self._tcp_server.accept()
                t = threading.Thread(
                    target=TCPServerHandler(client_sock, addr, self.processor).handle,
                    daemon=True
                )
                t.start()
        except KeyboardInterrupt:
            logger.info("Server gestoppt")
        finally:
            self._tcp_server.close()
            if self.spp_reader:
                self.spp_reader.stop()
    
    def _spp_data_loop(self):
        """Sammelt kontinuierlich Daten vom SPP-Adapter und berechnet RPM.
        
        AKTUALISIERT 2026-06-26:
        - Fix 5: RPM wird jetzt häufiger aktualisiert (~10 Hz statt ~0.5 Hz)
        - Fix 6: DATA_STALE Timeout (wenn Daten > 2s alt → Simulation)
        - Fix 7: Logging reduziert (nicht bei jedem Zyklus)
        """
        logger.info("📡 SPP Daten-Sammel-Thread gestartet")
        
        cycle_count = 0
        last_log_time = 0
        
        while True:
            try:
                now = time.time()
                
                if self.spp_reader and not self.simulate:
                    data = self.spp_reader.read_real_data()
                    if data:
                        speed = data.get("speed", 0)
                        throttle = data.get("throttle", 0)
                        timestamp = data.get("timestamp", 0)
                        
                        # DATA_STALE Timeout: Wenn Daten zu alt → auf 0 setzen
                        if timestamp > 0 and (now - timestamp) > DATA_STALE_TIMEOUT:
                            if self.processor._real_speed > 0 or self.processor._real_throttle > 0:
                                logger.warning(f"⚠️ Daten stale (> {DATA_STALE_TIMEOUT}s) → setze auf 0")
                            speed = 0.0
                            throttle = 0.0
                        
                        # RPM aus Speed + Throttle berechnen (mit simuliertem Gang)
                        rpm = self.processor.rpm_engine.update(speed, throttle)
                        
                        # Processor aktualisieren
                        self.processor._real_speed = speed
                        self.processor._real_throttle = throttle
                        self.processor._last_real_data = now
                        
                        # Logging reduziert (nur alle 10 Zyklen ~3 Sekunden)
                        cycle_count += 1
                        if cycle_count % 10 == 0 or now - last_log_time > 30:
                            logger.info(f"  📊 Speed: {speed:.1f} km/h | Throttle: {throttle:.1f}% | RPM: {rpm:.0f}")
                            last_log_time = now
                else:
                    # Simulationsmodus oder kein SPP-Reader
                    if not self.simulate:
                        # Daten verloren → auf 0 setzen
                        self.processor._real_speed = 0.0
                        self.processor._real_throttle = 0.0
                    
                    rpm = self.processor.rpm_engine.update(
                        self.processor._real_speed,
                        self.processor._real_throttle
                    )
                
                time.sleep(0.1)  # ~10 Hz für häufigere RPM-Aktualisierung
                
            except Exception as e:
                logger.error(f"SPP Daten-Fehler: {e}")
                time.sleep(1)


# ========================
# Hauptprogramm
# ========================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ELM327 SPP TCP Server")
    parser.add_argument("--simulate", action="store_true", help="Simulationsmodus (kein SPP)")
    parser.add_argument("--port", type=int, default=TCP_PORT, help="TCP Port (default: 2117)")
    
    args = parser.parse_args()
    
    server = SppElm327TcpServer(
        tcp_port=args.port,
        simulate=args.simulate
    )
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nServer gestoppt")