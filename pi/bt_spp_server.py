#!/usr/bin/env python3
"""
Bluetooth SPP Server - ELM327 OBD2 Emulation
==============================================
Bluetooth Serial Port (RFCOMM) Server OHNE SDP (rely on PSCAN).
Handy kann sich per Bluetooth mit dem Pi pairien und ELM327-Befehle senden.

Geräte-Name: "PiZeroCar-OBD2"
RFCOMM Channel: 1
"""

import bluetooth
import socket
import logging
import random
import threading
import subprocess
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("bt-spp")

BD_ADDR = "B8:27:EB:F3:C7:61"
SERVER_PORT = 1


class ELM327Engine:
    def __init__(self):
        self.echo = True
        self.idle_rpm = 850

    def process(self, command):
        line = command.strip()
        if not line:
            return ""
        response = ""
        if self.echo:
            response = line + "\r"
        if line == "ATZ":
            response += "ELM327 v1.5a\r\nSerial: OBD2-PI001\r\nHardware: Pi Zero 2W\r\nSoftware: 2.0.0\r\n\r\nReady\r\n"
            self.idle_rpm = 850
        elif line == "ATI":
            response += "PiZeroCar-OBD2\r\n"
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
            response += "PiZeroCar-OBD2\r\n"
        elif line in ("0100", "01 00"):
            response += "41 00 E0 00 00 01\r\n"
        elif line in ("0104", "01 04"):
            load = random.randint(20, 35)
            response += f"41 04 {load:02X}\r\n"
        elif line in ("0105", "01 05"):
            response += "41 05 82\r\n"
        elif line in ("010C", "01 0C"):
            rpm = self.idle_rpm + random.randint(-20, 20)
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


class BTConnectionHandler:
    def __init__(self, client_sock, addr):
        self.socket = client_sock
        self.addr = addr
        self.engine = ELM327Engine()

    def handle(self):
        logger.info(f"Connected from {self.addr}")
        try:
            self.socket.sendall('PiZeroCar-OBD2\r\n\r\nReady\r\n'.encode())
            while True:
                data = self.socket.recv(1024)
                if not data:
                    break
                text = data.decode('utf-8', errors='ignore')
                lines = text.replace('\r\n', '\r').split('\r')
                for line in lines:
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
    logger.info("Bluetooth SPP ELM327 Server")
    logger.info("=" * 50)
    logger.info(f"RFCOMM Channel: {SERVER_PORT}")
    logger.info(f"MAC: {BD_ADDR}")
    logger.info("=" * 50)
    
    server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((BD_ADDR, SERVER_PORT))
    except OSError as e:
        logger.error(f"Port already in use: {e}")
        return
        
    server_socket.listen(1)
    server_socket.settimeout(1.0)
    
    # Set device name and scan modes
    try:
        subprocess.run(["sudo", "hciconfig", "hci0", "name", "PiZeroCar-OBD2"], capture_output=True, timeout=5)
        subprocess.run(["sudo", "hciconfig", "hci0", "piscan"], capture_output=True, timeout=5)
        logger.info("Device name + PSCAN set")
    except Exception as e:
        logger.warning(f"hciconfig failed: {e}")
    
    logger.info("")
    logger.info("WAITING FOR CONNECTIONS...")
    logger.info("On your phone: search for 'PiZeroCar-OBD2' or 'PiZeroCar'")
    logger.info("PIN: 1234 or 0000")
    logger.info("Connect as 'Serial Port'")
    
    try:
        while True:
            try:
                client_sock, addr = server_socket.accept()
                logger.info(f"New connection from {addr}")
                t = threading.Thread(target=BTConnectionHandler(client_sock, addr).handle, daemon=True)
                t.start()
            except bluetooth.BluetoothError as e:
                logger.error(f"Bluetooth error: {e}")
            except OSError:
                pass
    except KeyboardInterrupt:
        logger.info("Server stopped")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()