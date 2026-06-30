#!/usr/bin/env python3
"""
Data Pipeline - Verbindet BLE Client + RPM Engine + TCP Server

Sammelt echte OBD2-Daten vom Vgate iCar Pro via BLE,
berechnet simulierte RPM basierend auf Speed und versorgt
den ELM327 TCP Server mit den Daten.

Nutzung:
    python3 obd2_data_pipeline.py
    
Oder als Modul:
    from obd2_data_pipeline import DataPipeline
    pipeline = DataPipeline()
    await pipeline.start()
    rpm = await pipeline.get_rpm()
    await pipeline.stop()
"""

import asyncio
import sys
import logging
import time
from typing import Optional

# Importiere lokale Module
try:
    from rpm_simulation_engine import RPMSimulationEngine, DriveState
except ImportError:
    print("❌ rpm_simulation_engine.py nicht gefunden!")
    sys.exit(1)

# bleak für BLE (wird später geladen, um Import-Fehler zu vermeiden)
bleak_available = False
try:
    from bleak import BleakScanner
    bleak_available = True
except ImportError:
    pass

# Logging
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("data_pipeline")


# ========================
# DataPipeline Klasse
# ========================

class DataPipeline:
    """
    Hauptklasse die alle Komponenten verbindet:
    
    Vgate BLE → OBD2 Daten → RPM Engine → Simulierte RPM
    """
    
    def __init__(self, vgate_mac: Optional[str] = None, use_fake_data: bool = True):
        """
        Initialisiert die Data Pipeline.
        
        Args:
            vgate_mac: BLE MAC Adresse des Vgate Adapters (wenn vorhanden)
            use_fake_data: True = simulierte Daten wenn kein Vgate (Fallback)
        """
        self.vgate_mac = vgate_mac
        self.use_fake_data = use_fake_data
        
        # RPM Engine
        self.rpm_engine = RPMSimulationEngine()
        
        # BLE Client (wird lazy geladen)
        self.ble_client = None
        self._ble_client_class = None
        
        # Steuerungsvariablen
        self._running = False
        self._pipeline_task: Optional[asyncio.Task] = None
        
        # Aktuelle Daten
        self._speed = 0.0
        self._rpm = 850.0
        self._gear = "P"
        self._drive_state = DriveState.IDLE
        self._has_real_data = False
        
        # Fallback Timer
        self._last_real_data = time.time()
        self._real_data_timeout = 10.0  # Sekunden bis Fallback aktiv
        
        # Statistiken
        self._total_updates = 0
        self._ble_errors = 0
        self._fallback_activations = 0
        
        logger.info(f"🔧 Data Pipeline initialisiert (Fake-Data: {use_fake_data})")
    
    def _ensure_ble_client(self):
        """Stellt sicher dass BLE Client geladen und initialisiert ist."""
        if self.ble_client is None and bleak_available and self.vgate_mac:
            try:
                from ble_client_vgate import VgateBLEClient
                self._ble_client_class = VgateBLEClient
                self.ble_client = VgateBLEClient(self.vgate_mac)
                
                # Data Callback
                self.ble_client.on_data(self._on_obd2_data)
                
                logger.info(f"📡 BLE Client für {self.vgate_mac} initialisiert")
            except Exception as e:
                logger.error(f"❌ BLE Client Initialisierung fehlgeschlagen: {e}")
                self.ble_client = None
    
    async def start(self):
        """
        Startet die Data Pipeline.
        
        Verbindet sich zum Vgate (wenn MAC vorhanden) und beginnt
        mit dem Sammeln von OBD2-Daten.
        """
        if self._running:
            logger.warning("Pipeline läuft bereits")
            return
        
        self._running = True
        
        # BLE Client vorbereiten
        if self.vgate_mac and bleak_available:
            self._ensure_ble_client()
            if self.ble_client:
                try:
                    logger.info("🚀 Starte BLE Verbindung zu Vgate...")
                    await self.ble_client.start()
                except Exception as e:
                    logger.error(f"❌ BLE Start fehlgeschlagen: {e}")
                    self.ble_client = None
        else:
            if not bleak_available:
                logger.warning("⚠️  bleak nicht verfügbar → Verwende Fake-Data")
            elif not self.vgate_mac:
                logger.warning("⚠️  Keine MAC angegeben → Verwende Fake-Data")
            else:
                logger.warning("⚠️  BLE nicht konfiguriert → Verwende Fake-Data")
        
        # Pipeline Task starten
        self._pipeline_task = asyncio.create_task(self._pipeline_loop())
        
        logger.info("✅ Data Pipeline gestartet")
    
    async def stop(self):
        """Stoppt die Data Pipeline."""
        self._running = False
        
        if self._pipeline_task and not self._pipeline_task.done():
            self._pipeline_task.cancel()
        
        if self.ble_client:
            await self.ble_client.stop()
        
        logger.info("🔌 Data Pipeline gestoppt")
    
    async def _pipeline_loop(self):
        """Hauptschleife der Data Pipeline."""
        update_interval = 0.1  # 100ms
        
        while self._running:
            try:
                # Prüfen ob wir echte Daten haben
                now = time.time()
                time_since_real = now - self._last_real_data
                
                if self._has_real_data and time_since_real > self._real_data_timeout:
                    # Keine realen Daten mehr → Fallback
                    self._has_real_data = False
                    self._fallback_activations += 1
                    logger.info("⚠️  Keine realen Daten mehr → Fallback auf simulierte Daten")
                
                if self._has_real_data and self.ble_client:
                    # Echte Daten vom BLE Client verwenden
                    obd_data = await self.ble_client.get_obd_data()
                    speed = obd_data.speed
                    
                    # RPM Engine aktualisieren
                    self._rpm = self.rpm_engine.update(speed)
                    self._speed = speed
                    self._gear = self.rpm_engine.get_state().gear
                    self._drive_state = self.rpm_engine.get_state().drive_state
                    self._total_updates += 1
                    
                    # Logging für wichtige Änderungen
                    if self._total_updates % 20 == 0:
                        logger.info(f"📊 Speed: {speed:4.1f} km/h | RPM: {self._rpm:5.0f} | "
                                   f"Gang: {self._gear} | Zustand: {self._drive_state.value}")
                
                else:
                    # Fallback: Simuliere Speed (langsames Auslaufen)
                    if self._speed > 0:
                        self._speed = max(0, self._speed - 2.0)  # -2 km/h pro Sekunde
                    self._rpm = self.rpm_engine.update(self._speed, 0)
                    self._gear = self.rpm_engine.get_state().gear
                    self._drive_state = self.rpm_engine.get_state().drive_state
                
                await asyncio.sleep(update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Pipeline-Fehler: {e}")
                self._ble_errors += 1
                await asyncio.sleep(1)
    
    async def _on_obd2_data(self, obd_data):
        """Callback wenn neue OBD2-Daten vom BLE Client kommen."""
        self._last_real_data = time.time()
        self._has_real_data = True
        self._speed = obd_data.speed
    
    # ---- Öffentliche Accessoren ----
    
    async def get_rpm(self) -> float:
        """Gibt aktuelle RPM zurück (real oder simuliert)."""
        return self._rpm
    
    async def get_speed(self) -> float:
        """Gibt aktuelle Speed zurück."""
        return self._speed
    
    async def get_gear(self) -> str:
        """Gibt aktuellen Gang zurück."""
        return self._gear
    
    async def get_drive_state(self) -> DriveState:
        """Gibt aktuellen Fahrzustand zurück."""
        return self._drive_state
    
    async def get_supported_pids(self) -> str:
        """Gibt Supported PIDs Bitmap zurück."""
        return self.rpm_engine.get_supported_pids()
    
    def get_stats(self) -> dict:
        """Gibt Pipeline-Statistiken zurück."""
        return {
            "running": self._running,
            "has_real_data": self._has_real_data,
            "speed": self._speed,
            "rpm": self._rpm,
            "gear": self._gear,
            "drive_state": self._drive_state.value,
            "total_updates": self._total_updates,
            "ble_errors": self._ble_errors,
            "fallback_activations": self._fallback_activations,
        }


# ========================
# Hilfsfunktion für TCP Server Integration
# ========================

class ELM327DataInjector:
    """
    Injektor der echte Daten vom Pipeline in den ELM327 TCP Server einbindet.
    
    Wird vom TCP Server genutzt um echte RPM/Speed statt simulierten Daten zu senden.
    """
    
    def __init__(self, pipeline: DataPipeline):
        self.pipeline = pipeline
        self.enabled = False
    
    async def get_rpm_for_pid_0c(self) -> str:
        """
        Gibt RPM Antwort für OBD2 PID 010C zurück.
        
        Format: "41 0C XX XX" (wie vom ELM327 Standard)
        """
        rpm = await self.pipeline.get_rpm()
        value = int(rpm) * 4  # RPM * 4 = Wert
        
        a = (value >> 8) & 0xFF  # High Byte
        b = value & 0xFF          # Low Byte
        
        return f"41 0C {a:02X} {b:02X}"
    
    async def get_speed_for_pid_0d(self) -> str:
        """
        Gibt Speed Antwort für OBD2 PID 010D zurück.
        
        Format: "41 0D XX" (Speed in km/h)
        """
        speed = await self.pipeline.get_speed()
        return f"41 0D {int(speed):02X}"
    
    async def get_supported_pids_response(self) -> str:
        """Gibt Antwort für PID 0100 zurück."""
        pids = await self.pipeline.get_supported_pids()
        return f"41 00 {pids}"
    
    def enable(self):
        self.enabled = True
        logger.info("📡 ELM327 Data Injector aktiviert")
    
    def disable(self):
        self.enabled = False
        logger.info("📡 ELM327 Data Injector deaktiviert")


# ========================
# Hauptprogramm / Test
# ========================

async def main_test():
    """Test-Hauptprogramm."""
    print("=" * 60)
    print("Data Pipeline Test")
    print("=" * 60)
    
    # Ohne BLE (Fake-Data)
    pipeline = DataPipeline(use_fake_data=True)
    await pipeline.start()
    
    print("\n⏱️  Läuft für 15 Sekunden mit Fake-Data...")
    try:
        for i in range(30):
            stats = pipeline.get_stats()
            print(f"  Speed: {stats['speed']:4.1f} km/h | "
                  f"RPM: {stats['rpm']:5.0f} | "
                  f"Zustand: {stats['drive_state']}")
            await asyncio.sleep(0.5)
    except KeyboardInterrupt:
        print("\n🛑 Unterbrochen")
    
    await pipeline.stop()
    
    print("\n" + "=" * 60)
    print("Test abgeschlossen!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OBD2 Data Pipeline")
    parser.add_argument("--mac", type=str, help="Vgate BLE MAC Adresse")
    parser.add_argument("--test", action="store_true", help="Test-Modus (Fake-Data)")
    
    args = parser.parse_args()
    
    async def _main():
        if args.test or not args.mac:
            await main_test()
        else:
            pipeline = DataPipeline(vgate_mac=args.mac)
            await pipeline.start()
            
            print("\nPipeline läuft. Drücke STRG+C zum Beenden.")
            try:
                while True:
                    stats = pipeline.get_stats()
                    print(f"  Speed: {stats['speed']:4.1f} km/h | "
                          f"RPM: {stats['rpm']:5.0f} | "
                          f"Real: {stats['has_real_data']}")
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Beende...")
                await pipeline.stop()
    
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\n🛑 Test beendet")