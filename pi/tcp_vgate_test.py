#!/usr/bin/env python3
"""
TCP Test — Prüft ob vGate iCar Pro über WiFi erreichbar ist.

vGate iCar Pro VK1032 unterstützt WiFi TCP auf Port 5555!
CanZE Plus verwendet wahrscheinlich WiFi, nicht BLE.
"""
import socket
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("TCP-Vlink-Test")


def scan_wifi_network():
    """Scannt das WiFi-Netzwerk nach vGate-Geräten."""
    logger.info("\n" + "=" * 60)
    logger.info("WIFI NETZWERK SCAN")
    logger.info("=" * 60)
    
    import os
    # Aktuelle IP des Pi
    result = os.popen("hostname -I").read()
    logger.info(f"  Pi IP: {result.strip()}")
    
    # Netzmasken-Ermittlung
    result = os.popen("ip route").read()
    logger.info(f"  Route: {result.strip()}")
    
    # Alle verbundenen WiFi-Geräte
    result = os.popen("iwctl station wlan0 get-networks").read()
    logger.info(f"  WiFi Netzwerke: {result.strip()}")


def try_vgate_connection(ip: str, port: int = 5555, timeout: float = 2.0) -> bool:
    """Versucht Verbindung zum vGate iCar Pro."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        logger.info(f"\n  ✅ VERBUNDEN: {ip}:{port}")
        
        # ELM327 Command senden
        cmd = b"ATZ\r"
        s.send(cmd)
        logger.info(f"  Gesendet: {cmd}")
        
        response = s.recv(1024)
        if response:
            logger.info(f"  Empfangen: {response}")
        else:
            logger.info(f"  Kein Antwort")
        
        s.close()
        return True
        
    except socket.timeout:
        logger.info(f"  ⏱️  Timeout: {ip}:{port}")
        return False
    except ConnectionRefusedError:
        logger.info(f"  ❌ Connection refused: {ip}:{port}")
        return False
    except Exception as e:
        logger.info(f"  ❌ Fehler: {ip}:{port} — {e}")
        return False


def try_vgate_on_network():
    """Scannt das lokale Netz nach vGate-Geräten."""
    logger.info("\n" + "=" * 60)
    logger.info("VGLITE iCAR PRO WIFII SCAN (Port 5555)")
    logger.info("=" * 60)
    
    import os
    # Netz ermitteln
    result = os.popen("ip route | grep default").read()
    logger.info(f"  Route: {result.strip()}")
    
    # IP des Pi ermitteln
    pi_ip = os.popen("hostname -I").read().strip()
    if pi_ip:
        base_ip = '.'.join(pi_ip.split('.')[:3])  # 192.168.178.x
        logger.info(f"  Basis-IP: {base_ip}")
        
        # Scanne letztes Octet (1-50)
        found = []
        for i in range(1, 51):
            ip = f"{base_ip}.{i}"
            if try_vgate_connection(ip, port=5555, timeout=0.5):
                found.append(ip)
        
        if found:
            logger.info(f"\n  🎯 GEFUNDENE VGLITE GERäte: {found}")
        else:
            logger.info(f"\n  ⚠️  KEIN vGate iCar Pro über WiFi gefunden!")
            logger.info(f"  → vGate iCar Pro ist NICHT im gleichen Netz!")


def try_vgate_bt_tcp():
    """Versucht TCP direkt über die MAC-Adresse (BlueZ bt-tcp)."""
    logger.info("\n" + "=" * 60)
    logger.info("BLUETOOTH TCP TEST (bt-tcp)")
    logger.info("=" * 60)
    
    import os
    
    # Prüfe ob bt-tcp Device existiert
    result = os.popen("ip addr show bt-tcp 2>&1").read()
    logger.info(f"  bt-tcp: {result.strip()}")
    
    # Versuche bt-tcp Verbindung
    for mac in ["13:E0:2F:8D:61:07", "D2:E0:2F:8D:61:07"]:
        try:
            cmd = f"sudo bt-tcp {mac} 5555"
            logger.info(f"\n  Versuch: bt-tcp {mac}")
            result = os.popen(cmd).read()
            logger.info(f"  Ergebnis: {result.strip()}")
        except Exception as e:
            logger.info(f"  bt-tcp nicht verfügbar: {e}")


async def main():
    print("=" * 60)
    print("VGLITE iCAR PRO WIFII/BT-TCP TEST")
    print("=" * 60)
    print(f"\n⏰ Start: {datetime.now()}")
    print("=" * 60)
    
    # 1. WiFi-Netzwerk scan
    scan_wifi_network()
    
    # 2. WiFi TCP Test
    try_vgate_on_network()
    
    # 3. Bluetooth TCP Test
    try_vgate_bt_tcp()
    
    print(f"\n⏰ Ende: {datetime.now()}")
    print("\n✅ Test abgeschlossen!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())