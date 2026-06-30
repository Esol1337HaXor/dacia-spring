#!/usr/bin/env python3
"""
BLE GATT Client für vGate iCar Pro auf Raspberry Pi.

Verbindet sich per BLE GATT mit dem IOS-Vlink Adapter
und liest CAN-Daten aus — basierend auf CanZE Protocol.

WICHTIG: IOS-Vlink sendet ECHOES zurück — Parsing muss das berücksichtigen!

BLE UUIDs:
- Service:  e7810a71-73ae-499d-8c15-faa9aef0c3f2
- Char:     bef8d6c9-9c21-4c9e-b632-bd58c1009f9f

MUSS ALS ROOT AUSGEFÜHRT WERDEN!
  sudo python3 ble_client_vgate_root.py
"""
import asyncio
import sys
import logging
from datetime import datetime

import os
if os.geteuid() != 0:
    print("=" * 60)
    print("FEHLER: Dieser Script MUSS als root ausgeführt werden!")
    print("=" * 60)
    print("\nBefehl zum Ausführen:")
    print("  sudo python3 ble_client_vgate_root.py")
    print("\n" + "=" * 60)
    sys.exit(1)

from bleak import BleakScanner, BleakClient

# ============ KONFIGURATION ============
VGLITE_MAC = "D2:E0:2F:8D:61:07"  # <-- MAC anpassen!
VGLITE_SERVICE = "e7810a71-73ae-499d-8c15-faa9aef0c3f2"
VGLITE_CHAR = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"

# ============ LOGGER ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("vGate-BLE-GATT")


class OBD2Data:
    """Hält alle aktuellen OBD2-Daten."""
    def __init__(self):
        self.speed = 0.0
        self.rpm = 0.0
        self.throttle = 0.0
        self.battery_soc = 0.0
        self.raw_response = ""
        self.timestamp = datetime.now()

    def __str__(self):
        return (f"Speed={self.speed:.1f} km/h | Throttle={self.throttle:.1f}% | "
                f"RPM={self.rpm:.0f} | SOC={self.battery_soc:.1f}%")


class VGateBLEClient:
    """
    BLE GATT Client für IOS-Vlink / vGate iCar Pro.
    
    Verwendet BLE GATT Notify für ELM327-Kommunikation.
    WICHTIG: IOS-Vlink sendet ECHOES — Responses müssen gefiltert werden!
    """
    
    def __init__(self, mac: str = VGLITE_MAC, debug: bool = False):
        self.mac = mac.upper()
        self.debug = debug
        self.obd_data = OBD2Data()
        
        self.client = None
        self.running = False
        self.buffer = bytearray()
    
    async def connect(self) -> bool:
        """Verbindet sich per BLE GATT mit dem IOS-Vlink."""
        try:
            logger.info(f"Scanne nach BLE-Geräten in der Nähe...")
            logger.info(f"Suche IOS-Vlink bei {self.mac}...")
            
            # Scanner starten um Gerät zu finden
            devices = await BleakScanner.discover(timeout=5.0)
            found = False
            for d in devices:
                if self.mac in d.address or (d.name and "vgate" in d.name.lower()):
                    logger.info(f"✅ Gefunden: {d.address} - {d.name}")
                    found = True
                    break
                elif d.name and "IOS" in d.name:
                    logger.info(f"✅ Gefunden IOS-Vlink: {d.address} - {d.name}")
                    self.mac = d.address
                    found = True
                    break
            
            if not found:
                logger.warning("⚠️  IOS-Vlink NICHT gefunden — versuche trotzdem zu verbinden")
            
            logger.info(f"Verbinde per BLE GATT zu {self.mac}...")
            
            self.client = BleakClient(self.mac, timeout=10.0)
            await self.client.connect()
            
            logger.info(f"✅ BLE GATT verbunden!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ BLE Verbindung fehlgeschlagen: {e}")
            return False
    
    async def notification_handler(self, sender, data: bytearray):
        """Notify-Callback für ELM327-Antworten.
        
        IOS-Vlink sendet ECHOES — der Buffer sammelt alle Notify-Daten
        und filtert Echoes heraus.
        """
        self.buffer.extend(data)
        
        # Buffer als String darstellen
        content = self.buffer.decode('ascii', errors='ignore')
        
        if self.debug and len(content) > 50:
            logger.debug(f"Buffer Inhalt: {repr(content[-100:])}")
    
    async def send_command(self, cmd: str, timeout: float = 3.0) -> str:
        """Sendet einen ELM327-Befehl via BLE GATT Notify.
        
        IOS-Vlink sendet ECHOES zurück — der Buffer muss gefiltert werden.
        Echte Antworten beginnen mit:
        - OK, NO DATA, SEARCHING...
        - 41XX (OBD2-Response)
        - ELM327 v...
        - 6XXX (Extended Response)
        """
        if not self.client or not self.client.is_connected:
            raise ConnectionError("BLE nicht verbunden")
        
        # Buffer zurücksetzen
        self.buffer = bytearray()
        
        # Notify registrieren
        await self.client.start_notify(VGLITE_CHAR, self.notification_handler)
        
        # Befehl senden (mit \r)
        data = f"{cmd}\r".encode()
        await self.client.write_gatt_char(VGLITE_CHAR, data)
        
        # Antwort lesen (Notify kommt asynchron)
        await asyncio.sleep(timeout)
        
        # Buffer analysieren und Echoes filtern
        raw_content = self.buffer.decode('ascii', errors='ignore')
        
        # Antwort extrahieren — Echoes entfernen
        response = self._extract_response(raw_content, cmd)
        
        return response
    
    def _extract_response(self, raw: str, cmd: str) -> str:
        """Extrahiert echte Antwort aus rohem Notify-Buffer.
        
        Entfernt:
        - Command-Echo (das gesendete Command)
        - 'STOPPED\r\r>' Prompt
        - 'SEARCHING...' Status
        
        Gibt zurück:
        - Echte OBD2-Antwort (41XX...)
        - OK, NO DATA, MODE $1 FAIL
        - ELM327 v...
        """
        # Remove command echo
        cmd_echo = cmd + "\r"
        cmd_space = cmd.replace(" ", "") + "\r"
        
        content = raw
        
        # Entferne SEARCHING... Status
        content = content.replace("SEARCHING...", "")
        
        # Entferne alle Command Echoes
        content = content.replace(cmd_echo, "")
        content = content.replace(cmd_space, "")
        content = content.replace(cmd, "")
        
        # Entferne 'STOPPED\r\r>' wenn am Anfang
        while content.startswith("STOPPED\r\r>"):
            content = content[len("STOPPED\r\r>"):]
        
        # Entferne Prompt-Zeichen am Ende
        content = content.rstrip(">\r\n")
        
        # Clean up multiple newlines
        import re
        content = re.sub(r'\r\n\r\n+', '\r\n', content)
        content = re.sub(r'\r+\r+', '\r', content)
        
        return content.strip()
    
    async def setup_elm327(self):
        """Initialisiert ELM327 mit richtigen Einstellungen."""
        logger.info("\n" + "=" * 60)
        logger.info("ELM327 Initialisierung")
        logger.info("=" * 60)
        
        setup_cmds = [
            ("ATE0", "Echo aus"),
            ("ATH0", "Header aus"),
            ("ATS0", "Spaces aus"),
            ("ATC0", "Checksum aus"),
            ("ATR0", "Response Format aus"),
            ("ATSP 0", "Protokoll Auto"),
        ]
        
        for cmd, desc in setup_cmds:
            try:
                response = await self.send_command(cmd, timeout=2.0)
                logger.info(f"  {desc}: '{response}'")
            except Exception as e:
                logger.error(f"  {desc}: ❌ {e}")
    
    async def scan_services(self):
        """Scannt alle BLE Services und Characteristics."""
        if not self.client or not self.client.is_connected:
            logger.error("Nicht verbunden!")
            return
        
        services = self.client.services
        logger.info("\n" + "=" * 60)
        logger.info("BLE Services des IOS-Vlink:")
        logger.info("=" * 60)
        
        for svc in services:
            logger.info(f"\nService: {svc.uuid}")
            for ch in svc.characteristics:
                props = str(ch.properties)
                logger.info(f"  Char: {ch.uuid}")
                logger.info(f"    Properties: {props}")
                logger.info(f"    Description: {ch.description}")
    
    async def parse_speed(self, response: str) -> float:
        """Parsst Speed aus OBD2 Antwort 010D.
        Format: '41 0D XX' wobei speed = int(XX, 16) km/h
        """
        # Bereinigen
        cleaned = response.replace(' ', '').replace('\r', '').replace('\n', '')
        
        for i, part in enumerate(cleaned.split()):
            if part.upper() == '410D' and i + 1 < len(cleaned.split()):
                try:
                    speed = int(cleaned.split()[i + 1], 16)
                    return float(speed)
                except ValueError:
                    pass
        return 0.0
    
    async def parse_throttle(self, response: str) -> float:
        """Parsst Throttle aus 22 20 2E (Renault ZE).
        Format: '62202E0000' — Byte 4 ist Throttle in %
        """
        cleaned = response.replace(' ', '').replace('\r', '').replace('\n', '')
        
        if cleaned.startswith('62202E') and len(cleaned) >= 12:
            try:
                # Byte 4 (Position 8-9) ist Throttle
                throttle_byte = int(cleaned[8:10], 16)
                return float(throttle_byte)
            except ValueError:
                pass
        
        # Standard OBD2 Throttle 0111
        cleaned = response.replace(' ', '').replace('\r', '').replace('\n', '')
        for i, part in enumerate(cleaned.split()):
            if part.upper() == '4111' and i + 1 < len(cleaned.split()):
                try:
                    throttle = int(cleaned.split()[i + 1], 16) * 100 / 255
                    return float(throttle)
                except ValueError:
                    pass
        return 0.0
    
    async def parse_rpm(self, response: str) -> float:
        """Parsst RPM aus OBD2 Antwort 010C.
        Format: '41 0C A B' wobei RPM = (256*A + B) / 4
        """
        cleaned = response.replace(' ', '').replace('\r', '').replace('\n', '')
        parts = cleaned.split()
        for i, part in enumerate(parts):
            if part.upper() == '410C' and i + 3 < len(parts):
                try:
                    a = int(parts[i + 1], 16)
                    b = int(parts[i + 2], 16)
                    rpm = ((256 * a + b) / 4)
                    return rpm
                except (ValueError, IndexError):
                    pass
        return 0.0
    
    async def test_elm327(self):
        """Testet grundlegende ELM327-Befehle MIT ECHO-FILTERING."""
        if not self.client or not self.client.is_connected:
            logger.error("Nicht verbunden!")
            return
        
        # ELM327 Setup
        await self.setup_elm327()
        
        commands = [
            ("0100", "Supported PIDs"),
            ("010D", "Vehicle Speed"),
            ("010C", "Engine RPM"),
            ("0111", "Throttle Position"),
            ("0114", "Control Module Voltage"),
            ("222003", "Speed (CanZE 22XXXX)"),
            ("22202E", "Throttle (CanZE 22XXXX)"),
            ("229001", "Battery SOC (CanZE 22XXXX)"),
        ]
        
        logger.info("\n" + "=" * 60)
        logger.info("ELM327 Command-Response Test")
        logger.info("=" * 60)
        
        for cmd, desc in commands:
            try:
                logger.info(f"\nBefehl: {cmd} ({desc})")
                response = await self.send_command(cmd, timeout=2.0)
                
                if response and response.strip():
                    logger.info(f"  ✅ Antwort: {response}")
                    
                    # Speed parsen
                    if cmd == "010D":
                        speed = await self.parse_speed(response)
                        if speed > 0:
                            logger.info(f"  🚗 Speed: {speed} km/h")
                            self.obd_data.speed = speed
                    
                    # Throttle parsen
                    elif cmd == "22202E":
                        throttle = await self.parse_throttle(response)
                        if throttle > 0:
                            logger.info(f"  🔧 Throttle: {throttle:.1f}%")
                            self.obd_data.throttle = throttle
                    
                    # RPM parsen
                    elif cmd == "010C":
                        rpm = await self.parse_rpm(response)
                        if rpm > 0:
                            logger.info(f"  ⚙️ RPM: {rpm:.0f}")
                            self.obd_data.rpm = rpm
                else:
                    logger.info(f"  ⚠️  Keine Antwort erhalten")
                
            except Exception as e:
                logger.error(f"  ❌ Fehler: {e}")
        
        logger.info("\n" + "=" * 60)
        logger.info("ZUSAMMENFASSUNG")
        logger.info("=" * 60)
        logger.info(f"Speed: {self.obd_data.speed} km/h")
        logger.info(f"RPM: {self.obd_data.rpm}")
        logger.info(f"Throttle: {self.obd_data.throttle}%")
        logger.info(f"Raw Response: {self.obd_data.raw_response}")
    
    async def disconnect(self):
        """Trennt die BLE-Verbindung."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            logger.info("❌ BLE getrennt")


async def main():
    """Hauptfunktion."""
    print("=" * 60)
    print("IOS-Vlink / vGate iCar Pro BLE GATT Client")
    print("Basierend auf CanZE Protocol (BLE)")
    print("=" * 60)
    
    if os.geteuid() != 0:
        print("\n❌ FEHLER: Muss als root ausgeführt werden!")
        print("Befehl: sudo python3 ble_client_vgate_root.py")
        sys.exit(1)
    
    print(f"\n📡 MAC: {VGLITE_MAC}")
    print(f"📡 Service: {VGLITE_SERVICE}")
    print(f"📡 Char: {VGLITE_CHAR}")
    
    client = VGateBLEClient(debug=True)
    
    # Verbinden
    if not await client.connect():
        sys.exit(1)
    
    # Services scannen
    await client.scan_services()
    
    # ELM327-Test
    await client.test_elm327()
    
    # Trennen
    await client.disconnect()
    print("\n✅ Test abgeschlossen!")


if __name__ == "__main__":
    asyncio.run(main())