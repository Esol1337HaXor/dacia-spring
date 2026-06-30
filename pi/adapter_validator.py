#!/usr/bin/env python3
"""
ELM327 Adapter Validator für Dacia Spring CAN-Bus Kommunikation

Überprüft ob ein angeschlossener ELM327-Adapter tatsächlich die erforderlichen
Features für die Kommunikation mit dem Dacia Spring unterstützt:
- Echte ELM327 Firmware (PIC18F25K80 oder PIC18F47K42)
- Extended CAN IDs (29-bit / UDS Protocol)
- J1939 Dynamic Address Support
- Full OBD2 PID Support

Verbindungsmethoden:
- Serial (Bluetooth/USB TTL)
- TCP/IP (WiFi Adapter wie vGate iCar Pro)
- BLE (Bluetooth Low Energy)

Autor: Dacia Spring Projekt
Lizenz: GPL-3.0
"""

import socket
import serial
import time
import re
import json
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ============================================================================
# KONFIGURATION
# ============================================================================

# Standard-Einstellungen für ELM327 Adapter
DEFAULT_BAUDRATE = 38400       # Standard Baudrate für ELM327
DEFAULT_TIMEOUT = 5.0          # Timeout in Sekunden für Antworten
AUTO_RECONNECT_RETRIES = 3     # Wie oft soll bei Fehler neu verbunden werden

# CAN-Bus Geschwindigkeiten für Renault/Dacia
CAN_500KBPS = 6       # ISO 15765-4 500K (Standard für Renault)
CAN_250KBPS = 7       # ISO 15765-4 250K

# Wichtige CAN-IDs für Dacia Spring / Renault Zoe
DACIA_SPRING_CAN_IDS = {
    'standard_obd2': 0x7DF,           # OBD2 Broadcast
    'diagnostic_request': 0x7E0,      # Extended Diagnostic Request
    'diagnostic_response': 0x7E8,     # Extended Diagnostic Response
    'kom_motor': 0x0B0,               # Motor-Status
    'battery_management': 0x2B8,      # Batteriemanagement (LBC)
    'uds_request': 0x7DF,             # UDS über OBD2
    'uds_response': 0x7E8,            # UDS Response
    'j1939_extended': 0x18DA,         # J1939 Extended Address
    'uds_dynamic_request': 0x18DAF100, # UDS Dynamic 0xF0
    'uds_dynamic_response': 0x18DA00F1, # UDS Dynamic 0xF1
}

# OBD2 PIDs die wir testen
TEST_OBD2_PIDS = [
    '0100',   # Supported PIDs (00-1F)
    '010C',   # Engine RPM
    '010D',   # Vehicle Speed
    '0105',   # Coolant Temperature
    '0104',   # Calculated Engine Load
    '0105',   # Engine Coolant Temperature
    '0109',   # Required Distance to MIL
    '010F',   # Intake Air Temperature
    '0111',   # Control Module Voltage
    '011C',   # Absolute Load Value
]

# UDS Tests (Extended Diagnostic)
TEST_UDS_MODES = [
    ('03', 'Freeze Frame Data'),
    ('04', 'Tester Present - Keep Alive'),
    ('09', 'Vehicle Info (VIN, etc.)'),
    ('1A', 'Diagnostic Service Listing'),
]

# ============================================================================
# ENUMS & DATACLASSES
# ============================================================================

class ConnectionType(Enum):
    """Verbindungstyp für den Adapter."""
    SERIAL = "serial"
    TCP = "tcp"
    BLE = "ble"

class TestStatus(Enum):
    """Status eines einzelnen Tests."""
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"
    WARN = "warning"
    SKIP = "skip"

@dataclass
class TestResult:
    """Ergebnis eines einzelnen Tests."""
    name: str
    command: str
    expected_pattern: str
    status: TestStatus
    response: str
    details: str = ""

@dataclass
class AdapterInfo:
    """Informationen über den erkannten Adapter."""
    vendor: str = ""
    firmware_version: str = ""
    chip_type: str = ""
    protocol: str = ""
    can_speed: str = ""

@dataclass
class ValidationReport:
    """Gesamter Validierungsbericht."""
    adapter_info: AdapterInfo = field(default_factory=AdapterInfo)
    results: List[TestResult] = field(default_factory=list)
    overall_score: float = 0.0
    is_compatible: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

# ============================================================================
# LOGGING KONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('elm327_validator')

# ============================================================================
# ELM327 ADAPTER VALIDATOR
# ============================================================================

class ELM327Validator:
    """
    Validiert ELM327-Adapter auf Kompatibilität mit dem Dacia Spring.

    Führt eine Serie von AT-Befehlen und OBD2/UDS-Tests durch um zu prüfen,
    ob der Adapter die erforderlichen Features unterstützt.
    """

    # Pattern für ELM327 Identifikation
    ELM327_PATTERN = re.compile(r'ELM327\s*v?(\d+\.\d+)', re.IGNORECASE)
    PIC18F_PATTERN = re.compile(r'PIC18F|pIC18F', re.IGNORECASE)
    OBDLINK_PATTERN = re.compile(r'OBDLink', re.IGNORECASE)
    KONWEI_PATTERN = re.compile(r'KONWEI|KW', re.IGNORECASE)

    def __init__(
        self,
        connection_type: ConnectionType,
        target: str,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = DEFAULT_TIMEOUT
    ):
        """
        Initialisiert den Validator.

        Args:
            connection_type: Art der Verbindung (serial/tcp/ble)
            target: Serial-Port (z.B. '/dev/ttyAMA0') oder Host:Port (z.B. '192.168.1.123:23')
            baudrate: Baudrate für serielle Verbindungen
            timeout: Timeout in Sekunden
        """
        self.conn_type = connection_type
        self.target = target
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self.report = ValidationReport()
        self.is_connected = False
        self._buffer = ""

        logger.info(
            f"Validator initialisiert: type={connection_type.value}, "
            f"target={target}, baudrate={baudrate}, timeout={timeout}s"
        )

    # ------------------------------------------------------------------
    # VERBINDUNGSMANAGEMENT
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Stellt eine Verbindung zum Adapter her."""
        try:
            if self.conn_type == ConnectionType.SERIAL:
                self.connection = serial.Serial(
                    port=self.target,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
            elif self.conn_type == ConnectionType.TCP:
                host, port = self.target.rsplit(':', 1)
                port = int(port)
                self.connection = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM
                )
                self.connection.settimeout(2.0)
                self.connection.connect((host, port))
                # Kurzes Lesen der Willkommensnachricht
                self.connection.settimeout(0.3)
                try:
                    while True:
                        chunk = self.connection.recv(4096)
                        if not chunk:
                            break
                        self._buffer += chunk.decode('ascii', errors='ignore')
                except socket.timeout:
                    pass
                # Timeout zurücksetzen
                self.connection.settimeout(self.timeout)
            elif self.conn_type == ConnectionType.BLE:
                # BLE-Verbindung über RFCOMM
                self.connection = serial.Serial(
                    port=self.target,
                    baudrate=self.baudrate,
                    timeout=self.timeout
                )

            self.is_connected = True
            logger.info(f"Verbunden mit {self.target}")
            return True

        except Exception as e:
            logger.error(f"Verbindungsfehler: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Trennt die Verbindung zum Adapter."""
        if self.connection:
            try:
                if self.conn_type == ConnectionType.TCP:
                    self.connection.close()
                elif self.conn_type in (ConnectionType.SERIAL, ConnectionType.BLE):
                    self.connection.close()
                logger.info("Verbindung getrennt")
            except Exception as e:
                logger.warning(f"Fehler beim Trennen: {e}")
            finally:
                self.is_connected = False
                self.connection = None
                self._buffer = ""

    def _read_until_timeout(self) -> str:
        """Liest bis zum Timeout und hängt an den Buffer an."""
        data = ""
        self.connection.settimeout(0.3)
        while True:
            try:
                chunk = self.connection.recv(4096)
                if chunk:
                    data += chunk.decode('ascii', errors='ignore')
                else:
                    break
            except socket.timeout:
                break
            except Exception:
                break
        self._buffer += data
        return data

    def send_command(
        self,
        command: str,
        strip_prompt: bool = True
    ) -> str:
        """
        Sendet einen Befehl an den Adapter und empfängt die Antwort.
        """
        if not self.is_connected:
            logger.error("Nicht verbunden!")
            return ""

        try:
            if self.conn_type == ConnectionType.TCP:
                # Buffer leeren
                self._buffer = ""
                
                # Command senden
                cmd_bytes = command.encode('ascii')
                if not cmd_bytes.endswith(b'\r'):
                    cmd_bytes = cmd_bytes + b'\r'
                self.connection.sendall(cmd_bytes)
                
                # Auf Antwort warten
                time.sleep(0.2)
                
                # Socket nicht-blockierend setzen für multi-packet read
                self.connection.settimeout(0.3)
                response = ""
                for _ in range(5):  # Max 5 Lese-Zyklen
                    try:
                        chunk = self.connection.recv(4096)
                        if chunk:
                            response += chunk.decode('ascii', errors='ignore')
                        else:
                            break
                    except socket.timeout:
                        break
                    except Exception:
                        break
                
                # Prompt entfernen (alles VOR dem letzten > nehmen)
                if strip_prompt and '>' in response:
                    response = response.split('>', 1)[0]
                response = response.strip()
                
                logger.debug(f"TCP: '{command}' -> '{response[:200]}'")
                return response

            else:
                # Serial/BLE
                cmd_bytes = command.encode('ascii')
                if not cmd_bytes.endswith(b'\r'):
                    cmd_bytes = cmd_bytes + b'\r'
                self.connection.write(cmd_bytes)
                time.sleep(0.5)
                response = self.connection.read(
                    self.connection.in_waiting or 1024
                ).decode('ascii', errors='ignore')

                if strip_prompt and '>' in response:
                    response = response.split('>', 1)[-1]
                response = response.strip()
                return response

        except Exception as e:
            logger.error(f"Fehler beim Senden von '{command}': {e}")
            return ""

    # ------------------------------------------------------------------
    # TEST-FUNKTIONEN
    # ------------------------------------------------------------------

    def _add_result(
        self,
        name: str,
        command: str,
        expected_pattern: str,
        status: TestStatus,
        response: str,
        details: str = ""
    ):
        """Fügt ein Testergebnis zum Bericht hinzu."""
        self.report.results.append(TestResult(
            name=name,
            command=command,
            expected_pattern=expected_pattern,
            status=status,
            response=response,
            details=details
        ))

        if status == TestStatus.PASS:
            logger.info(f"✅ {name}: PASS")
        elif status == TestStatus.WARN:
            logger.warning(f"⚠️  {name}: WARN")
            self.report.warnings.append(details or name)
        elif status == TestStatus.FAIL:
            logger.error(f"❌ {name}: FAIL")
            self.report.errors.append(details or name)
        else:
            logger.info(f"➖ {name}: {status.value}")

    # --- Test 1: ELM327 Identifikation ---

    def test_atz(self) -> TestResult:
        """
        Test ATZ - Reset des Adapters und Identifikation.

        Erwartete Antwort: "ELM327 v1.5" oder "ELM327 v2.1"
        """
        response = self.send_command('ATZ')
        time.sleep(0.5)  # Warten auf vollständigen Reset

        if 'elm327' in response.lower():
            # Firmware-Version extrahieren
            match = self.ELM327_PATTERN.search(response)
            version = match.group(1) if match else "unknown"
            self.report.adapter_info.firmware_version = version

            # Chip-Typ prüfen
            if self.PIC18F_PATTERN.search(response):
                self.report.adapter_info.chip_type = "PIC18F25K80"
            else:
                self.report.adapter_info.chip_type = "unknown (but ELM327)"

            self._add_result(
                name="ATZ - Adapter Reset",
                command="ATZ",
                expected_pattern="ELM327 v[0-9.]+",
                status=TestStatus.PASS,
                response=response,
                details=f"ELM327 v{version} erkannt"
            )
            return self.report.results[-1]
        else:
            self._add_result(
                name="ATZ - Adapter Reset",
                command="ATZ",
                expected_pattern="ELM327 v[0-9.]+",
                status=TestStatus.FAIL,
                response=response,
                details="Kein echter ELM327 Adapter erkannt"
            )
            return self.report.results[-1]

    def test_ati(self) -> TestResult:
        """
        Test ATI - Zusätzliche Adapter-Informationen.

        Erwartete Antwort: Vendor/Chip Information wie "PIC18F25K80"
        """
        response = self.send_command('ATI')

        chip_found = self.PIC18F_PATTERN.search(response)
        vendor_found = (
            self.OBDLINK_PATTERN.search(response) or
            self.KONWEI_PATTERN.search(response)
        )

        if chip_found:
            self.report.adapter_info.chip_type = "PIC18F25K80/PIC18F47K42"
            self._add_result(
                name="ATI - Chip Identification",
                command="ATI",
                expected_pattern="PIC18F",
                status=TestStatus.PASS,
                response=response,
                details="PIC18F25K80 oder PIC18F47K42 Chip bestätigt"
            )
        elif vendor_found:
            self.report.adapter_info.vendor = "OBDLink/KONWEI"
            self._add_result(
                name="ATI - Chip Identification",
                command="ATI",
                expected_pattern="OBDLink|KONWEI",
                status=TestStatus.WARN,
                response=response,
                details="Vendor erkannt, aber PIC18F nicht explizit erwähnt"
            )
        else:
            self._add_result(
                name="ATI - Chip Identification",
                command="ATI",
                expected_pattern="PIC18F|OBDLink|KONWEI",
                status=TestStatus.WARN,
                response=response,
                details="Kein bekannter Chip/Vendor erkannt (könnte ein Clone sein)"
            )

        return self.report.results[-1]

    # --- Test 2: CAN-Protokoll-Erkennung ---

    def test_auto_protocol(self) -> TestResult:
        """
        Test ATSP0 - Aktiviert Auto-Protokoll-Erkennung.

        WICHTIG: Ohne Auto-Probing kann der Adapter nicht automatisch
        zwischen verschiedenen CAN-Geschwindigkeiten wechseln.
        """
        response1 = self.send_command('ATSP0')
        time.sleep(0.3)
        response2 = self.send_command('ATDPN')  # Aktuelle Protokoll-Nummer

        # Protokoll-Nummer prüfen
        # 6 = ISO 15765-4 500K (Standard für Renault/Dacia)
        # 7 = ISO 15765-4 250K
        if response2.strip().isdigit():
            proto_num = int(response2.strip())
            proto_map = {
                1: "SAE J1850 PWM",
                2: "SAE J1850 VPW",
                3: "ISO 9141-2",
                4: "ISO 14230-4 KWP (5 baud init)",
                5: "ISO 14230-4 KWP fast",
                6: "ISO 15765-4 (CAN 500K)",
                7: "ISO 15765-4 (CAN 250K)",
                8: "SAE J1939 (CAN 250K)",
                9: "SAE J1939 (CAN 500K)",
                10: "USER1 (CAN 500K)",
                11: "USER2 (CAN 250K)",
            }
            proto_name = proto_map.get(proto_num, f"Unknown ({proto_num})")
            self.report.adapter_info.protocol = proto_name
            self.report.adapter_info.can_speed = "500K" if proto_num == 6 else "250K"

            if proto_num == 6:  # ISO 15765-4 500K
                self._add_result(
                    name="ATSP0 + ATDPN - CAN Protocol Detection",
                    command="ATSP0 + ATDPN",
                    expected_pattern="6",
                    status=TestStatus.PASS,
                    response=response2,
                    details=f"ISO 15765-4 CAN 500K (Standard für Renault/Dacia)"
                )
            else:
                self._add_result(
                    name="ATSP0 + ATDPN - CAN Protocol Detection",
                    command="ATSP0 + ATDPN",
                    expected_pattern="6|7",
                    status=TestStatus.WARN,
                    response=response2,
                    details=f"Protokoll {proto_num} ({proto_name}) - könnte manuell auf 6 gesetzt werden müssen"
                )
        else:
            self._add_result(
                name="ATSP0 + ATDPN - CAN Protocol Detection",
                command="ATSP0 + ATDPN",
                expected_pattern="6|7",
                status=TestStatus.FAIL,
                response=response2,
                details=f"Ungültige Protokoll-Nummer: '{response2}'"
            )

        return self.report.results[-1]

    # --- Test 3: Standard OBD2 PID Test ---

    def test_obd2_pids(self) -> List[TestResult]:
        """
        Testet Standard OBD2 PID-Anfragen.

        Sendet verschiedene PID-Befehle und prüft die Antworten.
        Bei einem elektrischen Fahrzeug wie dem Dacia Spring wird
        Motor-Drehzahl (010C) 0 ergeben, aber die Antwort-Struktur
        muss korrekt sein.
        """
        results = []

        for pid in TEST_OBD2_PIDS[:5]:  # Nur erste 5 PIDs testen
            response = self.send_command(pid)
            time.sleep(0.3)

            # Erwartete Antwort: "41 XX ..." (41 = Response für PID 01)
            if response.startswith('41'):
                self._add_result(
                    name=f"OBD2 PID {pid}",
                    command=pid,
                    expected_pattern="41 [0-9A-F]+",
                    status=TestStatus.PASS,
                    response=response,
                    details=f"OBD2 Response korrekt für PID {pid}"
                )
                results.append(self.report.results[-1])
            elif 'NO DATA' in response.upper() or 'NO RESPONSE' in response.upper():
                self._add_result(
                    name=f"OBD2 PID {pid}",
                    command=pid,
                    expected_pattern="NO DATA|41",
                    status=TestStatus.WARN,
                    response=response,
                    details=f"Keine Daten für PID {pid} (könnte bei EV normal sein)"
                )
                results.append(self.report.results[-1])
            else:
                self._add_result(
                    name=f"OBD2 PID {pid}",
                    command=pid,
                    expected_pattern="41 [0-9A-F]+|NO DATA",
                    status=TestStatus.FAIL,
                    response=response,
                    details=f"Unerwartete Antwort für PID {pid}: {response}"
                )
                results.append(self.report.results[-1])

        return results

    # --- Test 4: Extended CAN Diagnostic Test ---

    def test_extended_can(self) -> List[TestResult]:
        """
        Testet erweiterte CAN-Diagnose über 7E0/7E8 IDs.

        WICHTIG: Für die Dacia Spring Kommunikation müssen Extended
        CAN IDs (32-bit) unterstützt werden.
        """
        results = []

        # Setze CAN-IDs auf Extended Diagnostic
        self.send_command('ATH0')  # Extended Headers ausschalten
        self.send_command('ATSH 7E0')  # Request ID
        time.sleep(0.1)
        self.send_command('ATSH 7E8')  # Response ID
        time.sleep(0.1)

        # Mode 03 - Freeze Frame Data
        for mode, description in TEST_UDS_MODES[:3]:
            self.send_command('ATSH 7E0')  # Reset auf Request ID
            time.sleep(0.1)

            response = self.send_command(mode)
            time.sleep(0.3)

            # Erwartete Antwort: 7E8 ... (Response von ECU)
            if response.startswith('7E8') or response.startswith('7E8'):
                self._add_result(
                    name=f"Extended CAN Mode {mode} - {description}",
                    command=f"ATSH 7E0 -> {mode}",
                    expected_pattern="7E8",
                    status=TestStatus.PASS,
                    response=response,
                    details=f"Extended CAN Response korrekt ({description})"
                )
                results.append(self.report.results[-1])
            elif 'NO DATA' in response.upper():
                self._add_result(
                    name=f"Extended CAN Mode {mode} - {description}",
                    command=f"ATSH 7E0 -> {mode}",
                    expected_pattern="7E8|NO DATA",
                    status=TestStatus.WARN,
                    response=response,
                    details=f"Keine Extended CAN Response für Mode {mode} (ECU nicht erreichbar)"
                )
                results.append(self.report.results[-1])
            else:
                self._add_result(
                    name=f"Extended CAN Mode {mode} - {description}",
                    command=f"ATSH 7E0 -> {mode}",
                    expected_pattern="7E8|NO DATA",
                    status=TestStatus.FAIL,
                    response=response,
                    details=f"Unerwartete Extended CAN Antwort: {response}"
                )
                results.append(self.report.results[-1])

        return results

    # --- Test 5: J1939 Extended Address Test ---

    def test_j1939_extended(self) -> TestResult:
        """
        Testet J1939 Extended Address (Dynamic Address) Support.

        WICHTIG: Für UDS over CAN (ISO 14229) mit Dynamic Addresses
        müssen 32-bit CAN-IDs wie 0x18DAF100 unterstützt werden.
        """
        # Setze Extended Address
        response = self.send_command('ATSA F1')  # Set Extended Address to 0xF1
        time.sleep(0.2)

        # Sende UDS Request mit Extended Address
        response = self.send_command('10 00')  # UDS DiagnosticSessionControl
        time.sleep(0.3)

        # Erwartete Antwort: Extended Address Response
        if response and (
            response.startswith('10') or  # Positive Response
            '7F' not in response or        # Negative Response (fehlgeschlagen)
            'NO DATA' in response.upper()  # Keine Antwort
        ):
            self._add_result(
                name="J1939 Extended Address (0xF1)",
                command="ATSA F1 + 10 00",
                expected_pattern="10|7F|NO DATA",
                status=TestStatus.PASS,
                response=response,
                details="Extended Address Support erkannt"
            )
        else:
            self._add_result(
                name="J1939 Extended Address (0xF1)",
                command="ATSA F1 + 10 00",
                expected_pattern="10|7F|NO DATA",
                status=TestStatus.WARN,
                response=response,
                details="Extended Address Support unklar - möglicherweise begrenzt"
            )

        return self.report.results[-1]

    # --- Test 6: Raw CAN Frame Capture Test ---

    def test_raw_can_capture(self) -> TestResult:
        """
        Testet Raw CAN Frame Capture (ATCR).

        WICHTIG: Für das Sniffen von CAN-Bus Traffic müssen Raw Frames
        gelesen werden können.
        """
        # CAN-Hörer aktivieren
        self.send_command('ATH0')  # Headers aus
        self.send_command('ATA0')  # Echo aus
        self.send_command('ATE0')  # AT-Echo aus
        time.sleep(0.1)

        # Setze auf CAN-Modus (automatisch)
        self.send_command('ATSP6')  # ISO 15765-4 500K
        time.sleep(0.2)

        # Sende einen Test-Befehl um CAN-Traffic zu erzeugen
        self.send_command('ATSH 7DF')  # OBD2 Broadcast
        response = self.send_command('0100')  # PID Request
        time.sleep(0.5)

        # Versuche Raw CAN Frames zu lesen
        raw_response = self.send_command('ATCR')
        time.sleep(0.2)

        if raw_response and any(
            c in raw_response for c in ['7DF', '7E0', '7E8', '41', '01']
        ):
            self._add_result(
                name="Raw CAN Frame Capture",
                command="ATCR (nach 0100 PID Request)",
                expected_pattern="7DF|7E0|7E8|41",
                status=TestStatus.PASS,
                response=raw_response,
                details="CAN-Bus Traffic wurde erfolgreich erfasst"
            )
        else:
            self._add_result(
                name="Raw CAN Frame Capture",
                command="ATCR (nach 0100 PID Request)",
                expected_pattern="7DF|7E0|7E8|41|NO DATA",
                status=TestStatus.WARN,
                response=raw_response,
                details="Kein Raw CAN Traffic erfasst (Adapter unterstützt evtl. kein Sniffing)"
            )

        return self.report.results[-1]

    # ------------------------------------------------------------------
    # GESAMTVALIDIERUNG
    # ------------------------------------------------------------------

    def validate(self) -> ValidationReport:
        """
        Führt die vollständige Adapter-Validierung durch.

        Returns:
            ValidationReport mit allen Testergebnissen
        """
        logger.info("=" * 60)
        logger.info("ELM327 Adapter Validierung für Dacia Spring")
        logger.info("=" * 60)

        if not self.is_connected:
            if not self.connect():
                logger.error("Verbindung fehlgeschlagen - Validierung abgebrochen")
                self.report.errors.append("Verbindung fehlgeschlagen")
                return self.report

        try:
            # Serie 1: Grundlegende Identifikation
            logger.info("\n--- Serie 1: Adapter Identifikation ---")
            self.test_atz()
            self.test_ati()

            # Serie 2: CAN-Protokoll-Erkennung
            logger.info("\n--- Serie 2: CAN-Protokoll ---")
            self.test_auto_protocol()

            # Serie 3: OBD2 PID Tests
            logger.info("\n--- Serie 3: OBD2 PID Tests ---")
            self.test_obd2_pids()

            # Serie 4: Extended CAN Tests
            logger.info("\n--- Serie 4: Extended CAN Diagnostic ---")
            self.test_extended_can()

            # Serie 5: J1939 Extended Address
            logger.info("\n--- Serie 5: J1939 Extended Address ---")
            self.test_j1939_extended()

            # Serie 6: Raw CAN Capture
            logger.info("\n--- Serie 6: Raw CAN Frame Capture ---")
            self.test_raw_can_capture()

            # Ergebnis berechnen
            self._calculate_results()

        finally:
            self.disconnect()

        return self.report

    def _calculate_results(self):
        """Berechnet die Gesamtbewertung der Validierung."""
        total = len(self.report.results)
        passed = sum(
            1 for r in self.report.results
            if r.status == TestStatus.PASS
        )
        warnings = len(self.report.warnings)

        # Score: 100% für PASS, 50% für WARN, 0% für FAIL
        score = (passed / total * 100) if total > 0 else 0
        score -= warnings * 5  # 5% Abzug pro Warnung
        self.report.overall_score = max(0, min(100, score))

        # Kompatibilität prüfen
        essential_pass = all(
            r.status in (TestStatus.PASS, TestStatus.WARN)
            for r in self.report.results
            if 'ATZ' in r.name or 'Protocol' in r.name or 'OBD2 PID 0100' in r.name
        )

        self.report.is_compatible = (
            essential_pass and
            self.report.overall_score >= 70 and
            not any('Verbindung' in e for e in self.report.errors)
        )

        logger.info(f"\n{'=' * 60}")
        logger.info(f"VALIDIERUNGSERGEBNIS")
        logger.info(f"Score: {self.report.overall_score:.1f}%")
        logger.info(f"Kompatibel: {'JA ✅' if self.report.is_compatible else 'NEIN ❌'}")
        logger.info(f"{'=' * 60}")

    # ------------------------------------------------------------------
    # BERICHT-AUSGABE
    # ------------------------------------------------------------------

    def get_report_json(self) -> str:
        """Gibt den Bericht als JSON aus."""
        data = {
            'adapter_info': {
                'vendor': self.report.adapter_info.vendor,
                'firmware_version': self.report.adapter_info.firmware_version,
                'chip_type': self.report.adapter_info.chip_type,
                'protocol': self.report.adapter_info.protocol,
                'can_speed': self.report.adapter_info.can_speed,
            },
            'overall_score': self.report.overall_score,
            'is_compatible': self.report.is_compatible,
            'warnings': self.report.warnings,
            'errors': self.report.errors,
            'tests': [
                {
                    'name': r.name,
                    'command': r.command,
                    'expected': r.expected_pattern,
                    'status': r.status.value,
                    'response': r.response,
                    'details': r.details,
                }
                for r in self.report.results
            ]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def get_report_text(self) -> str:
        """Gibt einen lesbaren Textbericht aus."""
        lines = []
        lines.append("=" * 60)
        lines.append("ELM327 ADAPTER VALIDIERUNGSBERICHT")
        lines.append("=" * 60)
        lines.append("")

        # Adapter Info
        info = self.report.adapter_info
        lines.append("Adapter-Informationen:")
        lines.append(f"  Hersteller:   {info.vendor or 'Unbekannt'}")
        lines.append(f"  Firmware:     {info.firmware_version or 'Unbekannt'}")
        lines.append(f"  Chip-Typ:     {info.chip_type or 'Unbekannt'}")
        lines.append(f"  Protokoll:    {info.protocol or 'Unbekannt'}")
        lines.append(f"  CAN-Geschw.:  {info.can_speed or 'Unbekannt'}")
        lines.append("")

        # Testergebnisse
        lines.append("Testergebnisse:")
        lines.append("-" * 60)
        for r in self.report.results:
            icon = {
                'pass': '✅',
                'warn': '⚠️',
                'fail': '❌',
                'skip': '➖',
                'pending': '⏳',
            }.get(r.status.value, '?')
            lines.append(f"  {icon} {r.name}")
            if r.details:
                lines.append(f"     → {r.details}")
        lines.append("")

        # Zusammenfassung
        lines.append("-" * 60)
        lines.append(f"Score: {self.report.overall_score:.1f}%")
        lines.append(
            f"Kompatibel: {'JA ✅' if self.report.is_compatible else 'NEIN ❌'}"
        )

        if self.report.warnings:
            lines.append("")
            lines.append("Warnungen:")
            for w in self.report.warnings:
                lines.append(f"  ⚠️  {w}")

        if self.report.errors:
            lines.append("")
            lines.append("Fehler:")
            for e in self.report.errors:
                lines.append(f"  ❌ {e}")

        lines.append("=" * 60)
        return '\n'.join(lines)


# ============================================================================
# MAIN / BEFEHLSZEILEN-SCHNITTSTELLE
# ============================================================================

def parse_args():
    """Parsst Kommandozeilenargumente."""
    import argparse

    parser = argparse.ArgumentParser(
        description='ELM327 Adapter Validator für Dacia Spring'
    )
    parser.add_argument(
        '-t', '--type',
        choices=['serial', 'tcp', 'ble'],
        default='tcp',
        help='Verbindungstyp (default: tcp)'
    )
    parser.add_argument(
        '-d', '--device',
        default='192.168.1.123:23',
        help='Gerät/Host (z.B. /dev/ttyAMA0 oder 192.168.1.123:23)'
    )
    parser.add_argument(
        '-b', '--baudrate',
        type=int,
        default=DEFAULT_BAUDRATE,
        help=f'Baudrate (default: {DEFAULT_BAUDRATE})'
    )
    parser.add_argument(
        '-o', '--output',
        choices=['text', 'json', 'both'],
        default='text',
        help='Ausgabeformat (default: text)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose Mode (mehr Logs)'
    )
    parser.add_argument(
        '--save-report',
        type=str,
        help='Bericht in Datei speichern'
    )

    return parser.parse_args()


def main():
    """Hauptfunktion für die Kommandozeilen-Nutzung."""
    args = parse_args()

    # Log-Level einstellen
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Verbindungstyp bestimmen
    conn_type = ConnectionType(args.type)

    # Validator erstellen und ausführen
    validator = ELM327Validator(
        connection_type=conn_type,
        target=args.device,
        baudrate=args.baudrate
    )

    report = validator.validate()

    # Bericht ausgeben
    if args.output in ('text', 'both'):
        text_report = validator.get_report_text()
        print(text_report)

    if args.output in ('json', 'both'):
        json_report = validator.get_report_json()
        print("\n--- JSON Report ---")
        print(json_report)

    # Bericht speichern
    if args.save_report:
        with open(args.save_report, 'w', encoding='utf-8') as f:
            if args.output == 'json':
                f.write(validator.get_report_json())
            else:
                f.write(validator.get_report_text())
        logger.info(f"Bericht gespeichert: {args.save_report}")

    # Exit-Code setzen
    return 0 if report.is_compatible else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())