#!/usr/bin/env python3
"""
ELM327 WiFi TCP Server - Alternative zu Bluetooth
===================================================
Ein simpler TCP-Server der ELM327 OBD2 Befehle emuliert.
Handy verbindet sich per WiFi TCP zum Pi und sendet ELM327-Befehle.

Vorteile gegenüber Bluetooth:
- Keine Pairing-Probleme
- Zuverlässigere Verbindung
- Funktioniert über WiFi-Range (viel weiter)

Usage:
    python3 elm327_tcp_server.py
"""

import socket
import logging
import random
import threading
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("tcp-server")

TCP_PORT = 2117  # Standard ELM327 TCP Port


class ELM327Engine:
    """ELM327 command processor for OBD2 emulation."""
    
    def __init__(self):
        self.echo = True
        self.idle_rpm = 850
        self.connected_at = datetime.now()

    def process(self, command):
        """Process ELM327 command and return response."""
        line = command.strip()
        if not line:
            return ""
        
        # Normalize: remove spaces and uppercase (ATZ vs "AT Z" vs "at z")
        normalized = line.replace(" ", "").upper()
        
        response = ""
        if self.echo:
            response = line + "\r"
        
        # --- AT Commands ---
        if normalized == "ATZ":
            # Reset - keep response minimal for RevHeadz compatibility
            response += "ELM327 v1.5a\r\nOK\r\n"
            self.idle_rpm = 850
            
        elif normalized == "ATI":
            response += "PiZeroCar-OBD2\r\n"
            
        elif normalized == "ATE0":
            self.echo = False
            response += "OK\r\n"
            
        elif normalized == "ATE1":
            self.echo = True
            response += "OK\r\n"
            
        elif normalized == "ATH0":
            response += "OK\r\n"
            
        elif normalized == "ATH1":
            response += "OK\r\n"
            
        elif normalized == "ATS0":
            response += "OK\r\n"
            
        elif normalized == "ATS1":
            response += "OK\r\n"
            
        elif normalized == "ATSP0":
            response += "OK\r\n"
            
        elif normalized == "ATA":
            response += "PiZeroCar-OBD2\r\n"
            
        # --- OBD2 PID Commands ---
        elif normalized in ("0100",):
            # Supported PIDs
            response += "41 00 E0 00 00 01\r\n"
            
        elif normalized in ("0104",):
            # Engine Load
            load = random.randint(20, 35)
            response += f"41 04 {load:02X}\r\n"
            
        elif normalized in ("0105",):
            # Coolant Temperature
            response += "41 05 82\r\n"
            
        elif normalized in ("010C",):
            # Engine RPM
            rpm = self.idle_rpm + random.randint(-20, 20)
            value = rpm * 4
            a = (value >> 8) & 0xFF
            b = value & 0xFF
            response += f"41 0C {a:02X} {b:02X}\r\n"
            
        elif normalized in ("010D",):
            # Vehicle Speed
            response += "41 0D 00\r\n"
            
        elif normalized in ("010E",):
            # Timing Advance
            response += "41 0E 0C\r\n"
            
        elif normalized in ("0101",):
            # Monitor status
            response += "41 01 4C 02 A0 7B\r\n"
            
        elif normalized in ("0111",):
            # Load (alt)
            rpm = self.idle_rpm + random.randint(-20, 20)
            load = min(100, max(0, (rpm - 400) / 70))
            a = int(load * 255 / 100)
            response += f"41 11 {a:02X}\r\n"
            
        elif normalized in ("0114",):
            # Barometric Pressure
            response += "41 14 82\r\n"
            
        elif normalized in ("0120",):
            # Support PIDs 21-40
            response += "41 20 00 00 01 00\r\n"
            
        else:
            response += "NO DATA\r\n"
        
        return response


class TCPHandler:
    def __init__(self, client_socket, addr):
        self.socket = client_socket
        self.addr = addr
        self.engine = ELM327Engine()

    def handle(self):
        logger.info(f"Connected from {self.addr}")
        try:
            welcome = f"PiZeroCar-OBD2\r\nELM327 v1.5a (WiFi)\r\nReady\r\n"
            self.socket.sendall(welcome.encode())
            
            buffer = ""
            while True:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8', errors='ignore')
                
                # Process all complete commands
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
                    
                    response = self.engine.process(line)
                    if response:
                        self.socket.sendall(response.encode())
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            logger.info(f"Disconnected {self.addr}")
            self.socket.close()


def main():
    logger.info("=" * 50)
    logger.info("ELM327 WiFi TCP Server")
    logger.info("=" * 50)
    logger.info(f"Port: {TCP_PORT}")
    
    # Get Pi's WiFi IP
    try:
        import subprocess
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5)
        ip = result.stdout.strip().split()[0] if result.stdout.strip() else "unknown"
        logger.info(f"WiFi IP: {ip}")
    except Exception:
        logger.info("WiFi IP: check with 'hostname -I'")
    
    logger.info("=" * 50)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", TCP_PORT))
    server.listen(5)
    
    logger.info("WAITING FOR CONNECTIONS...")
    logger.info("Connect from your phone to Pi's WiFi IP")
    logger.info(f"Port: {TCP_PORT}")
    logger.info("")
    logger.info("Recommended OBD2 Apps:")
    logger.info("  - RevHeadz (Motorsound-Simulation)")
    logger.info("  - Potenza Drive")
    logger.info("  - Car Scanner ELM OBD2")
    logger.info("")
    
    try:
        while True:
            client_sock, addr = server.accept()
            logger.info(f"New connection from {addr}")
            t = threading.Thread(target=TCPHandler(client_sock, addr).handle, daemon=True)
            t.start()
    except KeyboardInterrupt:
        logger.info("Server stopped")
    finally:
        server.close()


if __name__ == "__main__":
    main()