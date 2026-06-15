#!/usr/bin/env python3
"""
Simple ELM327 TCP Server - works reliably on Pi Zero
"""

import asyncio
import logging
import random
from datetime import datetime

PORT = 4000
IDLE_RPM = 850

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("elm327")


class ELM327Handler(asyncio.Protocol):
    def __init__(self):
        self.buffer = ""
        self.echo = True
        self.ram = random.randint(830, 870)  # Pre-set idle RPM
        
    def connection_made(self):
        logger.info("Client connected")
        welcome = "ELM327 v1.5a\r\niCar Pro BLE\r\n\r\nReady\r\n"
        self.transport.write(welcome.encode())
        
    def data_received(self, data):
        text = data.decode("utf-8", errors="ignore")
        self.buffer += text
        
        # Process all complete commands
        while "\r" in self.buffer or "\n" in self.buffer:
            if "\r" in self.buffer:
                line, self.buffer = self.buffer.split("\r", 1)
            elif "\n" in self.buffer:
                line, self.buffer = self.buffer.split("\n", 1)
            else:
                break
                
            line = line.strip()
            if not line:
                continue
                
            response = ""
            
            # Echo command if enabled
            if self.echo:
                response = line + "\r"
            
            # AT commands
            if line == "ATZ":
                response += "ELM327 v1.5a\r\nSerial: OBD2-PI001\r\nHardware: Pi Zero 2W\r\nSoftware: 1.0.1\r\n\r\nReady\r\n"
                self.ram = random.randint(830, 870)  # Reset RPM on reset
                
            elif line == "ATI":
                response += "iCar Pro BLE\r\n"
                
            elif line == "ATE0":
                self.echo = False
                response += "OK\r\n"
                
            elif line == "ATE1":
                self.echo = True
                response += "OK\r\n"
                
            elif line == "ATH0":
                response += "OK\r\n"
                
            elif line == "ATH1":
                response += "OK\r\n"
                
            elif line == "ATS0":
                response += "OK\r\n"
                
            elif line == "ATS1":
                response += "OK\r\n"
                
            elif line == "ATSP0":
                response += "OK\r\n"
                
            elif line == "ATA":
                response += "ELM327 v1.5a\r\n"
                
            # OBD2 PIDs
            elif line in ("0100", "01 00"):
                # Supported PIDs: 00, 01, 04, 05, 0C, 0D, 0E
                response += "41 00 E0 00 00 01\r\n"
                
            elif line in ("0104", "01 04"):
                load = random.randint(20, 35)
                response += f"41 04 {load:02X}\r\n"
                
            elif line in ("0105", "01 05"):
                response += "41 05 82\r\n"  # 90°C
                
            elif line in ("010C", "01 0C"):
                # RPM = (A*256 + B) / 4
                rpm = self.ram + random.randint(-15, 15)
                value = rpm * 4
                a = (value >> 8) & 0xFF
                b = value & 0xFF
                response += f"41 0C {a:02X} {b:02X}\r\n"
                
            elif line in ("010D", "01 0D"):
                response += "41 0D 00\r\n"  # Speed = 0
                
            elif line in ("010E", "01 0E"):
                response += "41 0E 0C\r\n"  # Throttle ~12%
                
            elif line in ("0101", "01 01"):
                response += "41 01 4C 02 A0 7B\r\n"  # Status
                
            else:
                response += "NO DATA\r\n"
            
            try:
                self.transport.write(response.encode())
            except Exception as e:
                logger.error(f"Send error: {e}")
                
    def connection_lost(self, exc):
        logger.info("Client disconnected")


async def main():
    logger.info(f"ELM327 Simple TCP Server starting on port {PORT}")
    logger.info("Testing: telnet 192.168.178.87 4000")
    
    server = await asyncio.start_server(
        ELM327Handler, '0.0.0.0', PORT
    )
    
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())