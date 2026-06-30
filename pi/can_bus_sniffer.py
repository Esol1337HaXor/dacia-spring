#!/usr/bin/env python3
"""
CAN-Bus Frame Sniffer für Vlink iCar Pro

Fängt alle CAN-Frames vom Fahrzeug ab und zeigt sie live an.
Zeigt auch an welche CAN-IDs am aktivsten sind.

Auf dem Pi ausführen:
  cd ~/obd2-adapter
  source ~/obd2-adapter-env/bin/activate
  python3 can_bus_sniffer.py
"""

import asyncio
import time
from collections import Counter
from bleak import BleakClient

# Vlink iCar Pro Konfiguration
MAC = "D2:E0:2F:8D:61:07"
CHAR_UUID = "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"

# Häufige Renault ZE CAN-IDs zum Überwachen
COMMON_CAN_IDS = [
    0x100, 0x110, 0x120, 0x130, 0x140, 0x150, 0x160, 0x170,
    0x180, 0x190, 0x1A0, 0x1B0, 0x1C0, 0x1D0, 0x1E0, 0x1F0,
    0x200, 0x210, 0x220, 0x230, 0x240, 0x250, 0x260, 0x270,
    0x280, 0x290, 0x2A0, 0x2B0, 0x2C0, 0x2D0, 0x2E0, 0x2F0,
    0x300, 0x310, 0x320, 0x330, 0x340, 0x350, 0x360, 0x370,
    0x380, 0x390, 0x3A0, 0x3B0, 0x3C0, 0x3D0, 0x3E0, 0x3F0,
    0x400, 0x410, 0x420, 0x430, 0x440, 0x450, 0x460, 0x470,
    0x480, 0x490, 0x4A0, 0x4B0, 0x4C0, 0x4D0, 0x4E0, 0x4F0,
]

# CAN ID zu möglicher Bedeutung (Renault ZE Referenz)
CAN_ID_MEANING = {
    0x170: "Fahrpedal / Throttle",
    0x1A0: "Speed / Geschwindigkeit",
    0x2E8: "Speed / Geschwindigkeit (alternativ)",
    0x2E0: "Throttle Position",
    0x350: "Ready Status / Zündung",
    0x368: "Batterie Status",
    0x380: "Motor/E-Motor Status",
}


def parse_can_frame(data: bytes) -> dict:
    """Parse einen rohen CAN-Frame aus ELM327 Antwort."""
    text = data.decode('utf-8', errors='ignore').strip()
    
    can_id = None
    data_bytes = []
    
    parts = text.split()
    if len(parts) >= 2:
        id_str = parts[0]
        
        # 29-bit Frame: beginnt mit 5, 6, 7
        if len(id_str) >= 4 and id_str[0] in ('5', '6', '7'):
            can_id = int(id_str[1:], 16)
        else:
            # 11-bit Frame
            can_id = int(id_str, 16)
        
        data_bytes = [int(b, 16) for b in parts[1:] if b not in ('\r', '>')]
    
    return {
        'can_id': can_id,
        'data_bytes': data_bytes,
        'raw': text,
        'meaning': CAN_ID_MEANING.get(can_id, 'Unbekannt') if can_id else None
    }


def format_can_frame(frame: dict) -> str:
    """Format einen parsed CAN-Frame für die Anzeige."""
    can_id = frame['can_id']
    data = frame['data_bytes']
    meaning = frame['meaning']
    
    if can_id is None:
        return f"  [?] Raw: {frame['raw']}"
    
    id_hex = f"0x{can_id:03X}"
    data_hex = ' '.join(f'{b:02X}' for b in data)
    
    meaning_str = f"  <-- {meaning}" if meaning else ""
    
    return f"  [{id_hex}] {data_hex}{meaning_str}"


async def can_bus_sniffer():
    """Haupt-Sniffer: Fängt alle CAN-Frames ab und zeigt Statistik."""
    
    print("=" * 70)
    print("  CAN-Bus Sniffer fuer Vlink iCar Pro")
    print(f"  Ziel MAC: {MAC}")
    print(f"  Ueberwache CAN-IDs: 0x100-0x4F0")
    print("=" * 70)
    print()
    
    frame_counter = Counter()
    all_frames = []
    seen_ids = set()
    start_time = time.time()
    
    def notify_handler(sender, data):
        """Fängt alle BLE Notify-Daten ab."""
        text = data.decode('utf-8', errors='ignore').strip()
        
        # Ignoriere ECHO und Prompt
        if text in ('\r', '>', '', 'ELM327', 'v2.3'):
            return
        
        # Auf CAN-Frames filtern
        parts = text.replace('\r', '').split()
        if len(parts) >= 2:
            first = parts[0]
            
            try:
                test_id = first if len(first) <= 3 else first[1:]
                can_id = int(test_id, 16)
                
                if 0x100 <= can_id <= 0x500:
                    frame = parse_can_frame(data)
                    frame_counter[can_id] += 1
                    seen_ids.add(can_id)
                    all_frames.append((time.time(), frame))
                    
                    # Zeige ersten 30 Frames detailliert
                    if len(all_frames) <= 30:
                        print(format_can_frame(frame))
            except ValueError:
                pass
    
    connect_attempts = 0
    max_attempts = 5
    
    while connect_attempts < max_attempts:
        try:
            print(f"Verbinde zum Vlink Adapter... (Versuch {connect_attempts + 1}/{max_attempts})")
            
            async with BleakClient(MAC) as client:
                print("Verbunden!")
                print()
                
                # Notify einrichten
                await client.start_notify(CHAR_UUID, notify_handler)
                print("Notify aktiv")
                print()
                
                # ELM327 auf CAN-Frame Modus vorbereiten
                print("Setze ELM327 auf CAN-Frame Modus...")
                
                commands = [
                    ('ATZ', 'Reset ELM327'),
                    ('ATE0', 'Echo aus'),
                    ('ATH0', 'Header aus'),
                    ('ATS0', 'Space aus'),
                    ('ATSP0', 'Protokoll auto'),
                    ('AT CAF 0', 'Alle Frames anzeigen'),
                    ('AT FC 0', 'Flow Control aus'),
                ]
                
                for cmd, desc in commands:
                    await client.write_gatt_char(CHAR_UUID, f'{cmd}\r'.encode())
                    await asyncio.sleep(0.3)
                
                print("ELM327 konfiguriert")
                print()
                print("=" * 70)
                print("  CAN-Frames werden abgefangen... (Str+C zum Stoppen)")
                print("=" * 70)
                print()
                
                try:
                    while True:
                        await asyncio.sleep(2.0)
                        
                        now = time.time()
                        elapsed = now - start_time
                        rate = len(all_frames) / elapsed if elapsed > 0 else 0
                        
                        print(f"\r  [{elapsed:.0f}s] {len(all_frames)} Frames empfangen | "
                              f"{len(seen_ids)} unique IDs | {rate:.1f} FPS", 
                              end='', flush=True)
                        
                        # Top 10 CAN-IDs alle 10 Frames
                        if frame_counter and len(all_frames) % 10 == 0:
                            print(f"\n  Top 10 CAN-IDs:")
                            for cid, count in frame_counter.most_common(10):
                                meaning = CAN_ID_MEANING.get(cid, 'Unbekannt')
                                print(f"    0x{cid:03X} {count:6d} frames  ({meaning})")
                
                except (KeyboardInterrupt, asyncio.CancelledError):
                    pass
                
                # Statistik ausgeben
                print()
                print()
                print("=" * 70)
                print("  SNIFFER STATISTIK")
                print("=" * 70)
                print(f"\n  Gesamte Frames: {len(all_frames)}")
                print(f"  Unique CAN-IDs: {len(seen_ids)}")
                print(f"  Dauer: {time.time() - start_time:.0f}s")
                
                if frame_counter:
                    print(f"\n  Alle aktiven CAN-IDs:")
                    for can_id, count in frame_counter.most_common():
                        meaning = CAN_ID_MEANING.get(can_id, 'Unbekannt')
                        pct = (count / len(all_frames)) * 100
                        bar = '#' * int(pct / 2)
                        print(f"    0x{can_id:03X} {count:6d} ({pct:5.1f}%)  {bar}  {meaning}")
                
                print(f"\n  Ueberwachte IDs die NICHT aktiv waren:")
                missing = set(COMMON_CAN_IDS) - seen_ids
                for cid in sorted(missing)[:20]:
                    meaning = CAN_ID_MEANING.get(cid, '')
                    print(f"    0x{cid:03X}" + (f" ({meaning})" if meaning else ""))
                
        except Exception as e:
            print(f"Verbindungfehler: {e}")
            connect_attempts += 1
            if connect_attempts < max_attempts:
                print(f"  Retry in 3 Sekunden...")
                await asyncio.sleep(3)
            else:
                print("Alle Verbindungsversuche fehlgeschlagen")
                break
    
    print("\nFertig!")


if __name__ == "__main__":
    try:
        asyncio.run(can_bus_sniffer())
    except KeyboardInterrupt:
        print("\n\nSniffer gestoppt.")