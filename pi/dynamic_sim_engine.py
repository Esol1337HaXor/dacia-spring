#!/usr/bin/env python3
"""
Dynamic Simulation Engine für E-Autos (Sport-Modus)

Berechnet RPM und Gang basierend auf Speed + Gaspedal-Position.
Überzogene Sport-Werte für RevHeadz App.

Eingabe:
- Speed (km/h) — echt vom Vlink BLE
- Throttle (0-100%) — Gaspedal-Position

Ausgabe:
- RPM (simuliert, 800-8000)
- Gang (0-6)
- Engine Load (simuliert)

Algorithmus:
- Gang wird aus Speed ermittelt (Sport-Schaltpunkte)
- RPM wird aus Gang + Throttle berechnet (überzogene Werte)
- Nicht-lineare Verstärkung für mehr Dynamik
- Redline-Bereich bei 7500+ RPM
- Auto-Downshift bei Überdrehzahl
"""

import math


class DynamicSimEngine:
    """
    Dynamische RPM/Gang-Simulation für E-Autos.
    
    Berechnet realistische (sportliche) RPM und Gang aus Speed + Throttle.
    """
    
    # === KONFIGURATION: SPORT-WERTE ===
    
    # Gang-Schaltpunkte (Speed-basiert)
    # Index + 1 = Gangnummer
    GEAR_SPEED_THRESHOLDS = [
        (0, 20),     # Gang 1: 1-20 km/h
        (20, 40),    # Gang 2: 20-40 km/h
        (40, 60),    # Gang 3: 40-60 km/h
        (60, 80),    # Gang 4: 60-80 km/h
        (80, 110),   # Gang 5: 80-110 km/h
        (110, 999),  # Gang 6: 110+ km/h
    ]
    
    # Basis-RPM pro Gang (höherer Leerlauf)
    GEAR_BASE_RPM = {
        0: 1200,   # Leerlauf (höher für Sport-Feeling)
        1: 2500,
        2: 3000,
        3: 3500,
        4: 4000,
        5: 4500,
        6: 5000,
    }
    
    # RPM-Range pro Gang (wie weit Throttle hochzählt)
    GEAR_RPM_RANGE = {
        0: 0,      # Kein Range bei Leerlauf
        1: 3000,   # 2500-5500
        2: 3000,   # 3000-6000
        3: 3000,   # 3500-6500
        4: 3000,   # 4000-7000
        5: 3000,   # 4500-7500
        6: 3000,   # 5000-8000 (Redline!)
    }
    
    # Redline-Bereich
    REDLINE_RPM = 7500
    MAX_RPM = 8000
    MIN_RPM = 800
    
    # Smooth-Faktor (0-1, niedriger = smoother)
    SMOOTH_ALPHA = 0.25  # 25% neues RPM, 75% altes RPM
    
    # Nicht-lineare Throttle-Verstärkung
    # 1.0 = linear, >1.0 = überproportional
    THROTTLE_CURVE = 1.3  # Überzogene Beschleunigung
    
    # Downshift bei Überdrehzahl
    DOWNSHIFT_RPM = 7800
    
    # Upshift bei Niedrigdrehzahl
    UPSHIFT_RPM = 2000
    
    def __init__(self):
        self._last_rpm = 1200
        self._last_speed = 0.0
        self._last_throttle = 0.0
        self._last_gear = 0
        
        # Telemetrie
        self._peak_rpm = 0
        self._peak_speed = 0
        self._gear_shifts = 0
    
    def get_gear(self, speed: float) -> int:
        """
        Ermittelt den aktuellen Gang basierend auf Speed.
        
        Args:
            speed: Speed in km/h
            
        Returns:
            Gang (0=N bei 0 km/h, 1-6)
        """
        if speed < 1:
            return 0  # Neutral/Stand
        for gear, (min_speed, max_speed) in enumerate(self.GEAR_SPEED_THRESHOLDS, start=1):
            if min_speed <= speed < max_speed:
                return gear
        return len(self.GEAR_SPEED_THRESHOLDS)  # Max Gang
    
    def calculate_rpm(self, gear: int, throttle: float) -> float:
        """
        Berechnet RPM basierend auf Gang und Throttle.
        
        Verwendet nicht-lineare Verstärkung für sportlicheres Feeling.
        
        Args:
            gear: Aktueller Gang (0=N, 1-6)
            throttle: Gaspedal-Position (0.0-1.0)
            
        Returns:
            RPM (800-8000)
        """
        base_rpm = self.GEAR_BASE_RPM.get(gear, 1200)
        rpm_range = self.GEAR_RPM_RANGE.get(gear, 3000)
        
        # Nicht-lineare Throttle-Verstärkung
        # Bei 50% Throttle = mehr als 50% RPM-Steigerung
        if throttle > 0:
            enhanced_throttle = min(1.0, throttle ** (2.0 - self.THROTTLE_CURVE))
        else:
            enhanced_throttle = 0
        
        raw_rpm = base_rpm + enhanced_throttle * rpm_range
        
        # Begrenzung auf Min/Max
        return max(self.MIN_RPM, min(self.MAX_RPM, raw_rpm))
    
    def update(self, speed: float, throttle: float) -> dict:
        """
        Aktualisiert die Simulation und berechnet RPM + Gang.
        
        Args:
            speed: Aktuelle Speed in km/h
            throttle: Gaspedal-Position (0.0-1.0 = 0-100%)
            
        Returns:
            Dict mit: rpm, gear, engine_load, raw_rpm
        """
        self._last_speed = speed
        self._last_throttle = throttle
        
        # Gang ermitteln (basierend auf aktueller Speed)
        gear = self.get_gear(speed)
        prev_gear = self._last_gear
        
        # RPM berechnen
        raw_rpm = self.calculate_rpm(gear, throttle)
        
        # Smooth (exponential glätten) — vor Auto-Shifts
        alpha = self.SMOOTH_ALPHA
        smoothed_rpm = alpha * raw_rpm + (1 - alpha) * self._last_rpm
        
        # Auto-Upshift wenn Speed zu niedrig für Gang (runterbremsen)
        # z.B. Gang 3 bei 40 km/h → noch OK
        # z.B. Gang 3 bei 30 km/h → downshift auf Gang 2
        if speed > 1 and smoothed_rpm < self.UPSHIFT_RPM and gear > 1:
            # Zu niedrig für aktuellen Gang → runter
            new_gear = gear - 1
            if new_gear >= 1:
                raw_rpm = self.calculate_rpm(new_gear, throttle)
                smoothed_rpm = alpha * raw_rpm + (1 - alpha) * self._last_rpm
                gear = new_gear
                self._gear_shifts += 1
        
        # Telemetrie aktualisieren
        self._last_rpm = smoothed_rpm
        self._last_gear = gear
        if smoothed_rpm > self._peak_rpm:
            self._peak_rpm = smoothed_rpm
        if speed > self._peak_speed:
            self._peak_speed = speed
        
        # Engine Load simulieren
        engine_load = self._calculate_engine_load(speed, throttle, gear)
        
        return {
            "rpm": round(smoothed_rpm, 1),
            "gear": gear,
            "engine_load": round(engine_load, 1),
            "raw_rpm": round(raw_rpm, 1),
            "throttle": round(throttle * 100, 1),  # % umrechnen
            "speed": round(speed, 1),
            "peak_rpm": round(self._peak_rpm, 1),
            "peak_speed": round(self._peak_speed, 1),
            "gear_shifts": self._gear_shifts,
        }
    
    def _calculate_engine_load(self, speed: float, throttle: float, gear: int) -> float:
        """
        Bereint Engine Load (0-100%) für RevHeadz.
        
        Load hängt ab von:
        - Throttle (Hauptfaktor)
        - Beschleunigung (Speed-Delta)
        - Gang (niedriger Gang + viel Gas = hohe Load)
        """
        # Basis: Throttle
        load = throttle * 100
        
        # Beschleunigungs-Bonus
        delta_speed = speed - self._last_speed
        if delta_speed > 0.5:
            load += delta_speed * 5  # Beschleunigen = höhere Load
        
        # Gang-Korrektur
        if gear == 0:
            load = min(100, load + 10)  # N/P = leicht erhöhte Load
        
        return max(0, min(100, load))
    
    def reset(self):
        """Setzt die Engine zurück."""
        self._last_rpm = 1200
        self._last_speed = 0.0
        self._last_throttle = 0.0
        self._last_gear = 0
        self._peak_rpm = 0
        self._peak_speed = 0
        self._gear_shifts = 0
    
    def get_telemetry(self) -> dict:
        """Gibt Telemetrie-Daten zurück."""
        return {
            "peak_rpm": round(self._peak_rpm, 1),
            "peak_speed": round(self._peak_speed, 1),
            "gear_shifts": self._gear_shifts,
        }


def print_test():
    """Testet die DynamicSimEngine mit simulierten Fahrdaten."""
    engine = DynamicSimEngine()
    
    print("=" * 70)
    print("Dynamic Simulation Engine - SPORT-MODUS TEST")
    print("=" * 70)
    print()
    
    # Test-Szenario: 0-100 km/h mit vollem Gas
    print("Szenario: Vollgas von 0-100 km/h")
    print("-" * 70)
    print(f"{'Speed':>8} | {'Throttle':>10} | {'Gear':>5} | {'RPM':>8} | {'Load':>6} | {'Info'}")
    print("-" * 70)
    
    # Simuliere Fahrprofil
    test_data = [
        (0, 0.0),    # Stand
        (0, 0.3),    # 30% Gas im Stand
        (0, 1.0),    # Vollgas im Stand
        (5, 1.0),
        (10, 1.0),
        (15, 1.0),   # Schaltpunkt G1→G2
        (20, 1.0),
        (25, 1.0),
        (30, 1.0),
        (35, 1.0),   # Schaltpunkt G2→G3
        (40, 1.0),
        (45, 1.0),
        (50, 1.0),
        (55, 1.0),   # Schaltpunkt G3→G4
        (60, 1.0),
        (65, 1.0),
        (70, 1.0),
        (75, 1.0),   # Schaltpunkt G4→G5
        (80, 1.0),
        (85, 1.0),
        (90, 1.0),
        (95, 1.0),   # Schaltpunkt G5→G6
        (100, 1.0),
        (100, 0.5),  # Ausrollen
        (95, 0.0),   # Ausrollen
        (80, 0.0),
        (60, 0.0),
        (40, 0.0),
        (20, 0.0),
        (0, 0.0),    # Stop
    ]
    
    for speed, throttle in test_data:
        result = engine.update(speed, throttle)
        
        info = ""
        if result["rpm"] > 7500:
            info = "⚠️ REDLINE!"
        elif result["gear"] > engine._last_gear:
            info = "⬆ UP!"
        elif result["gear"] < engine._last_gear:
            info = "⬇ DOWN!"
        
        print(f"{result['speed']:8.1f} | {result['throttle']:9.1f}% | {result['gear']:5} | {result['rpm']:8.1f} | {result['engine_load']:5.1f}% | {info}")
    
    print("-" * 70)
    print()
    
    # Telemetrie
    telemetry = engine.get_telemetry()
    print("Telemetrie:")
    print(f"  Peak RPM:      {telemetry['peak_rpm']}")
    print(f"  Peak Speed:    {telemetry['peak_speed']} km/h")
    print(f"  Gear Shifts:   {telemetry['gear_shifts']}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    print_test()