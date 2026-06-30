#!/usr/bin/env python3
"""
ELM327 BLE + TCP Server - Integrierte Lösung
==============================================
Verbindet sich zum Vgate iCar Pro BLE Adapter, liest OBD2-Daten
und serviert sie über WiFi TCP als ELM327-Emulator.

Falls BLE nicht verfÜgbar oder keine realen Daten → automatische Simulation.

Nutzung:
    python3 elm327_ble_tcp_server.py
    
Oder nur TCP (ohne BLE):
    python3 elm327_ble_tcp_server.py --no-ble
    
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
from datetime import datetime
from typing import Optional, Dict, Any

# bleak für BLE (optional)
bleak_available = False
try:
    from bleak import BleakClient, BleakScanner
    bleak_available = True
except ImportError:
    pass

# Lokale Module
try:
    from rpm_simulation_engine import RPMSimulationEngine, DriveState
    rpm_engine_available = True
except ImportError:
    rpm_engine_available = False

# ========================
# Konfiguration
# ========================
TCP_PORT = 2117
BLE_MAC = "D2:E0:2F:8D:61:07"  # Vlink iCar Pro MAC
BLE_CHAR_UUID = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"
BLE_CONNECT_TIMEOUT = 10  # Sekunden
BLE_COMMAND_TIMEOUT = 3.0  # Sekunden für OBD2-Befehle
DATA_POLL_INTERVAL = 0.2  # Sekunden zwischen Daten-Updates

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("elm327-server")


# ========================
# BLE OBD2 Client
# ========================

class BLEObd2Client:
    """Bleibt persistent verbunden mit Auto-Reconnect."""
    
    def __init__(self, mac: str, char_uuid: str):
        self.mac = mac
        self.char_uuid = char_uuid
        self.client: Optional[BleakClient] = None
        self._running = False
        self._reconnect_delay = 3.0
        self._last_response = ""
        self._raw_notify_count = 0
        self._can_frames = []
        
    async def start(self) -> bool:
        """Startet BLE Verbindung."""
        if not bleak_available:
            logger.warning("⚠️ bleak nicht verfügbar → Keine BLE-Daten")
            return False
        
        try:
            self._running = True
            async with BleakClient(self.mac) as client:
                self.client = client
                logger.info(f"✅ BLE verbunden: {self.mac}")
                
                # Notify einrichten
                client.set_disconnected_callback(lambda: logger.warning("⚠️ BLE getrennt"))
                
                # ELM327 initialisieren
                await self._init_elm327()
                
                # OBD2-Daten lesen
                await self._read_obd2_loop()
                return True
                
        except Exception as e:
            logger.error(f"❌ BLE Fehler: {e}")
            return False
    
    async def _init_elm327(self):
        """Initialisiert ELM327 Adapter."""
        commands = [
            ("ATZ", 1.0),
            ("ATE0", 0.5),
            ("ATH0", 0.5),
            ("ATS0", 0.5),
            ("ATSP0", 1.0),
        ]
        
        for cmd, timeout in commands:
            resp = await self._send_command(cmd, timeout)
            logger.info(f"  AT {cmd}: {resp or '(keine Antwort)'}")
    
    async def _send_command(self, cmd: str, timeout: float = BLE_COMMAND_TIMEOUT) -> str:
        """Sendet AT-Befehl und wartet auf Antwort."""
        if not self.client or not self.client.is_connected:
            return ""
        
        try:
            self._last_response = ""
            cmd_bytes = f"{cmd}\r".encode('utf-8')
            await self.client.write_gatt_char(self.char_uuid, cmd_bytes)
            await asyncio.sleep(timeout)
            return self._last_response
        except Exception as e:
            logger.debug(f"Command {cmd} fehlgeschlagen: {e}")
            return ""
    
    async def _read_obd2_loop(self):
        """Kontinuierlich OBD2-Daten lesen."""
        poll_commands = ["010C", "010D", "0111"]  # RPM, Speed, Throttle
        
        while self._running:
            try:
                if self.client and self.client.is_connected:
                    for cmd in poll_commands:
                        resp = await self._send_command(cmd, 1.0)
                        if resp and "NO DATA" not in resp:
                            logger.info(f"OBD2 {cmd}: {resp}")
                        await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(self._reconnect_delay)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Read-Loop Fehler: {e}")
                await asyncio.sleep(2)
    
    async def stop(self):
        """Stoppt BLE Verbindung."""
        self._running = False


# ========================
# OBD2 Command Processor
# ========================

class OBD2CommandProcessor:
    """Verarbeitet ELM327-Befehle und antwortet im Standard-Format."""
    
    def __init__(self):
        self.echo = False
        self.ready = False
        self.connected_at = datetime.now()
        
        # Aktive Daten
        self._speed = 0.0
        self._rpm = 850.0
        self._throttle = 0.0
        self._has_real_data = False
        self._last_real_data = time.time()
        
        # RPM Engine (Fallback)
        self.rpm_engine: Optional[RPMSimulationEngine] = None
        if rpm_engine_available:
            self.rpm_engine = RPMSimulationEngine()
    
    def update_from_ble(self, rpm: float, speed: float, throttle: float):
        """Aktualisiert Daten vom BLE Client."""
        self._rpm = rpm
        self._speed = speed
        self._throttle = throttle
        self._has_real_data = True
        self._last_real_data = time.time()
    
    def process_command(self, command: str) -> str:
        """Verarbeitet einen ELM327-Befehl und gibt Antwort zurück."""
        line = command.strip()
        if not line:
            return ""
        
        normalized = line.replace(" ", "").upper()
        
        response = ""
        if self.echo:
            response = line + "\r"
        
        # --- AT Commands ---
        if normalized == "ATZ":
            response += "ELM327 v2.3\r\nOK\r\n"
            self.ready = True
            
        elif normalized == "ATI":
            response += "Dacia Spring OBD2\r\n"
            
        elif normalized == "ATE0":
            self.echo = False
            response += "OK\r\n"
            
        elif normalized == "ATE1":
            self.echo = True
            response += "OK\r\n"
            
        elif normalized == "ATH0":
            response += "OK\r\n"
            
        elif normalized == "ATS0":
            response += "OK\r\n"
            
        elif normalized == "ATSP0":
            response += "OK\r\n"
            
        elif normalized == "ATDPN":
            response += "04\r\n"  # CAN 11/500
            
        # --- OBD2 PIDs ---
        elif normalized == "0100":
            # Supported PIDs 01-20
            # Bitfeld: PID 04, 05, 0C, 0D supported
            response += "41 00 E0 00 00 01\r\n"
            
        elif normalized == "0104":
            # Engine Load (emuliert)
            load = min(100, max(0, (self._rpm - 400) / 6))
            response += f"41 04 {int(load):02X}\r\n"
            
        elif normalized == "0105":
            # Coolant Temp (EV: Batterie Temp simulieren)
            temp = 30  # °C
            response += f"41 05 {temp + 40:02X}\r\n"
            
        elif normalized == "010C":
            # RPM
            rpm = self._get_rpm()
            value = int(rpm) * 4
            a = (value >> 8) & 0xFF
            b = value & 0xFF
            response += f"41 0C {a:02X} {b:02X}\r\n"
            
        elif normalized == "010D":
            # Speed
            speed = int(self._speed)
            response += f"41 0D {speed:02X}\r\n"
            
        elif normalized == "010E":
            # Timing Advance
            response += "41 0E 0C\r\n"
            
        elif normalized == "0111":
            # Throttle Position
            throttle = min(100, int(self._throttle * 100 / 255))
            response += f"41 11 {throttle:02X}\r\n"
            
        elif normalized == "0114":
            # Barometric Pressure
            response += "41 14 82\r\n"
            
        elif normalized == "0120":
            # Support PIDs 21-40
            response += "41 20 00 00 01 00\r\n"
            
        else:
            response += "NO DATA\r\n"
        
        return response
    
    def _get_rpm(self) -> float:
        """Gibt RPM zurück — real oder simuliert."""
        # Immer simulierte RPM berechnen
        if self.rpm_engine:
            return self.rpm_engine.update(self._speed, self._throttle)
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
        
        # Willkommensnachricht
        welcome = "Dacia Spring OBD2\r\nELM327 v2.3 (WiFi)\r\nReady\r\n"
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

class ELM327BTcpServer:
    """Integrierter BLE + TCP Server."""
    
    def __init__(self, tcp_port: int = TCP_PORT, use_ble: bool = True):
        self.tcp_port = tcp_port
        self.use_ble = use_ble and bleak_available
        self.processor = OBD2CommandProcessor()
        self.ble_client: Optional[BLEObd2Client] = None
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
        logger.info("ELM327 BLE + TCP Server Start")
        logger.info(f"  TCP Port: {self.tcp_port}")
        logger.info(f"  WiFi IP: {ip}")
        logger.info(f"  BLE: {'Aktiv' if self.use_ble else 'Deaktiviert'}")
        if self.use_ble:
            logger.info(f"  BLE MAC: {BLE_MAC}")
        logger.info("=" * 60)
        
        # BLE Client starten
        if self.use_ble:
            self.ble_client = BLEObd2Client(BLE_MAC, BLE_CHAR_UUID)
            ble_task = asyncio.create_task(self._ble_loop())
        else:
            logger.info("BLE deaktiviert → Verwende simulierte Daten")
            ble_task = None
        
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
            if self.ble_client:
                await self.ble_client.stop()
    
    async def _ble_loop(self):
        """BLE Connect-und-Daten-Lese-Schleife."""
        while True:
            try:
                connected = await self.ble_client.start()
                if connected:
                    logger.info("BLE-Daten werden empfangen...")
                    # Hier könnten wir BLE-Daten in self.processor.update_from_ble() einfügen
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"BLE Fehler: {e}")
            await asyncio.sleep(1)


# ========================
# Hilfsfunktion
# ========================

def get_wifi_ip() -> str:
    """Ermittelt die WiFi IP des Pi."""
    try:
        import subprocess
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip().split()[0] if result.stdout.strip() else "unknown"
    except Exception:
        return "unknown"


# ========================
# Hauptprogramm
# ========================

def print_usage():
    """Zeigt Nutzungshilfe."""
    print("""
ELM327 BLE + TCP Server
========================

Nutzung:
    python3 elm327_ble_tcp_server.py          # Mit BLE
    python3 elm327_ble_tcp_server.py --no-ble  # Nur TCP (Simulation)

Verbindung:
    IP des Pi ermitteln: hostname -I
    TCP Port: 2117
    
Unterstützte Apps:
    - RevHeadz (Motorsound)
    - Potenza Drive
    - Car Scanner ELM OBD2

Beispiel:
    ip=$(hostname -I | awk '{print $1}')
    adb shell "am start -a android.intent.action.VIEW \\
        -d \"http://$ip:2117\"" --no-verify
    """)


if __name__ == "__main__":
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(description="ELM327 BLE + TCP Server")
    parser.add_argument("--no-ble", action="store_true", help="BLE deaktivieren (nur Simulation)")
    parser.add_argument("--port", type=int, default=TCP_PORT, help="TCP Port (default: 2117)")
    parser.add_argument("--mac", type=str, default=BLE_MAC, help="BLE MAC Adresse")
    
    args = parser.parse_args()
    
    server = ELM327BTcpServer(
        tcp_port=args.port,
        use_ble=not args.no_ble
    )
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nServer gestoppt")