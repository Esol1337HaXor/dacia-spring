# RPM-Simulationsalgorithmus - Spezifikation

## Übersicht

Dieser Algorithmus erzeugt realistische, synthetische Motordrehzahlen (RPM) aus EV-Fahrzeugdaten. Das Ziel ist es, für Sound-Apps ein nicht-lineares, realistisches RPM-Verhalten zu erzeugen, das sich wie ein mehrgängiger Verbrennungsmotor anfühlt.

## Eingangsparameter (von CAN-Bus)

| Parameter | CAN-Feld | Einheit | Bereich | Quelle |
|-----------|----------|---------|---------|--------|
| `vehicle_speed` | Speed | km/h | 0 - 200 | CAN Frame Speed |
| `vehicle_ready` | Ignition/Ready | bool | true/false | CAN Frame Ready |
| `throttle_position` | Pedal | % | 0 - 100 | CAN Frame Pedal |
| `motor_power` | Power | kW | -100 - +150 | CAN Frame Power |
| `brake_pressed` | Brake | bool | true/false | CAN Frame Brake |
| `gear_position` | Gear | enum | D/N/R/P | CAN Frame Gear |

## Ausgangsparameter (an Sound-App)

| Parameter | PID | Einheit | Bereich |
|-----------|-----|---------|---------|
| `virtual_rpm` | 0x0C | RPM | 0 - 8000 |
| `engine_load` | 0x04 | % | 0 - 100 |

## Zustandsmaschine

```
                     ┌─────────┐
                     │  OFF    │  (vehicle_ready = false)
                     │  RPM=0  │
                     └────┬────┘
                          │ vehicle_ready = true
                          ▼
                     ┌─────────┐     ┌──────────┐
               ┌────│  IDLE   │────▶│  STOPPED │
               │    │0-5 km/h │     │ 0 km/h   │
               │    │RPM:800  │     │RPM:0     │
               │    └─────────┘     └──────────┘
               │         │              │
               │    speed > 5        brake release
               │         │              │
               │         ▼              ▼
               │   ┌──────────┐   ┌──────────┐
               └───│  DRIVE   │◀──│  ACCEL   │
                   │          │   │ throttle │
                   │──────────│   │ > 10%    │
                   │accel>5%  │   └──────────┘
                   │throttle  │         │
                   │>30%      │         │
                   └─────┬────┘         │
                         │              │
                   throttle > 70%       │
                         │              │
                    ┌────┴──────────────┘
                    ▼
              ┌─────────────┐
              │  SHIFT-TRIP │  RPM > 5500
              │             │  throttle > 80%
              │ Check:     │
              │ Gear Up?   │
              └──────┬─────┘
                     │
            ┌────────┴────────┐
            │                 │
            ▼                 ▼
     ┌─────────────┐   ┌─────────────┐
     │  GEAR UP    │   │  FORCE RPM  │
     │ RPM: 5500→  │   │  CAP @ 6500 │
     │  3200       │   │               │
     └─────────────┘   └─────────────┘
```

## Phase 1: OFF (Fahrzeug nicht Ready)

```python
if not vehicle_ready:
    virtual_rpm = 0
    engine_load = 0
    state = "OFF"
```

## Phase 2: STOPPED (Ready aber 0 km/h)

```python
if vehicle_ready and vehicle_speed < 0.5 and throttle_position < 5:
    virtual_rpm = 0  # Wie bei Auto mit Start-Stopp
    engine_load = 0
    state = "STOPPED"
```

## Phase 3: IDLE (Ready, langsam, kein Gas)

```python
if vehicle_ready and vehicle_speed <= 5 and throttle_position < 10:
    # Virtueller Leerlauf mit leichter Variation
    base_rpm = 850
    noise = random.gauss(0, 15)  # Natürliche Variation
    virtual_rpm = max(750, min(950, base_rpm + noise))
    engine_load = 5  # Geringe Last (Klima, Licht)
    state = "IDLE"
```

## Phase 4: DRIVE (Hauptphase)

### 4a: Normal Driving (0-70% Gas, keine Shift-Trip)

```python
def calculate_drive_rpm(speed, throttle, acceleration, power):
    """
    Berechne RPM für Normalfahrzustand.
    
    Die Formel kombiniert mehrere Faktoren:
    - Speed: Grundlegende RPM-Basis (höherer Gang bei highway)
    - Throttle: Lastabhängige RPM-Erhöhung
    - Acceleration: Dynamische RPM-Anhebung
    - Power: EV-spezifische Korrektur
    """
    
    # Basis-RPM aus Geschwindigkeit (simuliert Getriebe-Übersetzung)
    # Annahme: Bei 120 km/h ≈ 2500 RPM (hoher Overdrive)
    base_rpm = 50 + (speed * 18)  # 0 km/h → 50, 120 km/h → 2210
    
    # Throttle-Korrektur (mehr Gas = höhere RPM)
    throttle_boost = throttle * 15  # 0-100 → 0-1500
    
    # Acceleration-Korrektur (schnelles Beschleunigen = höhere RPM)
    if acceleration > 0.5:
        accel_boost = acceleration * 200  # +200 RPM pro m/s²
    else:
        accel_boost = 0
    
    # EV-Power-Korrektur (hohe Aufnahme = hohe Last)
    if power > 10:  # Nur bei Leistungsaufnahme, nicht Rekuperation
        power_factor = power * 3  # +3 RPM pro kW
    else:
        power_factor = 0
    
    # Zusammen setzen
    rpm = base_rpm + throttle_boost + accel_boost + power_factor
    
    # Clamp und Glätten
    rpm = max(50, min(7500, rpm))
    rpm = smooth_rpm(rpm, 0.3)  # Glättungsfaktor 0-1
    
    return rpm
```

### 4b: High Throttle (Über 70% Gas)

```python
if throttle_position > 70 and acceleration > 1.0:
    # Simuliere hohen Motorbetrieb
    rpm_base = 3500 + (throttle_position * 35)  # 3500-7000
    
    # Beschleunigung verstärkt RPM-Anstieg
    if acceleration > 2.0:
        rpm_base += (acceleration - 2.0) * 300
    
    # Shift-Trip Prüfung
    if rpm_base > 5500 and throttle_position > 80:
        state = "SHIFT-TRIP"
    else:
        virtual_rpm = rpm_base
        engine_load = min(100, throttle_position + 20)
        state = "HIGH_THROTTLE"
```

### 4c: Bremsen / Rekuperation

```python
if brake_pressed or power < -5:  # Negativ = Rekuperation
    # RPM schnell sinken lassen
    target_rpm = 800
    
    if vehicle_speed < 1:
        target_rpm = 0  # Stoppen
    
    # Glattes Absinken, nicht zu abrupt
    virtual_rpm = max(target_rpm, virtual_rpm - 300)
    engine_load = 0
    state = "DECEL"
```

## Phase 5: SHIFT-TRIP (Gangwechsel-Simulation)

```python
def handle_shift_trip(throttle, speed):
    """
    Simuliere Gangwechsel wenn RPM zu hoch wird.
    
    Wann: throttle > 80% UND RPM > 5500
    Was: RPM fällt von ~5500 auf ~3000 (wie Gang hochschalten)
    """
    global shift_state
    
    if shift_state == "WAITING":
        if throttle_position > 80:
            shift_state = "TRIGGERED"
    
    elif shift_state == "TRIGGERED":
        if virtual_rpm > 5500:
            shift_state = "SHIFTING"
            shift_start_time = now()
            shift_target_rpm = 2800 + (speed * 15)  # Ziel-RPM nach Gangwechsel
            
            # Kurze Pause für "Kickdown"-Effekt
            play_shift_sound_effect()  # Optional für visuelles Feedback
    
    elif shift_state == "SHIFTING":
        elapsed = now() - shift_start_time
        
        if elapsed < 0.15:
            # Kurzer Moment bei hohem RPM (Kickdown)
            virtual_rpm = 5500
        elif elapsed < 0.3:
            # Schneller Drop (Gangwechsel)
            progress = (elapsed - 0.15) / 0.15
            virtual_rpm = lerp(5500, shift_target_rpm, progress)
        else:
            # Fertig
            shift_state = "WAITING"
            virtual_rpm = shift_target_rpm
            engine_load = max(5, throttle_position * 0.3)
```

## Glättungsfunktion

```python
def smooth_rpm(new_rpm, smoothing_factor=0.3):
    """
    Glättet RPM-Schwankungen für natürlicheres Verhalten.
    
    smoothing_factor: 0 = sehr glatt, 1 = kein Glätten
    """
    global smoothed_rpm
    smoothed_rpm = (smoothed_rpm * (1 - smoothing_factor)) + (new_rpm * smoothing_factor)
    return smoothed_rpm

def lerp(a, b, t):
    """Linear Interpolation"""
    return a + (b - a) * t
```

## Zufällige Variation (Natural Noise)

```python
import random

def add_natural_noise(base_rpm, is_idle=False):
    """
    Fügt natürliche RPM-Schwankungen hinzu.
    
    Idle: Kleinere Schwankungen (±15 RPM)
    Driving: Größere Schwankungen (±50 RPM)
    """
    if is_idle:
        noise = random.gauss(0, 10)
    else:
        noise = random.gauss(0, 25)
    
    return base_rpm + noise
```

## Vollständiger Berechnungsloop

```python
class RPMSimulator:
    def __init__(self):
        self.state = "OFF"
        self.shift_state = "WAITING"
        self.smoothed_rpm = 0
        self.last_update = 0
        
        # Konstanten
        self.IDLE_RPM = 850
        self.SHIFT_TRIGGER_RPM = 5500
        self.SHIFT_TARGET_RPM_BASE = 2800
        self.MAX_RPM = 7500
        self.MIN_RPM = 0
        self.SMOOTHING_FACTOR = 0.3
    
    def update(self, vehicle_speed, throttle, acceleration, 
               power, brake, ready):
        """
        Hauptschleife für RPM-Berechnung.
        SOLLTE alle 50-100ms aufgerufen werden.
        """
        if not ready:
            self.state = "OFF"
            self.smoothed_rpm = 0
            return 0, 0
        
        if self.state == "OFF" and ready:
            self.state = "IDLE"
        
        # Bremsen优先
        if brake or power < -5:
            return self._handle_braking(vehicle_speed)
        
        # Idle Bereich
        if vehicle_speed <= 5 and throttle < 10:
            return self._handle_idle()
        
        # High Throttle / Shift-Check
        if throttle > 70 and acceleration > 1.0:
            return self._handle_high_throttle(throttle, vehicle_speed, acceleration)
        
        # Normal Driving
        return self._handle_driving(vehicle_speed, throttle, acceleration, power)
    
    def _handle_idle(self):
        base = self.IDLE_RPM + random.gauss(0, 10)
        self.smoothed_rpm = self._smooth(base)
        return int(self.smoothed_rpm), 5
    
    def _handle_braking(self, speed):
        target = 0 if speed < 1 else 800
        self.smoothed_rpm = max(target, self.smoothed_rpm - 300)
        return int(self.smoothed_rpm), 0
    
    def _handle_driving(self, speed, throttle, accel, power):
        base = 50 + (speed * 18)
        boost = throttle * 15
        
        accel_boost = accel * 200 if accel > 0.5 else 0
        power_factor = power * 3 if power > 10 else 0
        
        raw_rpm = base + boost + accel_boost + power_factor
        return self._smooth_and_return(raw_rpm)
    
    def _handle_high_throttle(self, throttle, speed, accel):
        base = 3500 + (throttle * 35)
        if accel > 2.0:
            base += (accel - 2.0) * 300
        
        if base > self.SHIFT_TRIGGER_RPM and throttle > 80:
            self._trigger_shift(base, speed)
        
        return self._smooth_and_return(base)
    
    def _trigger_shift(self, current_rpm, speed):
        # Shift-Logik wie oben beschrieben
        pass
    
    def _smooth(self, value):
        return (self.smoothed_rpm * (1 - self.SMOOTHING_FACTOR)) + \
               (value * self.SMOOTHING_FACTOR)
    
    def _smooth_and_return(self, raw_value):
        self.smoothed_rpm = self._smooth(raw_value)
        rpm = max(self.MIN_RPM, min(self.MAX_RPM, int(self.smoothed_rpm)))
        load = min(100, int(raw_value / 75))  # Simuliere Last aus RPM
        return rpm, load
```

## Parameter-Tuning-Leitfaden

| Parameter | Einfluss | Empfohlener Bereich |
|-----------|----------|---------------------|
| `base_rpm_speed_factor` | Steigung RPM-Speed Kurve | 15-25 |
| `throttle_multiplier` | Gas → RPM Reaktion | 10-20 |
| `accel_multiplier` | Beschleunigung → RPM | 150-300 |
| `power_multiplier` | EV Power → RPM | 2-5 |
| `smoothing_factor` | Glättung (0=viel, 1=wenig) | 0.2-0.5 |
| `shift_trigger_rpm` | Wann Gangwechsel | 5000-6000 |
| `shift_target_ratio` | Ziel-RPM nach Gangwechsel | 0.5-0.6 |
| `idle_rpm` | Leerlauf-RPM | 800-1000 |
| `idle_noise_stddev` | Leerlauf-Variation | 5-20 |

## Test-Szenarien

### Szenario 1: Ständiges Anfahren
```
Vehicle: 0 → Ready → Gas geben (50%) → 30 km/h halten → Bremsen → Stop
Erwartet: 0 → 850 → ~2500 → ~1000 → ~850 → 0
```

### Szenario 2: Volgas-Beschleunigung
```
Vehicle: Ready → Volgas → bis ~6000 RPM → Gangwechsel → weiter
Erwartet: 850 → 3000 → 5000 → SHIFT → 3000 → weiter steigt
```

### Szenario 3: Stadtverkehr
```
Ampel → Grün → mäßig Gas → 50 km/h → Tempo-Limit → losfahren
Erwartet: 0 → 850 → ~1500 → ~1000 → 0 → ~850 → ~1200
```

### Szenario 4: Autobahn
```
Ausfahrt → stark beschleunigen → 120 km/h halten
Erwartet: 850 → 3000 → SHIFT → ~2200 (constant)