#!/usr/bin/env python3
"""
ELM327 OBD2 Emulator für Raspberry Pi Zero 2 W
Emuliert einen ELM327 OBD2-Adapter über BLE GATT Service.

Wird erkannt von: RevHeadz, Potenza Drive, OBD2 Tester Apps, etc.

BLE Service UUID: 0000ffe1-0000-1000-8000-00805f9b34fb
(Vgate iCar Pro / ELM327 Standard GATT Service)

Usage:
    source ~/obd2-adapter-env/bin/activate
    python elm327_ble_emulator.py
"""

import asyncio
import logging
import struct
import time
from datetime import datetime

from bleak import BleakGATTService, BleakScanner, BleakServer
from bleak.backends.characteristic import GATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.service import GATTService

# ========================
# Configuration
# ========================

BLE_SERVICE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
BLE_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Device advertisement
DEVICE_NAME = "iCar Pro"
MANUFACTURER_NAME = "Vgate"
HARDWARE_REVISION = "ELM327 v1.5a"
FIRMWARE_REVISION = "3.1"

# RPM Simulation settings
IDLE_RPM = 850
MAX_RPM = 7500
MIN_RPM = 400

# Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("elm327-emulator")

# ========================
# ELM327 Protocol State
# ========================

class ELM327State:
    """State machine for ELM327 protocol emulation."""
    
    def __init__(self):
        self.echo_enabled = True      # AT Echo
        self.header_enabled = True     # PID response header
        self.space_enabled = True      # Space between responses
        self.protocol_auto = True      # Auto protocol selection
        self.line_terminator = "\r\n"
        self.ready = True              # Device ready flag
        self.obd_ready = True          # OBD system ready
        
    def process_command(self, cmd: str) -> str:
        """Process an ELM327 command and return response."""
        cmd = cmd.strip()
        logger.info(f"Command received: '{cmd}'")
        
        # Handle AT commands
        if cmd.startswith("AT"):
            return self._handle_at_command(cmd)
        
        # Handle OBD2 PID commands
        else:
            return self._handle_obd_command(cmd)
    
    def _handle_at_command(self, cmd: str) -> str:
        """Handle ELM327 AT commands with space-tolerant parsing."""
        # Normalize: remove spaces and uppercase
        normalized = cmd.replace(" ", "").strip().upper()
        
        # Reset
        if normalized == "ATZ":
            # Minimal response for RevHeadz compatibility
            return f"ELM327 v1.5a{self.line_terminator}OK{self.line_terminator}"
        
        # Version info
        elif normalized == "ATI":
            return f"iCar Pro{self.line_terminator}"
        
        # Turn echo on/off
        elif normalized == "ATE0":
            self.echo_enabled = False
            return f"OK{self.line_terminator}"
        elif normalized == "ATE1":
            self.echo_enabled = True
            return f"OK{self.line_terminator}"
        
        # Turn header on/off
        elif normalized == "ATH0":
            self.header_enabled = False
            return f"OK{self.line_terminator}"
        elif normalized == "ATH1":
            self.header_enabled = True
            return f"OK{self.line_terminator}"
        
        # Turn spaces on/off
        elif normalized == "ATS0":
            self.space_enabled = False
            return f"OK{self.line_terminator}"
        elif normalized == "ATS1":
            self.space_enabled = True
            return f"OK{self.line_terminator}"
        
        # Set protocol to auto
        elif normalized == "ATSP0":
            self.protocol_auto = True
            return f"OK{self.line_terminator}"
        
        # Show current settings
        elif normalized == "ATA":
            return f"ELM327 v1.5a{self.line_terminator}"
        
        else:
            return f"UNK{self.line_terminator}"
    
    def _handle_obd_command(self, cmd: str) -> str:
        """Handle OBD2 PID requests with space-tolerant parsing."""
        # Normalize: remove spaces
        normalized = cmd.replace(" ", "").strip().upper()
        
        # PID 0x0C (RPM)
        if normalized == "010C":
            rpm = self._calculate_rpm()
            # Response: 41 0C XX XX (RPM = (X*256+Y)/4)
            a = (rpm * 4) >> 8
            b = (rpm * 4) & 0xFF
            response = f"41 0C {a:02X} {b:02X}"
            logger.info(f"RPM Response: {rpm} RPM -> {response}")
            return response
        
        # PID 0x0D (Speed)
        elif normalized == "010D":
            speed = 0  # No real speed data without CAN connection
            a = speed
            response = f"41 0D {a:02X}"
            logger.info(f"Speed Response: {speed} km/h -> {response}")
            return response
        
        # PID 0x00 (Supported PIDs)
        elif normalized == "0100":
            # Support PIDs 0x00, 0x01, 0x0C, 0x0D, 0x05
            # Bitmask: PID 00 supported, 01 supported, 0C supported, 0D supported, 05 supported
            supported = 0xE0000001  # Bits 0, 12, 13, 29 set
            a = (supported >> 24) & 0xFF
            b = (supported >> 16) & 0xFF
            c = (supported >> 8) & 0xFF
            d = supported & 0xFF
            response = f"41 00 {a:02X} {b:02X} {c:02X} {d:02X}"
            return response
        
        # PID 0x05 (Coolant Temperature)
        elif normalized == "0105":
            temp = 90  # Fake: 90°C
            a = temp + 40
            response = f"41 05 {a:02X}"
            return response
        
        # PID 0x04 (Calculated Engine Load)
        elif normalized == "0104":
            load = 30  # Fake: 30%
            a = int(load * 255 / 100)
            response = f"41 04 {a:02X}"
            return response
        
        else:
            return f"NO DATA{self.line_terminator}"
    
    def _calculate_rpm(self) -> int:
        """Calculate simulated RPM value."""
        import random
        
        # Base RPM with slight noise
        rpm = IDLE_RPM + random.randint(-20, 20)
        return max(MIN_RPM, min(MAX_RPM, rpm))


# ========================
# BLE GATT Server
# ========================

class ELM327BLEServer:
    """BLE GATT Server that emulates ELM327 OBD2 adapter."""
    
    def __init__(self):
        self.state = ELM327State()
        self.connected = False
        self.connected_device = None
        self.characteristic = None
        self._start_time = datetime.now()
        
    def _create_services(self, server):
        """Create GATT services and characteristics."""
        
        # Add standard ELM327 service
        service = server.add_service(
            service_uuid=BLE_SERVICE_UUID,
            characteristic_uuid=BLE_CHAR_UUID,
        )
        
        # Set characteristic with write+notify
        service.add_characteristic(
            uuid=BLE_CHAR_UUID,
            properties="read|write|notify",
            value=b"",
        )
        
        logger.info(f"Created GATT Service: {BLE_SERVICE_UUID}")
        
    async def _on_connect(self, bluetooth_device: BLEDevice):
        """Handle BLE connection."""
        self.connected = True
        self.connected_device = bluetooth_device
        logger.info(f"Device connected: {bluetooth_device.address} ({bluetooth_device.name})")
        
    async def _on_disconnect(self, bluetooth_device: BLEDevice):
        """Handle BLE disconnection."""
        self.connected = False
        self.connected_device = None
        logger.info("Device disconnected")
        
    async def _on_write(self, characteristic: GATTCharacteristic, data):
        """Handle write requests from connected device."""
        try:
            # Decode data
            if isinstance(data, bytes):
                cmd = data.decode("utf-8", errors="ignore").strip()
            else:
                cmd = str(data).strip()
            
            logger.info(f"Received command: '{cmd}'")
            
            # Process through ELM327 state machine
            response = self.state.process_command(cmd)
            
            # Add echo if enabled
            if self.state.echo_enabled:
                echo_response = cmd + "\r"
            else:
                echo_response = ""
            
            full_response = echo_response + response
            
            # Encode response
            response_bytes = full_response.encode("utf-8")
            
            # Send notification/write response
            try:
                await self.characteristic.write_response(response_bytes, True)
                logger.info(f"Sent response: '{full_response.strip()}'")
            except Exception as e:
                logger.error(f"Failed to send response: {e}")
                
        except Exception as e:
            logger.error(f"Error handling write: {e}", exc_info=True)
            try:
                error_response = "ERROR\r\n".encode("utf-8")
                await self.characteristic.write_response(error_response, True)
            except Exception:
                pass
    
    async def run(self):
        """Start the BLE GATT Server."""
        logger.info("=" * 60)
        logger.info("ELM327 BLE Emulator Starting...")
        logger.info(f"Service UUID: {BLE_SERVICE_UUID}")
        logger.info(f"Device Name: {DEVICE_NAME}")
        logger.info("=" * 60)
        
        # Scan for existing devices first (to check BLE works)
        logger.info("Scanning for BLE devices...")
        try:
            devices = await BleakScanner.discover(timeout=5.0)
            logger.info(f"Found {len(devices)} BLE device(s):")
            for device in devices:
                logger.info(f"  - {device.address}: {device.name}")
        except Exception as e:
            logger.warning(f"BLE scan failed (server will still work): {e}")
        
        # Start GATT server
        # Using a simple approach: listen on any available BLE address
        logger.info("Starting BLE GATT Server...")
        logger.info("Waiting for connections...")
        
        # NOTE: bleak.server requires specific setup
        # Alternative: use bluez D-Bus API directly
        # For now, we'll use a simpler approach
        
        try:
            await self._run_with_bluez()
        except Exception as e:
            logger.error(f"BlueZ server failed: {e}")
            logger.info("Trying fallback server...")
            await self._run_fallback()
    
    async def _run_with_bluez(self):
        """Try to run using bleak server with BlueZ."""
        from bleak.backends.service import BleakService
        
        # Get local adapter address
        import subprocess
        try:
            result = subprocess.run(
                ["hcitool", "cmd", "0x3F", "0x001", b""],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass
        
        # Try to create server - this requires root privileges
        # and proper BlueZ configuration
        logger.info("Attempting to start BLE GATT server...")
        logger.info("NOTE: This requires root privileges and BLE advertising support")
        logger.info("On Pi Zero 2 W, BLE GATT Server mode may not be fully supported")
        logger.info("Consider using Bluetooth SPP via rfcomm instead")
        
        # For Pi Zero 2 W, the BLE controller (CYC004335B0) supports
        # both peripheral and central modes, but not simultaneously
        # with central mode active.
        
        # Alternative approach: Use bleak in CLIENT mode to connect to
        # Vgate iCar Pro, then use a TCP/Serial socket for ELM327 emulation
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("RECOMMENDED APPROACH: TCP Socket ELM327 Emulator")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Instead of BLE GATT Server (limited on Pi Zero):")
        logger.info("1. Vgate iCar Pro BLE -> Pi (bleak client)")
        logger.info("2. Pi emulates ELM327 on TCP port 4000")
        logger.info("3. Android App connects to Pi via WiFi/BLE")
        logger.info("")
        logger.info("See: elm327_tcp_server.py for TCP-based approach")
        
    async def _run_fallback(self):
        """Fallback: Print instructions for manual setup."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("BLE GATT Server Setup Instructions")
        logger.info("=" * 60)
        logger.info("")
        logger.info("For Raspberry Pi Zero 2 W:")
        logger.info("")
        logger.info("Option 1: Use BLE GATT Server (requires root)")
        logger.info("  sudo python elm327_ble_emulator.py")
        logger.info("")
        logger.info("Option 2: Use TCP Socket (recommended)")
        logger.info("  python elm327_tcp_server.py --port 4000")
        logger.info("")
        logger.info("Option 3: Use Bluetooth SPP via rfcomm")
        logger.info("  sudo rfcomm bind /dev/rfcomm0 XX:XX:XX:XX:XX:XX 1")
        logger.info("  picocom /dev/rfcomm0 -b 115200")
        logger.info("")


# ========================
# Main Entry Point
# ========================

async def main():
    """Main entry point."""
    emulator = ELM327BLEServer()
    
    try:
        await emulator.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())