# Master Plan: Vgate iCar Pro BLE → RPM/Gang Simulation

## Überblick

Dieses Dokument beschreibt den Master Plan für die Integration des Vgate iCar Pro BLE OBD2 Adapters in das Dacia Spring RevHeadz Motorsound System. Das Ziel ist es, echte OBD2-Daten vom Auto (Speed, Motor RPM) zu lesen und daraus simulierte RPM und Gang-Werte für den Motorsound zu berechnen.

---

## 1. System-Zielarchitektur

```
┌─────────────────────────────────────────────────────────────────────┐
│                        IM AUTO                                       │
│                                                                      │
│  ┌─────────────────┐                                                │
│  │  Dacia Spring   │                                                │
│  │  E-Auto         │                                                │
│  │                 │                                                │
│  │  OBD2 Port      │                                                │
│  │     │           │                                                │
│  │     │ CAN Bus   │                                                │
│  │     ▼           │                                                │
│  │  ┌──────────┐   │                                                │
│  │  │ Vgate    │   │                                                │
│  │  │ iCar Pro │   │                                                │
│  │  │ BLE      │   │                                                │
│  │  └────┬─────┘   │                                                │
│  │       │ BLE     │                                                │
│  └───────┼─────────┘                                                │
│          │                                                            │
│          ▼ BLE 4.0 GATT                                             │
│  ┌──────────────────┐                                                │
│  │ Raspberry Pi     │                                                │
│  │ Zero 2 W         │                                                │
│  │                  │                                                │
│  │  ┌───────────┐   │                                                │
│  │  │ BLE      │   │                                                │
│  │  │ Client   │   │                                                │
│  │  │ (bleak)  │   │                                                │
│  │  └────┬─────┘   │                                                │
│  │       │         │                                                │
│  │       │ CAN     │                                                │
│  │       │ Data    │                                                │
│  │       ▼         │                                                │
│  │  ┌─────────────────────┐                                        │
│  │  │ Data Pipeline       │                                        │
│  │  │ ┌─────────────────┐ │                                        │
│  │  │ │ CAN Parse       │ │                                        │
│  │  │ │ → Speed (010D)  │ │                                        │
│  │  │ │ → Throttle      │ │                                        │
│  │  │ └─────────────────┘ │                                        │
│  │  │ ┌─────────────────┐ │                                        │
│  │  │ │ RPM Engine      │ │                                        │
│  │  │ │ E-Auto Model    │ │                                        │
│  │  │ │ → RPM + Gear    │ │                                        │
│  │  │ └─────────────────┘ │                                        │
│  │  └─────────────────────┘                                        │
│  │       │                                                         │
│  │       │ PIDs (simuliert)                                        │
│  │       ▼                                                         │
│  │  ┌─────────────────────┐                                        │
│  │  │ TCP Server          │                                        │
│  │  │ Port 2117           │                                        │
│  │  │ ELM327 Emulation    │                                        │
│  │  └────────┬────────────┘                                        │
│  │           │                                                     │
│  └───────────┼─────────────────────────────────────────────────────┘
│              │ TCP/IP (WiFi)
│              │
│              ▼
│  ┌──────────────────────┐
│  │  Android Phone       │
│  │  RevHeadz App        │
│  │  - RPM Anzeige       │
│  │  - Motorsound        │
│  │  - Gang Anzeige      │
│  └──────────────────────┘
│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technische Architektur

### 2.1 BLE Layer (Vgate iCar Pro)

**Hardware:** Vgate iCar Pro BLE 4.0
- **UUID Service:** 0000ffe1-0000-1000-8000-00805f9b34fb
- **UUID Characteristic:** 0000ffe1-0000-1000-8000-00805f9b34fb
- **Protocol:** ELM327 über BLE GATT

**BLE Kommunikation:**
```
Android App (bleak)
    │
    │ Write: ELM327 Command (z.B. "01 0D")
    ▼
Vgate iCar Pro BLE
    │
    │ Read: Response (z.B. "41 0D 3C")
    ▼
CAN Bus Parser
    │
    │ Extrahiert: Speed, Throttle, Motor RPM
```

### 2.2 Data Pipeline Layer

**Module:**
1. `ble_client_vgate.py` - BLE Client für Vgate iCar Pro
2. `can_parser.py` - CAN Bus Frame Parser
3. `rpm_simulation_engine.py` - RPM/Gang Berechnung
4. `data_pipeline.py` - Verbindet alle Module

**Datenfluss:**
```
BLE Data → CAN Parser → (Speed, Throttle) → RPM Engine → (RPM, Gear)
                                                    │
                                                    ▼
                                              TCP Server → RevHeadz
```

### 2.3 TCP Server Layer

**Bestehend:** `pi/elm327_tcp_server_standalone.py`
- Port: 2117
- Protocol: ELM327 Emulation
- RevHeadz Kompatibel

**Erweiterung:**
- Echtzeit-Daten von RPM Engine beziehen
- Simulierte PIDs basierend auf Vgate Daten senden

---

## 3. RPM/Gang Simulation Modell (E-Auto)

### 3.1 E-Auto Spezifika

**Dacia Spring E-Auto:**
- **Motor:** Elektrischer Permanentmagnet-Synchronmotor
- **Getriebe:** 1-Gang Reduktionsgetriebe
- **Ein-Pedal-Fahren:** Ja (Rekuperation)
- **Max RPM:** ca. 12.000-14.000
- **Idle RPM:** ca. 800

**Unterschiede zu Verbrennern:**
- Kein Kupplungslüfter
- Kein Getriebe-Shift
- Sofortiges Drehmoment
- RPM steigt/fällt linear mit Speed/Throttle

### 3.2 Simulationsmodell

```python
class EAutoRPMModel:
    """
    Simuliert RPM und Gang für E-Auto (Dacia Spring)
    
    Input:
        throttle: 0.0 - 1.0 (0% = aus, 100% = Vollgas)
        speed: 0 - 180 km/h (Echte Speed vom Vgate)
    
    Output:
        rpm: Simulierter Motor-RPM
        gear: Simulierter "Gang" (1-4 für Sound)
    """
    
    def __init__(self):
        # E-Motor Parameter
        self.idle_rpm = 800           # Leerlauf E-Motor
        self.max_rpm = 12000          # Max E-Motor RPM
        self.efficiency_rpm = 6000    # Effizientester Bereich
        
        # Beschleunigung/Fahrzeugdynamik
        self.accel_curve = 0.8        #非线性 Beschleunigung
        self.decel_brake_factor = 1.5 # Rekuperation stark
        
        # Gang-Schwellen (für Motorsound)
        self.gear_thresholds = [
            (0, 2500, 1),     # 0-2500 RPM = "1. Gang"
            (2500, 5000, 2),   # 2500-5000 RPM = "2. Gang"
            (5000, 8000, 3),   # 5000-8000 RPM = "3. Gang"
            (8000, 12000, 4),  # 8000-12000 RPM = "4. Gang"
        ]
    
    def calculate(self, throttle, speed):
        """
        Berechnet RPM und Gang basierend auf Throttle + Speed
        """
        if speed == 0 and throttle > 0.1:
            # Start vom Stillen
            rpm = self.idle_rpm + (throttle * 3000)
        elif throttle < 0.1 and speed > 5:
            # Bremsen/Rekuperation
            rpm = max(self.idle_rpm, self.idle_rpm + (speed * 25))
        else:
            # Normaler Betrieb
            base_rpm = self.idle_rpm + (throttle ** 0.7) * (self.max_rpm - self.idle_rpm)
            speed_offset = speed * 15
            rpm = base_rpm + speed_offset
        
        # Begrenzen
        rpm = max(self.idle_rpm, min(self.max_rpm, rpm))
        
        # Jitter (natürliche Schwankung)
        rpm += random.randint(-30, 30)
        
        # Gang berechnen
        gear = self._get_gear(rpm)
        
        return rpm, gear
    
    def _get_gear(self, rpm):
        for low, high, gear in self.gear_thresholds:
            if low <= rpm < high:
                return gear
        return 4
```

---

## 4. Implementierungsplan

### 4.1 Phase 1: Research & Setup

**Ziel:** Technische Grundlagen verstehen und vorbereiten

**Aufgaben:**
1. Vgate iCar Pro BLE Protocol analysieren
   - GATT Service/Characteristic UUIDs
   - Datenformat der CAN Frames
   - ELM327 Commands die der Vgate unterstützt

2. bleak BLE Client Dokumentation prüfen
   - Connection Setup
   - Characteristic Reads
   - Notification/Subscription für Echtzeit-Daten

3. CAN Bus Frame Format Dacia Spring recherchieren
   - welche Frames enthalten Speed/Throttle?
   - Frame IDs und Datenformate

4. hostapd WiFi AP Setup auf Pi Zero 2W testen
   - Kann Pi Zero 2W gleichzeitig BLE Client + WiFi AP?
   - Netzwerk-Konfiguration

**Zeit:** 2-3 Tage

### 4.2 Phase 2: BLE Client Implementierung

**Ziel:** BLE Client der Echtzeit-Daten vom Vgate liest

**Dateien:**
- `pi/ble_client_vgate.py` - Hauptmodule
- `pi/can_parser.py` - CAN Frame Parser

**Funktionen:**
```python
# ble_client_vgate.py
class VgateBLEClient:
    """BLE Client für Vgate iCar Pro"""
    
    def __init__(self):
        self.device_address = None
        self.characteristic = None
        self.speed = 0
        self.throttle = 0
        self.motor_rpm = 0
    
    async def connect(self):
        """Verbindung zu Vgate iCar Pro aufbauen"""
        pass
    
    async def read_obd_data(self):
        """OBD2 Daten lesen (010D Speed, 010C RPM)"""
        pass
    
    async def parse_can_data(self, raw_data):
        """CAN Bus Frames parsen"""
        pass
    
    def get_current_values(self):
        """Aktuelle Werte zurückgeben (speed, throttle, rpm)"""
        return self.speed, self.throttle, self.motor_rpm
```

**Test-Szenario:**
```bash
# Vgate iCar Pro in OBD2 Port stecken
# Pi mit Vgate verbinden
python3 ble_client_vgate.py --scan
python3 ble_client_vgate.py --connect
python3 ble_client_vgate.py --read 010D  # Speed
python3 ble_client_vgate.py --read 010C  # RPM
```

**Zeit:** 2-3 Tage

### 4.3 Phase 3: RPM Engine

**Ziel:** Simuliertes RPM basierend auf Speed + Throttle

**Dateien:**
- `pi/rpm_simulation_engine.py` - RPM/Gang Berechnung
- `pi/test_rpm_engine.py` - Tests

**Funktionen:**
```python
# rpm_simulation_engine.py
class EAutoRPMEngine:
    """RPM/Gang Simulation für E-Auto"""
    
    def __init__(self):
        self.idle_rpm = 800
        self.max_rpm = 12000
        self.gear_thresholds = [...]
    
    def calculate(self, throttle, speed):
        """Berechnet RPM und Gear"""
        pass
    
    def _get_gear(self, rpm):
        """Berechnet simulierten Gang"""
        pass
```

**Test-Szenario:**
```python
# Manuelle Tests
engine = EAutoRPMEngine()

# Stillstand, Vollgas
rpm, gear = engine.calculate(1.0, 0)
print(f"RPM: {rpm}, Gear: {gear}")  # ~3800 RPM, Gear 1

# 50 km/h, halb Gas
rpm, gear = engine.calculate(0.5, 50)
print(f"RPM: {rpm}, Gear: {gear}")  # ~6000 RPM, Gear 3

# 100 km/h, kein Gas (Rekuperation)
rpm, gear = engine.calculate(0.0, 100)
print(f"RPM: {rpm}, Gear: {gear}")  # ~2500 RPM, Gear 2
```

**Zeit:** 1-2 Tage

### 4.4 Phase 4: Data Pipeline Integration

**Ziel:** Alle Module verbinden und mit TCP Server integrieren

**Dateien:**
- `pi/data_pipeline.py` - Hauptmodule
- `pi/start_all.sh` - Start Script

**Architektur:**
```python
# data_pipeline.py
class DataPipeline:
    """Verbindet BLE Client + RPM Engine + TCP Server"""
    
    def __init__(self):
        self.ble_client = VgateBLEClient()
        self.rpm_engine = EAutoRPMEngine()
        self.tcp_server = None
    
    async def run(self):
        """Startet alle Komponenten"""
        # 1. BLE Client starten
        await self.ble_client.connect()
        
        # 2. Daten-Loop
        while True:
            speed, throttle, motor_rpm = self.ble_client.get_current_values()
            
            # 3. RPM berechnen
            rpm, gear = self.rpm_engine.calculate(throttle, speed)
            
            # 4. Shared State aktualisieren
            shared_state.set_rpm(rpm)
            shared_state.set_gear(gear)
            shared_state.set_speed(speed)
            
            await asyncio.sleep(0.05)  # 20Hz Update
        
        # 5. TCP Server startet mit shared State
        self.tcp_server = TCPServer(shared_state)
        await self.tcp_server.start()
```

**Start Script:**
```bash
#!/bin/bash
# start_all.sh

cd /home/lsd/obd2-adapter

# Alten Server stoppen
pkill -f elm327_tcp_server 2>/dev/null
pkill -f data_pipeline 2>/dev/null

# Data Pipeline starten
nohup python3 data_pipeline.py > pipeline.log 2>&1 &
PIPELINE_PID=$!

echo "Data Pipeline started (PID: $PIPELINE_PID)"
echo "TCP Server: 192.168.178.87:2117"
```

**Zeit:** 1-2 Tage

### 4.5 Phase 5: WiFi Access Point

**Ziel:** Pi als WiFi AP im Auto betreiben

**Dateien:**
- `/etc/hostapd/hostapd.conf` - AP Konfiguration
- `/etc/dnsmasq.conf` - DHCP Server
- `/etc/systemd/system/elm327-ap.service` - Auto-Start

**hostapd Konfiguration:**
```bash
# /etc/hostapd/hostapd.conf
interface=wlan0
driver=nl80211
ssid=DaciaSpring-OBD2
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=dacia-spring-2026
wpa_key_mgmt=WPA-PSK
wpa_pair_pattern=TKIP
rsn_pair_pattern=CCMP
```

**dnsmasq Konfiguration:**
```bash
# /etc/dnsmasq.conf
interface=wlan0
dhcp-range=192.168.50.50,192.168.50.150,12h
dhcp-option=3,192.168.50.1
dhcp-option=6,192.168.50.1
```

**Netzwerk im Auto:**
```
Pi Zero 2W (WiFi AP)
SSID: DaciaSpring-OBD2
IP: 192.168.50.1
TCP: 192.168.50.1:2117

Android Phone
Verbindet sich zu: DaciaSpring-OBD2
IP erhält via DHCP: 192.168.50.x
RevHeadz: 192.168.50.1:2117
```

**Zeit:** 0.5-1 Tag

### 4.6 Phase 6: System Stabilisierung

**Ziel:** Robuster Betrieb im Auto

**systemd Services:**
```bash
# /etc/systemd/system/elm327-pipeline.service
[Unit]
Description=ELM327 Data Pipeline (BLE + RPM + TCP)
After=network.target bluetooth.target

[Service]
Type=simple
User=lsd
WorkingDirectory=/home/lsd/obd2-adapter
ExecStart=/usr/bin/python3 /home/lsd/obd2-adapter/data_pipeline.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Aktivierung:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable elm327-pipeline
sudo systemctl start elm327-pipeline
```

**Zeit:** 0.5 Tag

---

## 5. Abhängigkeiten und Requirements

### Hardware
- Raspberry Pi Zero 2 W ✅
- Vgate iCar Pro BLE ✅
- Android Phone mit RevHeadz ✅
- OBD2 Port im Auto ✅

### Software (Bestehend)
- Python 3 ✅
- socket ✅
- threading ✅
- random ✅

### Software (Neu benötigt)
- bleak (BLE Client)
- hostapd (WiFi AP)
- dnsmasq (DHCP)
- python3-asyncio (async)

### Installation auf Pi:
```bash
# bleak installieren
pip install bleak

# hostapd + dnsmasq installieren
sudo apt install hostapd dnsmasq

# Services aktivieren
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
```

---

## 6. Risiken und Challenges

### 6.1 BLE Controller Limitation
**Problem:** Pi Zero 2W BLE Controller kann nur Central ODER Peripheral Mode
**Lösung:** BLE Client (Central Mode) + WiFi TCP (nicht BLE) für RevHeadz
**Risiko:** Gering - Lösung bereits bekannt

### 6.2 Vgate iCar Pro BLE Protocol
**Problem:** Unklar welche Daten der Vgate genau sendet
**Lösung:** Research Phase - BLE Scan und Data Analysis
**Risiko:** Mittel - muss zuerst analysiert werden

### 6.3 CAN Bus Frame Format
**Problem:** Dacia Spring CAN Frame Format unbekannt
**Lösung:** CanZE Plus Dokumentation, FORAS Forum, eigene Tests
**Risiko:** Mittel - kann Iterationen benötigen

### 6.4 Echtzeit-Anforderungen
**Problem:** RevHeadz braucht 20-30Hz Updates
**Lösung:** Asynchrone Data Pipeline mit 50ms Update-Interval
**Risiko:** Gering - TCP Server ist bereits schnell genug

### 6.5 Stromversorgung im Auto
**Problem:** Pi Zero 2W muss im Auto versorgt werden
**Lösung:** 5V/3A Netzteil mit OBD2 Stecker oder Powerbank
**Risiko:** Gering - Standard Lösung

---

## 7. Test-Plan

### Phase 1 Tests
- [ ] Vgate BLE UUIDs gescannt und verifiziert
- [ ] bleak Library installiert und Test-Connect erfolgreich
- [ ] CAN Bus Frame Format dokumentiert

### Phase 2 Tests
- [ ] BLE Client verbindet sich zu Vgate
- [ ] Speed (010D) zeigt korrekte Werte
- [ ] Motor RPM (010C) zeigt korrekte Werte
- [ ] Throttle-Werte extrahierbar

### Phase 3 Tests
- [ ] RPM Engine berechnet plausiblen RPM
- [ ] Gang-Anzeige stimmt mit RPM überein
- [ ] Rekuperation (Bremsen) erkannt

### Phase 4 Tests
- [ ] Data Pipeline startet alle Modules
- [ ] Echtzeit-Daten fließen von BLE → TCP
- [ ] RevHeadz zeigt echte Speed + RPM

### Phase 5 Tests
- [ ] WiFi AP startet beim Boot
- [ ] Android Phone verbindet sich zu AP
- [ ] RevHeadz über AP funktioniert

### Phase 6 Tests
- [ ] System überlebt Reboot
- [ ] Auto-Recovery bei Crash funktioniert
- [ ] 24h Dauerlauf stabil

---

## 8. Zeitplan (Geschätzt)

| Phase | Dauer | Kumulative Zeit |
|-------|-------|-----------------|
| Phase 1: Research | 2-3 Tage | 2-3 Tage |
| Phase 2: BLE Client | 2-3 Tage | 4-6 Tage |
| Phase 3: RPM Engine | 1-2 Tage | 5-8 Tage |
| Phase 4: Integration | 1-2 Tage | 6-10 Tage |
| Phase 5: WiFi AP | 0.5-1 Tag | 6.5-11 Tage |
| Phase 6: Stabilisierung | 0.5 Tag | 7-11.5 Tage |

**Gesamt:** ca. 1-2 Wochen (bei Teilzeit-Entwicklung)

---

## 9. Erfolgskriterien

### Muss haben (Kritisch)
- [x] RevHeadz verbindet sich mit TCP Server
- [ ] Echte Speed-Daten vom Vgate gelesen
- [ ] RPM basierend auf Speed/Throttle simuliert
- [ ] Motorsound in RevHeadz sincron mit Fahrverhalten

### Sollte haben (Wichtig)
- [ ] Gang-Anzeige korrekt
- [ ] Rekuperation (Bremsen) erkannt
- [ ] System startet automatisch

### Kann haben (Nice-to-have)
- [ ] WiFi AP für Auto-Einsatz
- [ ] Web Dashboard für Live-Monitoring
- [ ] Multi-Client Support

---

## 10. Fazit

Das Projekt ist **technisch machbar** und der erste Schritt (TCP/IP Verbindung mit RevHeadz) ist **bereits erfolgreich abgeschlossen**! ✅

Die größte Herausforderung wird die **Vgate iCar Pro BLE Protocol Analyse** sein - müssen verstehen welche Daten der Vgate sendet und wie wir diese mit bleak lesen können.

**Empfohlene nächste Aktion:**
1. bleak Library auf Pi installieren
2. BLE Scan des Vgate iCar Pro durchführen
3. Proof of Concept: Speed vom Vgate lesen und an RevHeadz weiterleiten

**Status:** Bereitet sich auf "toggle to Act mode" für Phase 1: Research vor.