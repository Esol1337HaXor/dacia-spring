#!/usr/bin/env python3
"""
Bluetooth SPP Server für ELM327 OBD2 Emulation
===============================================
Emuliert einen Bluetooth OBD2-Adapter über RFCOMM SPP.

Handy verbindet sich per Bluetooth mit dem Pi
und sendet ELM327 AT-Befehle über Serial Port.

Name: "PiZeroCar-OBD2"
Port: 1 (standard SPP)

Verwendet: python3-btsocket / bluez D-Bus API

Usage:
    source ~/obd2-adapter-env/bin/activate
    python bluetooth_spp_server.py
"""

import asyncio
import logging
import random
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("bluetooth-spp")


class ELM327Protocol:
    """ELM327 command processor."""
    
    def __init__(self):
        self.echo = True
        self.ram = random.randint(830, 870)
        
    def process(self, cmd: str) -> str:
        """Process ELM327 command."""
        line = cmd.strip()
        if not line:
            return ""
            
        response = ""
        if self.echo:
            response = line + "\r"
            
        if line == "ATZ":
            response += "ELM327 v1.5a\r\nSerial: OBD2-PI001\r\nHardware: Pi Zero 2W\r\nSoftware: 1.0.1\r\n\r\nReady\r\n"
            self.ram = random.randint(830, 870)
        elif line == "ATI":
            response += "PiZeroCar OBD2\r\n"
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
            response += "PiZeroCar OBD2\r\n"
        elif line in ("0100", "01 00"):
            response += "41 00 E0 00 00 01\r\n"
        elif line in ("0104", "01 04"):
            load = random.randint(20, 35)
            response += f"41 04 {load:02X}\r\n"
        elif line in ("0105", "01 05"):
            response += "41 05 82\r\n"
        elif line in ("010C", "01 0C"):
            rpm = self.ram + random.randint(-15, 15)
            value = rpm * 4
            a = (value >> 8) & 0xFF
            b = value & 0xFF
            response += f"41 0C {a:02X} {b:02X}\r\n"
        elif line in ("010D", "01 0D"):
            response += "41 0D 00\r\n"
        elif line in ("010E", "01 0E"):
            response += "41 0E 0C\r\n"
        elif line in ("0101", "01 01"):
            response += "41 01 4C 02 A0 7B\r\n"
        else:
            response += "NO DATA\r\n"
            
        return response


class SPPConnection:
    """Handle a single Bluetooth SPP connection."""
    
    def __init__(self, writer, addr):
        self.writer = writer
        self.addr = addr
        self.protocol = ELM327Protocol()
        self.buffer = ""
        
    async def send(self, data: str):
        """Send data to client."""
        try:
            self.writer.write(data.encode())
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Send error: {e}")
            
    async def handle(self):
        """Handle the connection loop."""
        logger.info(f"Connected from {self.addr}")
        
        # Welcome message
        await self.send("PiZeroCar-OBD2\r\n\r\nReady\r\n")
        
        try:
            while True:
                data = await self.reader.read(1024)
                if not data:
                    break
                    
                text = data.decode("utf-8", errors="ignore")
                self.buffer += text
                
                # Process complete commands
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
                        
                    response = self.protocol.process(line)
                    await self.send(response)
                    
        except Exception as e:
            logger.error(f"Connection error {self.addr}: {e}")
        finally:
            logger.info(f"Disconnected {self.addr}")
            self.writer.close()


class BlueZSPPServer:
    """
    Bluetooth SPP Server using BlueZ D-Bus API.
    
    Creates a Service Discovery Protocol (SDP) record
    so devices see this as a serial port device.
    """
    
    # SPP UUID
    SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"
    
    def __init__(self, name="PiZeroCar-OBD2", port=1):
        self.name = name
        self.port = port
        self.connections = []
        
    async def start(self):
        """Start the SPP server using BlueZ."""
        logger.info("=" * 50)
        logger.info(f"Bluetooth SPP Server: {self.name}")
        logger.info(f"Port: {self.port}")
        logger.info("=" * 50)
        
        # Try to use bt.socket (Bluetooth sockets)
        await self._start_bt_socket()
        
    async def _start_bt_socket(self):
        """Start using bt.socket for RFCOMM."""
        import bt
        
        try:
            # Create RFCOMM socket
            server_sock = bt.BTSocket(bt.AF_RFCOMM, bt.SOCK_STREAM)
            server_sock.bind(("B8:27:EB:F3:C7:61", self.port))  # Pi's MAC
            server_sock.listen(1)
            
            logger.info(f"Bluetooth SPP listening on port {self.port}")
            logger.info("Make this device discoverable from your phone")
            logger.info("Pair with Bluetooth settings, then connect")
            logger.info(f"Device name: {self.name}")
            logger.info("")
            logger.info("Expected in OBD2 apps:")
            logger.info("  - Device type: Serial Port / SPP")
            logger.info("  - Protocol: ELM327 compatible")
            logger.info("")
            
            while True:
                client_sock, addr = server_sock.accept()
                logger.info(f"New connection from {addr}")
                
                conn = SPPConnection(client_sock, addr)
                self.connections.append(conn)
                
                # Handle in background
                asyncio.create_task(conn.handle())
                
        except ImportError:
            logger.error("bt module not available")
            await self._start_using_btmgmt()
        except Exception as e:
            logger.error(f"bt.socket failed: {e}")
            await self._start_using_btmgmt()
            
    async def _start_using_btmgmt(self):
        """Fallback: Use btmgmt/BlueZ D-Bus API."""
        logger.info("Trying BlueZ D-Bus API...")
        
        try:
            import dbus
            import dbus.service
            import dbus.mainloop.glib
            import gi
            gi.require_version(' GIO', '2.0')
            from gi.repository import GLib
            
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus = dbus.SystemBus()
            
            # Create SDP record
            await self._create_sdp_record(bus)
            
        except ImportError:
            logger.error("dbus and gi not available")
            logger.info("Using fallback: TCP server on port 4000")
            logger.info("Connect via WiFi TCP instead of Bluetooth")
            await self._start_tcp_fallback()
            
    async def _create_sdp_record(self, bus):
        """Create SDP record for SPP service."""
        # SDP record template for RFCOMM
        import struct
        
        # Service classes
        service_class = uuid.UUID("00001101-0000-1000-8000-00805f9b34fb")  # SPP
        
        # Network service
        network = uuid.UUID("00001002-0000-1000-8000-00805f9b34fb")
        
        # Public browsing group
        pub_browse = uuid.UUID("00001002-0000-1000-8000-00805f9b34fb")
        
        # Create record
        record = dbus.Dictionary({
            dbus.UInt16(0x0001): dbus.ByteArray(b"\x00\x01"),  # ServiceClassIDList
            dbus.UInt16(0x0004): dbus.ByteArray(struct.pack("<H", 0x0100)),  # Protocol
            dbus.UInt16(0x0009): dbus.ByteArray(b"\x00\x01"),  # RFCOMM PSM
            dbus.UInt16(0x0005): dbus.ByteArray(b"\x04\x00"),  # RFCOMM port
        })
        
        logger.info("SDP record created")
        
    async def _start_tcp_fallback(self):
        """Fallback TCP server."""
        logger.info("Starting TCP fallback on port 4000...")
        server = await asyncio.start_server(
            self._tcp_handler, '0.0.0.0', 4000
        )
        async with server:
            await server.serve_forever()
            
    async def _tcp_handler(self, reader, writer):
        """TCP handler for fallback."""
        protocol = ELM327Protocol()
        addr = writer.get_extra_info("peername")
        logger.info(f"TCP connection from {addr}")
        
        writer.write("PiZeroCar-OBD2\r\n\r\nReady\r\n".encode())
        await writer.drain()
        
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                line = data.decode().strip()
                response = protocol.process(line)
                writer.write(response.encode())
                await writer.drain()
        except Exception as e:
            logger.error(f"TCP error: {e}")
        finally:
            writer.close()


async def main():
    """Main entry point."""
    server = BlueZSPPServer(name="PiZeroCar-OBD2", port=1)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())