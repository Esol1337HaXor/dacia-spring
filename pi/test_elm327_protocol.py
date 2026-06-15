#!/usr/bin/env python3
"""
ELM327 Protocol Test-Skript
=============================
Testet das ELM327-Protokoll ohne TCP-Server.

Usage:
    source ~/obd2-adapter-env/bin/activate
    python test_elm327_protocol.py
"""

import sys
import logging

# Import the protocol implementation
from elm327_tcp_server import ELM327Protocol

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("elm327-test")


def test_at_commands(protocol: ELM327Protocol):
    """Test ELM327 AT commands."""
    logger.info("=" * 60)
    logger.info("TEST: AT Commands")
    logger.info("=" * 60)
    
    test_commands = [
        ("ATZ", "Reset"),
        ("ATI", "Product info"),
        ("ATA", "Answer"),
        ("ATE0", "Echo off"),
        ("ATE1", "Echo on"),
        ("ATH0", "Header off"),
        ("ATH1", "Header on"),
        ("ATS0", "Space off"),
        ("ATS1", "Space on"),
        ("ATSP0", "Auto protocol"),
    ]
    
    for cmd, desc in test_commands:
        response = protocol.process_command(cmd)
        logger.info(f"  {cmd:8s} ({desc:15s}):")
        for line in response.strip().split("\r\n"):
            logger.info(f"    -> {line}")
    
    # Reset to default state
    protocol.process_command("ATE1")
    protocol.process_command("ATH1")
    protocol.process_command("ATS1")


def test_obd_commands(protocol: ELM327Protocol):
    """Test OBD2 PID commands."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST: OBD2 PID Commands")
    logger.info("=" * 60)
    
    test_commands = [
        ("0100", "Supported PIDs 01-20"),
        ("0101", "Status (calculated load)"),
        ("0104", "Calculated Engine Load"),
        ("0105", "Engine Coolant Temperature"),
        ("010C", "Engine RPM"),
        ("010D", "Vehicle Speed"),
        ("010E", "Throttle Position"),
        ("0111", "Engine Load (8-bit)"),
        ("0114", "Coolant Temp (alt)"),
        ("0120", "Supported PIDs 21-40"),
    ]
    
    for cmd, desc in test_commands:
        response = protocol.process_command(cmd)
        logger.info(f"  {cmd:8s} ({desc:25s}):")
        for line in response.strip().split("\r\n"):
            logger.info(f"    -> {line}")


def test_rpm_calculation(protocol: ELM327Protocol):
    """Test RPM calculation with multiple readings."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST: RPM Calculation (10 readings)")
    logger.info("=" * 60)
    
    rpms = []
    for i in range(10):
        response = protocol.process_command("010C")
        # Parse response: "41 0C XX XX"
        parts = response.strip().split()
        if len(parts) >= 4:
            a = int(parts[2], 16)
            b = int(parts[3], 16)
            rpm = (a * 256 + b) / 4
            rpms.append(rpm)
            logger.info(f"  Reading {i+1:2d}: {rpm:.0f} RPM")
    
    if rpms:
        logger.info(f"  Average: {sum(rpms)/len(rpms):.0f} RPM")
        logger.info(f"  Min:     {min(rpms):.0f} RPM")
        logger.info(f"  Max:     {max(rpms):.0f} RPM")


def test_full_session(protocol: ELM327Protocol):
    """Test a full ELM327 session like an app would use."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST: Full Session Simulation")
    logger.info("=" * 60)
    
    session = [
        # App connects
        ("ATZ", "Reset"),
        ("ATI", "Get device info"),
        ("ATE0", "Disable echo"),
        ("ATH0", "Disable header"),
        ("ATS0", "Disable space"),
        ("ATSP0", "Auto protocol"),
        ("", "Prompt"),
        ("0100", "Check supported PIDs"),
        ("010C", "Get RPM"),
        ("010D", "Get Speed"),
    ]
    
    logger.info("  Simulating app connection:")
    for cmd, desc in session:
        response = protocol.process_command(cmd)
        if cmd:
            logger.info(f"  > {cmd:6s}  ({desc})")
        else:
            logger.info(f"         ({desc})")
        if response:
            for line in response.strip().split("\r\n"):
                logger.info(f"    <- {line}")


def test_manual_telnet():
    """Print instructions for manual telnet testing."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Manual Test Instructions")
    logger.info("=" * 60)
    logger.info("")
    logger.info("1. Start the TCP server on the Pi:")
    logger.info("   cd ~/obd2-adapter")
    logger.info("   source ~/obd2-adapter-env/bin/activate")
    logger.info("   python elm327_tcp_server.py")
    logger.info("")
    logger.info("2. From another terminal (or your PC):")
    logger.info("   telnet 192.168.178.87 4000")
    logger.info("")
    logger.info("3. Test commands:")
    logger.info("   ATZ          -> Reset")
    logger.info("   ATI          -> Get device info")
    logger.info("   0100         -> Supported PIDs")
    logger.info("   010C         -> Engine RPM")
    logger.info("   010D         -> Vehicle Speed")
    logger.info("")
    logger.info("4. Or use netcat:")
    logger.info("   echo -e 'ATZ\\r010C\\r' | nc 192.168.178.87 4000")


def main():
    """Run all tests."""
    logger.info("")
    logger.info("*" * 60)
    logger.info("ELM327 Protocol Test Suite")
    logger.info("*" * 60)
    logger.info("")
    
    protocol = ELM327Protocol()
    
    # Run tests
    test_at_commands(protocol)
    test_obd_commands(protocol)
    test_rpm_calculation(protocol)
    test_full_session(protocol)
    test_manual_telnet()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("All tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()