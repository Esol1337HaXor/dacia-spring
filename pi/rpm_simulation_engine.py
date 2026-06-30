#!/usr/bin/env python3
"""
RPM Simulation Engine für E-Auto OBD2 Adapter

Berechnet simulierte Motordrehzahl (RPM) basierend auf:
- Echter Geschwindigkeit vom Vgate iCar Pro (PID 010D)
- Fahrpedalposition (optional, PID 0111 für E-Autos)
- Beschleunigungs/Verzögerungsmuster

Besonderheit bei E-Autos (Dacia Spring):
- Kein Verbrennungsmotor → kein echtes RPM
- aber E-Motoren haben sehr wohl Drehzahl!
- Simuliertes RPM soll für Sound-Apps realistisch wirken

Ein-Pedal-Fahr-Modell:
- Bremsen / Ausrollen → niedrige RPM (800-1500)
- Konstante Speed → moderate RPM (1500-2500)
- Beschleunigen → hohe RPM (2500-6000+)
"""

import time
import math
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class DriveState(Enum):
    """Fahrzustand des E-Autos."""
    IDLE = "idle"              # Motor läuft, Fahrzeug steht
    ACCELERATING = "accelerating"  # Beschleunigung
    CRUISING = "cruising"      # Konstante Speed
    COASTING = "coasting"      # Ausrollen (kein Gas, keine Bremse)
    BRAKING = "braking"        # Bremsen
    REGENERATING = "regenerating"  # Rekuperation (Ein-Pedal)


@dataclass
class VehicleState:
    """Aktueller Zustand des Fahrzeugs."""
    speed_kmh: float = 0.0           # Aktuelle Geschwindigkeit (km/h)
    last_speed: float = 0.0          # Vorherige Geschwindigkeit
    speed_delta: float = 0.0         # Differenz
    pedal_position: float = 0.0      # Fahrpedal 0-100%
    drive_state: DriveState = DriveState.IDLE
    rpm: float = 0.0                 # Berechnete RPM
    gear: str = "P"                  # Gang (P, R, N, D, oder simuliert)
    timestamp: float = 0.0           # Zeitstempel


class RPMSimulationEngine:
    """
    Berechnet simulierte RPM basierend auf E-Auto Fahrzustand.
    
    Bei einem E-Auto wie dem Dacia Spring:
    - Der Elektromotor hat sehr wohl eine Drehzahl (tatsächlich 0-15000 RPM)
    - Für Sound-Apps simulieren wir aber einen "typischen" Verbrenner-Sound
    
    RPM-Bereiche:
    - Idle:         800-900 RPM
    - Leichtes Fahren:   1000-1500 RPM  
    - Mittig:       1500-2500 RPM
    - Schnell:      2500-4000 RPM
    - Volllast:     4000-6000 RPM
    """
    
    # Konstanten
    IDLE_RPM = 850
    MAX_RPM = 6500
    MIN_RPM = 700
    SHIFT_UP_THRESHOLD = 5000
    SHIFT_DOWN_THRESHOLD = 2500
    
    # Speed-RPM mapping (präzise für E-Auto)
    # Formel: RPM = Idle + (Speed * Faktor) + State-Offset
    # RevHeadz braucht stabile, vorhersagbare RPM-Werte!
    SPEED_TO_RPM_BASE = {
        0: 850,       # Stand = Idle (Motor an)
        1: 870,       # Erstes Rollen
        2: 900,       # Leichtes Beschleunigen
        5: 1000,      # Langsam fahren
        10: 1200,     # Schleichen (Bremsen/Ausrollen)
        15: 1400,     # Stadt niedrig
        20: 1600,     # Stadtfahren
        30: 2000,     # Mittig Stadt
        40: 2400,     # Außenstadt
        50: 2800,     # Landstraße
        60: 3200,     # Oberes Landstraße
        70: 3600,     # Autobahn Start
        80: 4000,     # Autobahn
        90: 4400,     # Autobahn mittig
        100: 4800,    # Autobahn hoch
        110: 5200,    # Autobahn schnell
        120: 5500,    # Autobahn maximal
        130: 5800,    # Über 120 (begrenzt E-Auto)
    }
    
    def __init__(self, idle_rpm: Optional[float] = None, max_rpm: Optional[float] = None):
        """
        Initialisiert die RPM Simulation Engine.
        
        Args:
            idle_rpm: Basis-Idle-RPM (default: 850)
            max_rpm: Maximale RPM (default: 6500)
        """
        if idle_rpm is not None:
            self.IDLE_RPM = idle_rpm
        if max_rpm is not None:
            self.MAX_RPM = max_rpm
            
        self.state = VehicleState()
        self.last_update = time.time()
        
        # 🚀 LATENZ-OPTIMIERT (26.06.2026):
        # KEIN Smoothing = SOFORTIGE Reaktion beim Gas geben UND wegnehmen!
        self.smoothing_factor = 1.0  # 1.0 = keine Glättung = keine Latenz!
        self.current_smooth_rpm = self.IDLE_RPM
        
        # Hysteresis ENTFERNT — sofortiger Zustandwechsel!
        self.last_drive_state = DriveState.IDLE
        self.state_hold_time = 0.0
        self.state_threshold = 0.0  # 0.0 = SOFORT wechseln, KEIN Warten!
        
        # Historie für Statistik
        self.rpm_history = []
        self.max_history = 3600  # 1 Stunde bei 1Hz
        
        # Logging
        self._last_log_speed = -1
        self._last_log_rpm = -1
        self._log_interval = 0.5  # Max alle 0.5s ausgeben
        
        print(f"🔧 RPM Engine initialisiert (Idle: {self.IDLE_RPM}, Max: {self.MAX_RPM})")
    
    def update(self, speed_kmh: float, pedal_position: Optional[float] = None) -> float:
        """
        Aktualisiert den Fahrzeugzustand und berechnet neue RPM.
        
        Args:
            speed_kmh: Aktuelle Geschwindigkeit in km/h (vom Vgate)
            pedal_position: Optional Fahrpedal 0-100% (vom Vgate, PID 22202E)
            
        Returns:
            Berechnete RPM-Wert
            
        Besonderheit: Bei Speed=0 wird RPM direkt aus Throttle berechnet
        für Realistische Leerlaufdrehzahl beim Gasgeben im Stand!
        """
        now = time.time()
        dt = now - self.last_update
        
        # Speed clamp
        speed_kmh = max(0.0, min(200.0, speed_kmh))
        
        # Delta berechnen
        self.state.speed_delta = speed_kmh - self.state.last_speed
        self.state.last_speed = self.state.speed_kmh
        self.state.speed_kmh = speed_kmh
        
        # Pedal position aktualisieren (falls übergeben)
        if pedal_position is not None:
            self.state.pedal_position = max(0.0, min(100.0, pedal_position))
        
        # === SPEZIALFALL: IM STAND — RPM aus Throttle ===
        if speed_kmh < 0.5 and self.state.pedal_position > 1:
            # Gasgeben im Stand → RPM direkt aus Pedalposition
            # Formel: RPM = Idle + (Pedal * Faktor)
            # Bei 25% Pedal: 850 + 25*24 = 1450 RPM
            # Bei 50% Pedal: 850 + 50*24 = 2050 RPM
            # Bei 100% Pedal: 850 + 100*24 = 3250 RPM
            throttle_factor = 24.0  # 24 RPM pro Prozentpunkt (mehr Power)
            target_rpm = self.IDLE_RPM + (self.state.pedal_position * throttle_factor)
            target_rpm = max(self.IDLE_RPM, min(5000, target_rpm))  # Max 5000 RPM im Stand
            
            # Smoothing: 1.0 = KEIN Glätten = SOFORTIGE Änderung!
            alpha = 1.0  # 100% sofort = keine Latenz mehr!
            self.current_smooth_rpm = (alpha * target_rpm + 
                                       (1 - alpha) * self.current_smooth_rpm)
            self.state.rpm = self.current_smooth_rpm
            self.state.drive_state = DriveState.ACCELERATING
            self.state.gear = "P"
            
            # Logging
            if int(self.state.rpm) % 100 == 0:
                print(f"  🔧 Standgas: Speed={speed_kmh:.1f} | Pedal={self.state.pedal_position:.0f}% | RPM={self.state.rpm:.0f}")
            
            return self.state.rpm
        
        # Drive State erkennen
        new_state = self._detect_drive_state(speed_kmh, dt)
        
        # Hysteresis: Zustand nur wechseln wenn stabil
        if new_state != self.last_drive_state:
            self.state_hold_time += dt
            if self.state_hold_time < self.state_threshold:
                new_state = self.last_drive_state  # Noch nicht wechseln
            else:
                self.last_drive_state = new_state
                self.state_hold_time = 0.0
        else:
            self.state_hold_time = 0.0
        
        self.state.drive_state = new_state
        self.state.timestamp = now
        
        # RPM basierend auf Zustand berechnen
        raw_rpm = self._calculate_raw_rpm(speed_kmh, new_state)
        
        # 🚀 KEIN Smoothing mehr = SOFORTIGE RPM-Anpassung!
        # Alt: alpha = 0.3 → 30% neu, 70% alt = träge beim Gas wegnehmen
        # Neu: alpha = 1.0 → 100% neu = keine Verzögerung!
        if self.current_smooth_rpm == 0:
            self.current_smooth_rpm = raw_rpm
        
        alpha = self.smoothing_factor  # JETZT: 1.0 = SOFORTIG!
        self.current_smooth_rpm = (alpha * raw_rpm + 
                                    (1 - alpha) * self.current_smooth_rpm)
        
        self.state.rpm = self.current_smooth_rpm
        self.state.gear = self._calculate_gear(speed_kmh, new_state)
        
        # Historie aktualisieren
        self.rpm_history.append({
            "timestamp": now,
            "speed": speed_kmh,
            "rpm": self.state.rpm,
            "state": new_state.value,
        })
        if len(self.rpm_history) > self.max_history:
            self.rpm_history.pop(0)
        
        self.last_update = now
        
        # Status-Logging (nur bei Änderungen)
        self._log_if_changed(speed_kmh, self.state.rpm)
        
        return self.state.rpm
    
    def _detect_drive_state(self, speed: float, dt: float) -> DriveState:
        """
        Erkennt den aktuellen Fahrzustand.
        """
        delta = self.state.speed_delta
        pedal = self.state.pedal_position
        
        if speed == 0:
            return DriveState.IDLE
        
        # Rekuperation (Ein-Pedal-Fahren):
        # Speed sinkend, Pedal losgelassen
        if delta < -2.0 and pedal < 10:
            return DriveState.REGENERATING
        
        # Bremsen: Speed sinkend stark
        if delta < -3.0:
            return DriveState.BRAKING
        
        # Beschleunigen: Speed steigend ODER Pedal > 30%
        if delta > 1.0 or pedal > 30:
            return DriveState.ACCELERATING
        
        # Konstante Speed: kleine Delta, moderate Pedal
        if abs(delta) <= 1.0 and pedal > 5:
            return DriveState.CRUISING
        
        # Ausrollen: Speed leicht sinkend, Pedal los
        if -1.0 < delta <= 0 and pedal < 5:
            return DriveState.COASTING
        
        # Fallback
        return DriveState.CRUISING
    
    def _calculate_raw_rpm(self, speed: float, state: DriveState) -> float:
        """
        Berechnet rohe RPM basierend auf Speed und Fahrzustand.
        """
        # Basis-RPM vom Speed interpolieren
        base_rpm = self._speed_to_rpm(speed)
        
        # Zustand-Bonus/Malus
        state_offset = 0.0
        
        if state == DriveState.IDLE:
            state_offset = 0  # Genau Idle
        elif state == DriveState.ACCELERATING:
            # Beschleunigen → RPM erhöhen
            pedal_ratio = self.state.pedal_position / 100.0
            state_offset = pedal_ratio * 1500  # Bis +1500 RPM
        elif state == DriveState.CRUISING:
            state_offset = 0  # Basis-RPM vom Speed
        elif state == DriveState.COASTING:
            state_offset = -200  # Leicht runter
        elif state == DriveState.BRAKING:
            state_offset = -300  # Weiter runter
        elif state == DriveState.REGENERATING:
            state_offset = -250  # Rekuperation = niedrige RPM
        
        rpm = base_rpm + state_offset
        
        # Clamp
        rpm = max(self.MIN_RPM, min(self.MAX_RPM, rpm))
        
        return rpm
    
    def _speed_to_rpm(self, speed: float) -> float:
        """
        Mappt Speed (km/h) auf Basis-RPM mittels Interpolation.
        """
        if speed <= 0:
            return self.IDLE_RPM
        
        speeds = list(self.SPEED_TO_RPM_BASE.keys())
        rpms = list(self.SPEED_TO_RPM_BASE.values())
        
        # Über dem Max-Speed
        if speed >= speeds[-1]:
            return rpms[-1] + (speed - speeds[-1]) * 50  # +50 RPM/km/h über 130
        
        # Unter dem Min-Speed
        if speed <= speeds[0]:
            return rpms[0]
        
        # Interpoliere zwischen den beiden nahen Punkten
        for i in range(len(speeds) - 1):
            if speeds[i] <= speed <= speeds[i + 1]:
                t = (speed - speeds[i]) / (speeds[i + 1] - speeds[i])
                return rpms[i] + t * (rpms[i + 1] - rpms[i])
        
        return rpms[-1]
    
    def _calculate_gear(self, speed: float, state: DriveState) -> str:
        """
        Simuliert einen Gang basierend auf Speed + RPM.
        
        Bei einem E-Auto gibt es eigentlich nur 1 Gang,
        aber für Sound-Apps simulieren wir typische 6-Gang Schaltgetriebe.
        
        Verbessert 26.06.2026:
        - RPM-bezogene Gangwahl (nicht nur Speed!)
        - Realistische Shift-Points (RPM fällt beim Schalten)
        - R/N für Park/Neutral recognized
        """
        if speed < 0.5:
            # Auto steht → Gang P (Park) oder R (Rückwärts)
            # Wir nutzen P für Normalfall
            return "P"
        
        # RPM-basierte Gangwahl mit realistischen Shift-Points
        # Ein echter Motor schaltet wenn RPM fällt (nicht wenn Speed steigt!)
        rpm = self.state.rpm
        
        # Gang 1: 850-2000 RPM (oder Speed < 15 km/h)
        if rpm < 2000 or speed < 15:
            return "1"
        
        # Gang 2: 2000-3000 RPM (oder Speed < 30 km/h)
        elif rpm < 3000 or speed < 30:
            return "2"
        
        # Gang 3: 3000-3800 RPM (oder Speed < 50 km/h)
        elif rpm < 3800 or speed < 50:
            return "3"
        
        # Gang 4: 3800-4500 RPM (oder Speed < 70 km/h)
        elif rpm < 4500 or speed < 70:
            return "4"
        
        # Gang 5: 4500-5200 RPM (oder Speed < 95 km/h)
        elif rpm < 5200 or speed < 95:
            return "5"
        
        # Gang 6: 5200+ RPM
        else:
            return "6"
    
    def _log_if_changed(self, speed: float, rpm: float):
        """Gibt Status nur bei merklichen Änderungen aus."""
        speed_int = int(speed)
        rpm_int = int(rpm)
        
        if speed_int != self._last_log_speed or rpm_int != self._last_log_rpm:
            if speed_int % 5 == 0 or rpm_int % 100 == 0:
                state_icon = {
                    DriveState.IDLE: "⏸️",
                    DriveState.ACCELERATING: "🚀",
                    DriveState.CRUISING: "🏎️",
                    DriveState.COASTING: "🛤️",
                    DriveState.BRAKING: "🛑",
                    DriveState.REGENERATING: "🔋",
                }.get(self.state.drive_state, "❓")
                
                print(f"  {state_icon} Speed: {speed:4.1f} km/h | "
                      f"RPM: {rpm:5.0f} | "
                      f"Gang: {self.state.gear} | "
                      f"Zustand: {self.state.drive_state.value}")
                
                self._last_log_speed = speed_int
                self._last_log_rpm = rpm_int
    
    def get_state(self) -> VehicleState:
        """Gibt aktuellen Fahrzeugzustand zurück."""
        return self.state
    
    def get_rpm(self) -> float:
        """Gibt aktuelle RPM zurück."""
        return self.state.rpm
    
    def get_supported_pids(self) -> str:
        """
        Gibt Supported PIDs Bitmap zurück (für OBD2 PID 0100).
        
        Bitfeld für PIDs 01-20:
        Byte1: PIDs 01-08
        Byte2: PIDs 09-16
        Byte3: PIDs 17-24
        Byte4: PIDs 25-32
        """
        # Unterstützte PIDs:
        # PID 01 (Status) - Bit 7 von Byte1 = 0x80
        # PID 04 (Engine Load) - Bit 3 von Byte1 = 0x08
        # PID 05 (Coolant Temp) - Bit 2 von Byte1 = 0x04
        # PID 0C (RPM) - Bit 4 von Byte2 = 0x10
        # PID 0D (Speed) - Bit 5 von Byte2 = 0x20
        # PID 01 (Status) - Bit 0 von Byte1 = 0x01
        
        byte1 = 0x80 | 0x08 | 0x04 | 0x01  # PIDs 01, 04, 05
        byte2 = 0x10 | 0x20                 # PIDs 0C, 0D
        byte3 = 0x00
        byte4 = 0x00
        
        return f"{byte1:02X} {byte2:02X} {byte3:02X} {byte4:02X}"
    
    def reset(self):
        """Setzt Engine auf Initialzustand zurück."""
        self.state = VehicleState()
        self.current_smooth_rpm = self.IDLE_RPM
        self.last_update = time.time()
        self.last_drive_state = DriveState.IDLE
        self.state_hold_time = 0.0
        self._last_log_speed = -1
        self._last_log_rpm = -1
        print("🔄 RPM Engine zurückgesetzt")


if __name__ == "__main__":
    # Demo-Test
    import json
    
    engine = RPMSimulationEngine()
    
    print("\n" + "=" * 60)
    print("RPM Simulation Engine - Demo")
    print("=" * 60 + "\n")
    
    # Simuliere eine Fahrt
    test_cases = [
        (0, 0, "Motor startet, Fahrzeug steht"),
        (5, 10, "Langsam losfahren"),
        (15, 30, "Städtisches Fahren"),
        (30, 50, "Beschleunigen"),
        (50, 60, "Höheres Tempo"),
        (70, 70, "Kreisen"),
        (80, 80, "Autobahn"),
        (60, 40, "Leichtes Bremsen"),
        (40, 20, "Stärker bremsen"),
        (20, 0, "Komplett stoppen"),
        (0, 0, "Wieder stehen"),
        (10, 50, "Re-Akzeleration"),
        (60, 80, "Volles Gas"),
    ]
    
    for speed, pedal, description in test_cases:
        print(f"\n>>> {description}")
        rpm = engine.update(speed, pedal)
        state = engine.get_state()
        print(f"    Speed: {speed} km/h, Pedal: {pedal}%")
        print(f"    RPM: {rpm:.0f}, Gear: {state.gear}, State: {state.drive_state.value}")
    
    print("\n" + "=" * 60)
    print("Supported PIDs (für 01 00):", engine.get_supported_pids())
    print("=" * 60)