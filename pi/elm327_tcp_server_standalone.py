#!/usr/bin/env python3
"""
ELM327 WiFi TCP Server - RevHeadz Kompatibel
================================================
Standalone Version - keine externen Dependencies!
Startet auch ohne bleak/bluez.

Usage:
    python3 elm327_tcp_server_standalone.py
"""

import socket
import logging
import random
import threading
import sys
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

    def process(self, command):
        """Process ELM327 command and return response."""
        line = command.strip()
        if not line:
            return ""
        
        # Normalize: remove spaces and uppercase
        normalized = line.replace(" ", "").upper()
        
        response = ""
        if self.echo:
            response = line + "\r"
        
        # --- AT Commands (alle brauchen "> " Prompt am Ende für RevHeadz) ---
        if normalized == "ATZ":
            response += "ELM327 v1.5a\r\nOK\r\n> "
            self.idle_rpm = 850
            
        elif normalized == "ATI":
            response += "PiZeroCar-OBD2\r\n> "
            
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
            response += "OK\r\n> "
            
        elif normalized == "ATS1":
            response += "OK\r\n> "
            
        elif normalized == "ATSP0":
            response += "OK\r\n> "
            
        elif normalized == "ATA":
            response += "PiZeroCar-OBD2\r\n> "
            
        # --- OBD2 PID Commands ---
        elif normalized == "0100":
            # Supported PIDs: 01, 04, 05, 0C, 0D
            # Byte1 (PIDs 01-08): PID 01=bit7, PID 04=bit4, PID 05=bit3 = 10011000 = 0x98
            # Byte2 (PIDs 09-16): PID 0C=bit3, PID 0D=bit4 = 00011000 = 0x18
            # Byte3 (PIDs 17-24): 0x00
            # Byte4 (PIDs 25-32): 0x00
            response += "41 00 98 18 00 00\r\n> "
            
        elif normalized == "0104":
            load = random.randint(20, 35)
            response += f"41 04 {load:02X}\r\n> "
            
        elif normalized == "0105":
            response += "41 05 82\r\n> "
            
        elif normalized == "010C":
            rpm = self.idle_rpm + random.randint(-20, 20)
            value = rpm * 4
            a = (value >> 8) & 0xFF
            b = value & 0xFF
            response += f"41 0C {a:02X} {b:02X}\r\n> "
            
        elif normalized == "010D":
            response += "41 0D 00\r\n> "
            
        elif normalized == "010E":
            response += "41 0E 0C\r\n> "
            
        elif normalized == "0101":
            response += "41 01 4C 02 A0 7B\r\n> "
            
        elif normalized == "0111":
            rpm = self.idle_rpm + random.randint(-20, 20)
            load = min(100, max(0, (rpm - 400) / 70))
            a = int(load * 255 / 100)
            response += f"41 11 {a:02X}\r\n> "
            
        elif normalized == "0114":
            response += "41 14 82\r\n> "
            
        elif normalized == "0120":
            response += "41 20 00 00 01 00\r\n> "
            
        else:
            # AT AL oder unbekannte Commands - auch Prompt senden
            response += "NO DATA\r\n> "
        
        return response


class TCPHandler:
    def __init__(self, client_socket, addr):
        self.socket = client_socket
        self.addr = addr
        self.engine = ELM327Engine()

    def handle(self):
        logger.info(f"Connected from {self.addr}")
        try:
            # Welcome message - ELM327 style mit Prompt
            # RevHeadz sucht nach "> " als Command Prompt
            welcome = "PiZeroCar-OBD2\r\nELM327 v1.5a (WiFi)\r\nReady\r\n> "
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
                        try:
                            self.socket.sendall(response.encode())
                        except:
                            break
        except Exception as e:
            logger.error(f"Error handling {self.addr}: {e}")
        finally:
            try:
                self.socket.close()
            except:
                pass
            logger.info(f"Disconnected {self.addr}")


def main():
    logger.info("=" * 50)
    logger.info("ELM327 WiFi TCP Server (STANDALONE)")
    logger.info("=" * 50)
    logger.info(f"Port: {TCP_PORT}")
    
    # Get IP
    try:
        import subprocess
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5)
        ip = result.stdout.strip().split()[0] if result.stdout.strip() else "unknown"
        logger.info(f"WiFi IP: {ip}")
    except Exception:
        ip = "localhost"
        logger.info(f"WiFi IP: {ip}")
    
    logger.info("=" * 50)
    logger.info("WAITING FOR CONNECTIONS...")
    logger.info(f"Connect to: {ip}:{TCP_PORT}")
    logger.info("=" * 50)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(("0.0.0.0", TCP_PORT))
    except OSError as e:
        logger.error(f"Cannot bind to port {TCP_PORT}: {e}")
        logger.error("Maybe another ELM327 server is already running!")
        logger.error("Kill it first: pkill -f elm327")
        sys.exit(1)
    
    server.listen(5)
    
    try:
        while True:
            client_sock, addr = server.accept()
            logger.info(f"New connection from {addr}")
            t = threading.Thread(target=TCPHandler(client_sock, addr).handle, daemon=True)
            t.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        server.close()


if __name__ == "__main__":
    main()