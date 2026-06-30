#!/usr/bin/env python3
"""
vGate iCar Pro Bluetooth Classic RFCOMM Client für Dacia Spring.

Verbindet sich über Bluetooth Classic RFCOMM (SPP) mit dem vGate iCar Pro,
genau wie CanZE App es tut. Liest Raw CAN-Daten und leitet sie an Android-Apps weiter.

CanZE Protocol-Analyse (von fesche/CanZE):
- UUID: 00001101-0000-1000-8000-00805F9B34FB (SPP - Serial Port Profile)
- CAN IDs: 7ec (BCB/EMM), 7bb (LBC), 765 (UCH), 776 (DCDC)
- Speed PID: 222003 (Vehicle Speed)
- Throttle PID: 22202E (Accelerator Pedal Position)
- Motor Speed PID: 223045

Author: Dacia Spring Team
"""
import bluetooth
import threading
import time
import logging
import sys
import socket
from datetime import datetime

# ============ KONFIGURATION ============
# MAC-Adresse des vGate iCar Pro (über bluetoothctl list finden)
VGLITE_MAC = "D2:E0:2F:8D:61:07"  # <-- MAC-Adresse anpassen!
VGLITE_PORT = 1  # RFCOMM Channel für SPP ist immer 1

# SPP UUID (Bluetooth Serial Port Profile)
SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"

# ELM327 Initialisierung
ELM_INIT_SEQ = [
    "ATZ",      # Reset
    "ATE0",     # Echo aus
    "ATH0",     # Headers aus
    "ATS0",     # Spaces aus
    "ATSP0",    # Auto-Protocol
]

# ============ LOGGER ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("vGate-BT-RFCOMM")


class OBD2Data:
    """Hält alle aktuellen OBD2-Daten."""
    def __init__(self):
        self.speed = 0.0
        self.rpm = 0.0
        self.throttle = 0.0
        self.engine_load = 0.0
        self.coolant_temp = 0.0
        self.battery_soc = 0.0
        self.motor_speed = 0.0
        self.raw_response = ""
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "speed": self.speed,
            "rpm": self.rpm,
            "throttle": self.throttle,
            "engine_load": self.engine_load,
            "coolant_temp": self.coolant_temp,
            "battery_soc": self.battery_soc,
            "motor_speed": self.motor_speed,
            "timestamp": self.timestamp.isoformat()
        }

    def __str__(self):
        return (f"Speed={self.speed:.1f} km/h | Throttle={self.throttle:.1f}% | "
                f"RPM={self.rpm:.0f} | Motor={self.motor_speed:.0f} rpm | SOC={self.battery_soc:.1f}%")


class VGateBTClient:
    """
    Bluetooth Classic RFCOMM Client für vGate iCar Pro.
    
    Verbindet sich über SPP (Serial Port Profile) mit dem Adapter
    und liest Raw CAN-Daten aus.
    """
    
    def __init__(self, mac: str = VGLITE_MAC, port: int = VGLITE_PORT, debug: bool = False):
        self.mac = mac
        self.port = port
        self.debug = debug
        self.obd_data = OBD2Data()
        
        self.sock = None
        self.running = False
        self.receive_thread = None
        
        # Statistik
        self.stats = {
            "bytes_received": 0,
            "commands_sent": 0,
            "errors": 0,
            "connect_attempts": 0
        }
    
    def connect(self) -> bool:
        """Verbindet sich über Bluetooth Classic RFCOMM SPP."""
        try:
            self.stats["connect_attempts"] += 1
            logger.info(f"Scanne nach vGate iCar Pro bei {self.mac}...")
            
            # Prüfen ob Gerät gepairt ist
            logger.info(f"Verbinde zu {self.mac} auf RFCOMM Channel {self.port}...")
            
            self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.sock.settimeout(10.0)
            self.sock.connect((self.mac, self.port))
            
            logger.info(f"✅ Bluetooth Classic RFCOMM verbunden!")
            self.running = True
            
            # Initialisierungssequenz
            return self._init_elm327()
            
        except Exception as e:
            logger.error(f"❌ Bluetooth Verbindung fehlgeschlagen: {e}")
            logger.error("Prüfe:")
            logger.error("  1. vGate iCar Pro eingesteckt und gebootet?")
            logger.error("  2. MAC-Adresse in vgate_bt_rfcomm.py anpassen!")
            logger.error("  3. Mit bluetoothctl pairing prüfen: 'paired-devices'")
            return False
    
    def _init_elm327(self) -> bool:
        """Sendet ELM327 Initialisierungsbefehle."""
        logger.info("Sende ELM327 Initialisierung über SPP...")
        
        for cmd in ELM_INIT_SEQ:
            try:
                resp = self._send_command(cmd, timeout=3.0)
                logger.info(f"  {cmd:6s} → {resp.strip()}")
            except Exception as e:
                logger.warning(f"  {cmd:6s} → ERROR: {e}")
        
        return True
    
    def _send_command(self, cmd: str, timeout: float = 5.0) -> str:
        """Sendet einen Befehl über RFCOMM SPP."""
        if not self.sock:
            raise bluetooth.BluetoothError("Socket nicht verbunden")
        
        # Befehl senden
        self.sock.sendall(f"{cmd}\r\n".encode())
        self.stats["commands_sent"] += 1
        
        # Antwort lesen
        self.sock.settimeout(timeout)
        response = b""
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                # Timeout wenn keine neuen Daten
                self.sock.settimeout(1.0)
                try:
                    while True:
                        extra = self.sock.recv(4096)
                        if not extra:
                            break
                        response += extra
                        self.sock.settimeout(0.5)
                except:
                    pass
                break
        except Exception as e:
            if self.debug:
                logger.debug(f"Lesefehler: {e}")
        finally:
            self.sock.settimeout(10.0)
        
        self.stats["bytes_received"] += len(response)
        return response.decode('ascii', errors='ignore')
    
    def parse_can_response(self, raw: str) -> str:
        """
        Parst eine ELM327/CAN-Antwort und extrahiert die Felder.
        
        Basierend auf CanZE Field-Definitionen.
        """
        raw = raw.replace("\r", "").replace("\n", "").strip()
        
        if not raw or raw.startswith("NO DATA") or raw == ">":
            return ""
        
        # UDC ReadDataByIdentifier (22 XXXX → 62 XXXX)
        if raw.startswith("62") or raw.startswith("22"):
            return self._parse_can_raw(raw)
        
        # Standard OBD2 (41 XX YY ZZ)
        if raw.startswith("41"):
            return self._parse_obd2(raw)
        
        return ""
    
    def _parse_can_raw(self, raw: str) -> str:
        """Parst Raw CAN-Frames basierend auf CanZE Field-Definitionen."""
        try:
            hex_data = raw.replace("62", "").replace("22", "").replace(" ", "").strip()
            if not hex_data:
                return ""
            
            # Throttle (PID 22 20 2E)
            if "22202E" in raw.lower():
                idx = raw.lower().find("22202e")
                if idx >= 0 and len(raw) > idx + 14:
                    # Daten nach 22 20 2E
                    value_hex = raw[idx+8:idx+10] if len(raw) > idx+10 else ""
                    if value_hex:
                        raw_val = int(value_hex, 16)
                        # CanZE: resolution=0.00125, offset=0
                        self.obd_data.throttle = raw_val * 0.00125 * 100  # %
            
            # Battery SOC (PID 22 90 01)
            if "229001" in raw.lower():
                idx = raw.lower().find("229001")
                if idx >= 0 and len(raw) > idx + 14:
                    value_hex = raw[idx+8:idx+10]
                    if value_hex:
                        raw_val = int(value_hex, 16)
                        # CanZE: resolution=0.5, offset=6
                        self.obd_data.battery_soc = raw_val * 0.5 + 6
            
            # Vehicle Speed (PID 22 20 03)
            if "222003" in raw.lower():
                idx = raw.lower().find("222003")
                if idx >= 0 and len(raw) > idx + 14:
                    value_hex = raw[idx+8:idx+12]
                    if len(value_hex) >= 2:
                        raw_val = int(value_hex[:2], 16)
                        # CanZE: resolution=0.01, offset=0
                        self.obd_data.speed = raw_val * 0.01
                
        except (ValueError, IndexError) as e:
            if self.debug:
                logger.debug(f"CAN Parse-Fehler: {e}, Raw: {raw}")
        
        return raw
    
    def _parse_obd2(self, raw: str) -> str:
        """Parst standard OBD2 Response (41 XX YY ZZ)."""
        try:
            # Speed (41 0D)
            if "410D" in raw:
                idx = raw.find("410D")
                if idx >= 0 and len(raw) > idx + 4:
                    speed_hex = raw[idx+4:idx+6]
                    if speed_hex:
                        self.obd_data.speed = float(int(speed_hex, 16))
            
            # RPM (41 0C)
            if "410C" in raw:
                idx = raw.find("410C")
                if idx >= 0 and len(raw) > idx + 8:
                    a = int(raw[idx+4:idx+6], 16)
                    b = int(raw[idx+6:idx+8], 16)
                    self.obd_data.rpm = (a * 256 + b) / 4.0
                
        except (ValueError, IndexError) as e:
            if self.debug:
                logger.debug(f"OBD2 Parse-Fehler: {e}, Raw: {raw}")
        
        return raw
    
    def read_speed(self) -> float:
        """Liest aktuelle Speed über CanZE PID 22 20 03."""
        try:
            resp = self._send_command("222003", timeout=3.0)
            self.parse_can_response(resp)
            return self.obd_data.speed
        except Exception as e:
            logger.warning(f"Speed-Lesefehler: {e}")
            return 0.0
    
    def read_throttle(self) -> float:
        """Liest Pedal-Position über CanZE PID 22 20 2E."""
        try:
            resp = self._send_command("22202E", timeout=3.0)
            self.parse_can_response(resp)
            return self.obd_data.throttle
        except Exception as e:
            logger.warning(f"Throttle-Lesefehler: {e}")
            return 0.0
    
    def read_motor_speed(self) -> float:
        """Liest Motor-RPM über CanZE PID 22 30 45."""
        try:
            resp = self._send_command("223045", timeout=3.0)
            self.parse_can_response(resp)
            return self.obd_data.motor_speed
        except Exception as e:
            logger.warning(f"Motor-Speed-Lesefehler: {e}")
            return 0.0
    
    def read_soc(self) -> float:
        """Liest Battery SOC über CanZE PID 22 90 01."""
        try:
            resp = self._send_command("229001", timeout=3.0)
            self.parse_can_response(resp)
            return self.obd_data.battery_soc
        except Exception as e:
            logger.warning(f"SOC-Lesefehler: {e}")
            return 0.0
    
    def read_all(self) -> OBD2Data:
        """Liest alle verfügbaren Daten."""
        pids = [
            ("222003", "Vehicle Speed"),
            ("22202E", "Throttle"),
            ("223045", "Motor Speed"),
            ("229001", "Battery SOC"),
            ("222002", "HV Battery SOC"),
            ("222005", "14V Battery Voltage"),
        ]
        
        for pid, name in pids:
            try:
                resp = self._send_command(pid, timeout=3.0)
                self.parse_can_response(resp)
                if self.debug:
                    logger.debug(f"  {name:20s} ({pid}): {resp.strip()}")
            except Exception as e:
                if self.debug:
                    logger.debug(f"  {name:20s} ({pid}): ERROR {e}")
        
        self.obd_data.timestamp = datetime.now()
        return self.obd_data
    
    def start_continuous_read(self, interval: float = 0.5):
        """Startet kontinuierliches Lesen der CAN-Daten."""
        self.running = True
        self.receive_thread = threading.Thread(target=self._read_loop, args=(interval,), daemon=True)
        self.receive_thread.start()
        logger.info(f"📡 Continuous-Read Loop gestartet (Interval: {interval}s)")
    
    def _read_loop(self, interval: float):
        """Hauptschleife zum kontinuierlichen Lesen."""
        while self.running:
            try:
                self.read_all()
            except Exception as e:
                logger.error(f"Read-Loop-Fehler: {e}")
                self.stats["errors"] += 1
            time.sleep(interval)
    
    def disconnect(self):
        """Trennt die Bluetooth-Verbindung."""
        self.running = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        
        logger.info("❌ Bluetooth RFCOMM getrennt")
    
    def get_stats(self) -> dict:
        """Gibt Verbindungs-Statistik zurück."""
        return {
            **self.stats,
            "obd_data": self.obd_data.to_dict()
        }


class OBD2TCPServer:
    """
    ELM327 TCP Server der die CAN-Daten vom vGate iCar Pro
    an Android-Apps weiterleitet.
    """
    
    def __init__(self, bt_client: VGateBTClient, host: str = "0.0.0.0", port: int = 2117):
        self.bt_client = bt_client
        self.host = host
        self.port = port
        self.server_sock = None
        self.clients = []
        self.running = False
        self.broadcast_thread = None
    
    def start(self):
        """Startet den TCP Server."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self.server_sock.settimeout(1.0)
        
        self.running = True
        logger.info(f"🚀 OBD2 TCP Server gestartet auf {self.host}:{self.port}")
        
        # Broadcast-Thread starten
        self.broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.broadcast_thread.start()
    
    def _broadcast_loop(self):
        """Broadcast-Loop für neue Daten."""
        last_data = ""
        
        while self.running:
            try:
                # Neue Clients akzeptieren
                try:
                    client_sock, addr = self.server_sock.accept()
                    logger.info(f"📱 Neuer Client: {addr}")
                    self.clients.append(client_sock)
                except socket.timeout:
                    pass
                
                # Clients verarbeiten
                clients_to_remove = []
                for client_sock in self.clients[:]:
                    try:
                        client_sock.settimeout(0.1)
                        data = client_sock.recv(1024)
                        if data:
                            self._handle_command(client_sock, data)
                        else:
                            clients_to_remove.append(client_sock)
                    except socket.timeout:
                        pass
                    except Exception as e:
                        clients_to_remove.append(client_sock)
                
                for c in clients_to_remove:
                    if c in self.clients:
                        self.clients.remove(c)
                    try:
                        c.close()
                    except:
                        pass
                    logger.info("👋 Client getrennt")
                
                # Daten broadcasten
                if self.clients:
                    data_str = str(self.bt_client.obd_data)
                    if data_str != last_data:
                        last_data = data_str
                        for client_sock in self.clients[:]:
                            try:
                                msg = f"[DATA] {data_str}\r\n"
                                client_sock.sendall(msg.encode())
                            except:
                                pass
                
            except Exception as e:
                if self.running:
                    logger.error(f"Broadcast-Loop-Fehler: {e}")
            time.sleep(0.2)
    
    def _handle_command(self, client_sock: socket.socket, data: bytes):
        """Verarbeitet OBD2-Befehle von Android-Apps."""
        cmd = data.decode('ascii', errors='ignore').strip().replace("\r", "").replace("\n", "")
        
        if not cmd:
            return
        
        logger.info(f"📱 Client-Befehl: {cmd}")
        
        try:
            if cmd == "ATZ":
                resp = "vGate iCar Pro CAN-Sniffer (RFCOMM)\r\nReady\r\n> "
            elif cmd in ("ATE0", "ATH0", "ATS0", "ATSP0"):
                resp = "OK\r\n> "
            elif cmd == "0100":
                resp = "41 00 98 18 00 00\r\n> "
            elif cmd == "010D":
                speed = self.bt_client.read_speed()
                resp = f"41 0D {int(speed):02X}\r\n> "
            elif cmd == "010C":
                rpm = self.bt_client.read_motor_speed()
                value = int(rpm) * 4
                a = (value >> 8) & 0xFF
                b = value & 0xFF
                resp = f"41 0C {a:02X} {b:02X}\r\n> "
            elif cmd == "22202E":
                throttle = self.bt_client.read_throttle()
                raw_val = int(throttle / 0.00125)
                resp = f"62 20 2E {raw_val:02X}\r\n> "
            else:
                # Generic
                raw_resp = self.bt_client._send_command(cmd, timeout=3.0)
                resp = raw_resp + "\r\n> "
            
            client_sock.sendall(resp.encode())
            
        except Exception as e:
            logger.warning(f"Command-Fehler: {e}")
            client_sock.sendall(f"ERROR\r\n> ".encode())
    
    def stop(self):
        """Stoppt den TCP Server."""
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass


def main():
    """Hauptfunktion."""
    print("=" * 60)
    print("vGate iCar Pro Bluetooth RFCOMM Client")
    print("Basierend auf CanZE Protocol-Analyse (fesche/CanZE)")
    print("=" * 60)
    
    print(f"\n📡 MAC-Adresse: {VGLITE_MAC}")
    print(f"📡 RFCOMM Channel: {VGLITE_PORT}")
    print(f"📡 SPP UUID: {SPP_UUID}")
    
    # Client erstellen
    client = VGateBTClient(debug=True)
    
    # Verbinden
    if not client.connect():
        logger.error("Verbindung fehlgeschlagen!")
        sys.exit(1)
    
    # Daten lesen
    logger.info("\nLese alle CAN-Daten...")
    data = client.read_all()
    print(f"\n📊 OBD2-Daten: {data}")
    
    # Test
    logger.info("\n--- Einzeldaten-Tests ---")
    logger.info(f"Speed:     {client.read_speed():.2f} km/h")
    logger.info(f"Throttle:  {client.read_throttle():.2f} %")
    logger.info(f"Motor:     {client.read_motor_speed():.0f} rpm")
    logger.info(f"SOC:       {client.read_soc():.1f} %")
    
    print(f"\n📊 Ergebnis: {client.obd_data}")
    
    # TCP Server starten
    print("\n⚠️  TCP Server wird gestartet auf Port 2117...")
    print("   Drücken Sie STRG+C zum Beenden\n")
    
    try:
        # Server starten
        tcp_server = OBD2TCPServer(client, port=2117)
        tcp_server.start()
        
        # Continuous-Read starten
        client.start_continuous_read(interval=0.5)
        
        # Hauptschleife
        while True:
            time.sleep(5.0)
            stats = client.get_stats()
            print(f"\n📊 Stats: RX={stats['bytes_received']}B "
                  f"TX={stats['commands_sent']} "
                  f"Err={stats['errors']}")
            print(f"   OBD2: {client.obd_data}")
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Benutzerabbruch")
    finally:
        client.disconnect()
        print("\n✅ Beendet")


if __name__ == "__main__":
    import socket
    main()